'''
Created on Feb 15, 2014

@author: EHWAAL
'''


import re
import model
from util import Const
from PyQt4 import QtGui, QtCore
from json import loads

DEFAULT_COLOR      = 'darkslateblue'
DEFAULT_BACKGROUND = 'white'
DEFAULT_FONT       = 'Arial 12pt'


class ArrowTypes(Const):
  START = 'start'
  END   = 'end'
  
  
class StyledItem(object):
  ROLE = None
  def __init__(self, style, role, apply=True):
    self.style, self.role = style, role
    if apply:
      self.applyStyle()
  @property
  def full_role(self):
    if self.ROLE:
      return '%s-%s'%(self.role, self.ROLE)
    return self.role
  def setRole(self, role):
    self.role = role
    self.applyStyle()
  def applyStyle(self):
    raise NotImplementedError()




class Observable(object):
  ''' An object which keeps track of which object is currently being styled. 
      Supports the observer pattern
  '''
  def __init__(self):
    self.subject = None
    self.listners   = []
  def set(self, object):
    old_object = self.subject
    self.subject = object
    if object != old_object:
      for listner in self.listners:
        listner(object)
  def get(self):
    return self.subject
  def subscribe(self, listner):
    if not listner in self.listners:
      self.listners.append(listner)
  def unsubscribe(self, listner):
    while listner in self.listners:
      self.listners.remove(listner)



class Style(Observable):
  linestyles = dict(solid=QtCore.Qt.SolidLine,
                    dashed=QtCore.Qt.DashLine,
                    dotted=QtCore.Qt.DotLine)
  
  current_object = Observable() # List of QGraphicsItems
  current_style  = Observable()
  
  def __init__(self, details):
    Observable.__init__(self)
    self.details = details
    self.reloadDetails()
    
  def reloadDetails(self):
    pairs = self.details.Details.split(';')
    test = [d.split(':') for d in pairs]
    test = [d for d in test if len(d)==2]
    self.items = {key.strip():value.strip() for key, value in test}
    self.set(self.items)
    
  def findApplicableStyles(self, stereotype):
    pattern = '([A-Za-z0-9_\-]*)-%s-[A-Za-z0-9_]*'%stereotype
    all_keys = '\n'.join(self.items.keys())
    results = re.findall(pattern, all_keys)
    return results
    
  def findItem(self, name, postfix):
    # The name consists of parts separated by dashes.
    parts = name.split('-')
    # Final part must be 'color'
    if postfix and parts[-1] != postfix:
      parts.append(postfix)
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
    col1 = self.findItem(name, 'color1')
    if col1:
      col2 = self.findItem(name, 'color2') or col1
    else:
      color = self.findItem(name, 'background-color') or DEFAULT_BACKGROUND
      return QtGui.QBrush(QtGui.QColor(color))
      
    Gradient = QtGui.QLinearGradient(0, 0, 100, 100)
    Gradient.setColorAt(0, QtGui.QColor(col1))
    Gradient.setColorAt(1, QtGui.QColor(col2))
    return QtGui.QBrush(Gradient)
    
  
  def getPen(self, name):
    color = self.getColor(name)
    style = self.getLineStyle(name)
    width = self.getLineWidth(name)
    return QtGui.QPen(color, width, style, QtCore.Qt.RoundCap, QtCore.Qt.RoundJoin)
  
  def getFont(self, name):
    ''' Font details are given in a space-separated list, e.g. "Arial bold 14pt"
    '''
    font = self.findItem(name, 'font') or DEFAULT_FONT
    fname = 'arial'
    size = 12
    italic = False
    weight = 1
    for pt in [f.strip().lower() for f in font.split()]:
      if pt == 'bold':
        weight = 3
      elif pt == 'italic':
        italic = True
      elif pt.endswith('pt'):
        size = int(pt[:-2])
      else:
        fname = pt
    return QtGui.QFont(fname, size, weight, italic) 

  
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
      color:#00529c;
      color1:white;
      color2:#00529c;
      width:3;
      archblock-width:1;
      archblock-offset:[10,5];
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