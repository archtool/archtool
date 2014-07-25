'''
Created on Feb 15, 2014

@author: EHWAAL

Copyright (C) 2014 Evert van de Waal
This program is released under the conditions of the GNU General Public License.
'''

# TODO: Font names containing spaces are not handled properly.


import re
import model
from util import Const
from PyQt4 import QtGui, QtCore
from json import loads
import logging

DEFAULT_COLOR      = 'darkslateblue'
DEFAULT_BACKGROUND = 'white'
DEFAULT_FONT       = 'Arial 12pt'


class ArrowTypes(Const):
  START = 'start'
  END   = 'end'
  

class StyleTypes(Const):
  BOOL      = 1
  COLOR     = 2
  LINESTYLE = 3
  ARROW     = 4
  HALIGN    = 5
  VALIGN    = 6
  FLOAT     = 7
  FONT      = 8
  XYCOOD    = 9
  CONNECTOR = 10


class ConnectorTypes(Const):
  DIRECT  = 1
  SQUARED = 2


KNOWN_STYLEITEMS = {'halign'          :StyleTypes.HALIGN,
                    'valign'          :StyleTypes.VALIGN,
                    'font'            :StyleTypes.FONT,
                    'color1'          :StyleTypes.COLOR,
                    'color2'          :StyleTypes.COLOR,
                    'background-color':StyleTypes.COLOR,
                    'color'           :StyleTypes.COLOR,
                    'width'           :StyleTypes.FLOAT,
                    'line'            :StyleTypes.LINESTYLE,
                    'alpha'           :StyleTypes.FLOAT,
                    'font'            :StyleTypes.FONT,
                    'offset'          :StyleTypes.XYCOOD,
                    'is_gradient'     :StyleTypes.BOOL,
                    'end'             :StyleTypes.ARROW,
                    'start'           :StyleTypes.ARROW,
                    'constyle'        :StyleTypes.CONNECTOR
                   }


class StyledItem(object):
  ROLE = None
  def __init__(self, style, role, apply=True):
    self.style = style
    if isinstance(role, tuple):
      self.role, self.ROLE = role
    else:
      self.role = role
  @property
  def stereotype(self):
    item = self
    while True:
      if hasattr(item, 'ROLE'):
        return item.ROLE
      if item.parent():
        item = item.parent()
        continue
      return None
        
  @property
  def full_role(self):
    if self.ROLE and self.role:
      return '%s-%s'%(self.role, self.ROLE)
    if self.role is not None:
      return self.role
    elif self.ROLE:
      return self.ROLE
    return ''
  def setRole(self, role):
    self.role = role
    self.applyStyle()
  def applyStyle(self):
    raise NotImplementedError()



def getBool(text):
  ''' Convert a text to a boolean value '''
  if text is None:
    return False
  return text.lower() in ['y', 'j', 'ja', 'yes', '1', 'true']

def getFont(text):
  fname = 'arial'
  size = 12
  italic = False
  weight = 1
  underline = False
  strikeout = False
  for pt in [f.strip().lower() for f in text.split()]:
    if pt == 'bold':
      weight = 3
    elif pt == 'italic':
      italic = True
    elif pt.endswith('pt'):
      size = int(pt[:-2])
    elif pt == 'underline':
      underline = True
    elif pt == 'strikeout':
      strikeout = True
    else:
      fname = pt
  font = QtGui.QFont(fname, size, weight, italic)
  font.setUnderline(underline)
  font.setStrikeOut(strikeout)
  return font
  
def getItemType(item):
  type_name = item.split('-')[-1]
  return KNOWN_STYLEITEMS[type_name]

class Observable(object):
  ''' An object which keeps track of which object is currently being styled. 
      Supports the observer pattern
  '''
  def __init__(self):
    self.subject = None
    self.listners   = []
  def set(self, object):
    self.subject = object
    for listner in self.listners:
      try:
        listner(object)
      except:
        logging.exception('Exception when calling observer')
  def get(self):
    return self.subject
  def subscribe(self, listner):
    if not listner in self.listners:
      self.listners.append(listner)
  def unsubscribe(self, listner):
    while listner in self.listners:
      self.listners.remove(listner)



class Style(Observable):
  PART_SEP = '-'    # Separates parts of a name.
  qt = QtCore.Qt
  
  linestyles = dict(solid=QtCore.Qt.SolidLine,
                    dashed=QtCore.Qt.DashLine,
                    dotted=QtCore.Qt.DotLine)
  
  halignopts = {'left': qt.AlignLeft,
            'right': qt.AlignRight,
            'center': qt.AlignHCenter}
  
  valignopts = {'top': qt.AlignTop,
            'bottom': qt.AlignBottom,
            'center': qt.AlignVCenter}
  
  current_object = Observable() # List of QGraphicsItems
  current_style  = Observable()
  
  def __init__(self, details):
    Observable.__init__(self)
    self.details = details
    self.requested_keys = set()
    self.reloadDetails()
    
  def requestedItems(self, stereotype):
    pattern = '[A-Za-z0-9_\-]*%s-([A-Za-z0-9_\-]*)'%stereotype
    all_keys = '\n'.join(self.requested_keys)
    results = re.findall(pattern, all_keys)
    results = sorted(set(results))
    return results
    
    
  def reloadDetails(self):
    pairs = self.details.Details.split(';')
    test = [d.split(':') for d in pairs]
    test = [d for d in test if len(d)==2]
    self.items = {key.strip():value.strip() for key, value in test}
    self.set(self.items)
    
  def setItem(self, role, stereotype, value):
    self.items['%s-%s'%(role, stereotype)] = value
    all_items = [':'.join(p) for p in self.items.items()]
    self.details.Details = ';\n'.join(sorted(all_items))
    self.set(self.items)
    
  def findApplicableRoles(self, stereotype):
    pattern = '([A-Za-z0-9_\-]*)-%s-[A-Za-z0-9_]*'%stereotype
    all_keys = '\n'.join(self.items.keys())
    results = re.findall(pattern, all_keys)
    return list(set(results))
    
  def findItem(self, name, postfix):
    # Final part must be the 'postfix'
    if postfix and not name.endswith(postfix):
      name = '-'.join([name, postfix])
    self.requested_keys.add(name)
    # The name consists of parts separated by dashes.
    parts = name.split('-')

    while parts:
      # if a name is not present, try a less specific one.
      try_name = '-'.join(parts)
      if try_name not in self.items:
        parts.pop(0)
        continue
      return self.items[try_name]
    return None
    
  def getColor(self, name):
    color = self.findItem(name, 'color') or DEFAULT_COLOR
    return QtGui.QColor(color)

  def getLineStyle(self, name):
    linestyle = self.findItem(name, 'line') or 'solid'
    return self.linestyles[linestyle]
  
  def getLineWidth(self, name):
    return int(self.findItem(name, 'width')) or 3
      
  def getBrush(self, name):
    # Get the gradient
    is_gradient = getBool(self.findItem(name, 'is_gradient'))
    col1 = self.findItem(name, 'color1') or DEFAULT_BACKGROUND
    col2 = self.findItem(name, 'color2') or col1
    color = self.findItem(name, 'background-color') or DEFAULT_BACKGROUND
    alpha = self.findItem(name, 'alpha') or '1.0'
    if is_gradient:

      Gradient = QtGui.QLinearGradient(0, 0, 100, 100)
      col1 = QtGui.QColor(col1)
      col2 = QtGui.QColor(col2)
      col1.setAlphaF(float(alpha))
      col2.setAlphaF(float(alpha))
      Gradient.setColorAt(0, col1)
      Gradient.setColorAt(1, col2)
      return QtGui.QBrush(Gradient)
    else:
      col = QtGui.QColor(color)
      col.setAlphaF(float(alpha))
      return QtGui.QBrush(col)    
  
  def getPen(self, name):
    color = self.getColor(name)
    style = self.getLineStyle(name)
    width = self.getLineWidth(name)
    return QtGui.QPen(color, width, style, QtCore.Qt.RoundCap, QtCore.Qt.RoundJoin)
  
  def getVAlign(self, name):
    align = self.findItem(name, 'valign') or 'center'
    return self.valignopts[align.lower()]
            
  def getHAlign(self, name):
    align = self.findItem(name, 'halign') or 'center'
    return self.halignopts[align.lower()]
  
  def getFont(self, name):
    ''' Font details are given in a space-separated list, e.g. "Arial bold 14pt"
    '''
    font = self.findItem(name, 'font') or DEFAULT_FONT
    return getFont(font)
  

  
  def getArrow(self, name, arrow_type):
    ''' Returns the polygon object to be used for the arrow, or None.
        Location is either  '''
    points = self.findItem(name, arrow_type)
    if not points:
      return
    points = loads(points)
    points = [QtCore.QPointF(*p) for p in points]
    return QtGui.QPolygonF(points)
  
  def getOffset(self, name, default):
    ''' Returns a QPointF that can be used as an offset. '''
    offset = self.findItem(name, 'offset')
    offset = loads(offset) if offset else default
    return QtCore.QPointF(*offset)
  
  def getFloat(self, name, default=0.0):
    ''' Returns a single floating point number '''
    f = self.findItem(name, None)
    return float(f) if f else default


def createDefaultStyle(session):
  with model.sessionScope(session):
    style = model.Style(Name='Default', Details = '''
      background-color:white;
      font:Arial 12pt;
      halign:center;
      valign:center;
      is_gradient:True;
      color:#00529c;
      color1:white;
      color2:#00529c;
      text-is_gradient:False;
      functionpoint-is_gradient:False;
      functionpoint-alpha:1.0;
      connection-text-alpha:1.0;
      annotation-color2:#ffef5d;
      annotation-text-alpha:0.0;
      width:3;
      archblock-width:1;
      archblock-offset:[0,0];
      archblock-text-alpha:0.0;
      functionpoint-end:[[0,0], [-5, 5], [0, 0], [-5, -5], [0,0]];
      arrow-functionpoint-offset:[-10,10];
      type1-archblock-color2:white;
      type2-archblock-color2:#f2f2f2;
      type3-archblock-color2:#838383;
      type4-archblock-color2:cornflower blue
    ''')
    # TODO: Store the default style in the database
    #session.add(style)
    return style

  
  

class Styles(object):
  style_sheet = None
  def __init__(self, session):
    self.session = session
    
    style_defs = session.query(model.Style).all()
    if len(style_defs) == 0:
      style_defs = [createDefaultStyle(session)]

    self.styles = [Style(d) for d in style_defs]
      
    self.style_names = {d.Name:s for d, s in zip(style_defs, self.styles)}
    self.style_ids = {d.Id:s for d, s in zip(style_defs, self.styles)}
    
  def getStyle(self, name):
    ''' Name can either be a number, refering to the Id of the style,
        or a string (the name).
    '''
    if name is None:
      return self.style_names['Default']
    if isinstance(name, basestring):
      return self.style_names[name]
    return self.style_ids[name]
  
  @staticmethod
  def load(session):
    ''' Load the styles from the database '''
    Styles.style_sheet = Styles(session)


def run():
  d = model.Style(Details='background-color : yellow; color:blue; ')

if __name__ == '__main__':
  run()