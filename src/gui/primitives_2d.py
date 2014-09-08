'''
Wrappers over the QtGraphics items that correspond to general primitives that
can be exported as SVG elements.

Created on Feb 17, 2014

@author: EHWAAL
'''

from PyQt4 import QtGui, QtCore
from styles import Styles, ArrowTypes, StyledItem
from math import atan2, pi
import string
import re
from xml.sax.saxutils import escape


# Define some constants to use as flags when exporting SVG
NO_POS = 1    # Do not take the position into account



def extractSvgGradients(style, stereotype):
  ''' Analyse the style sheet, and extract all background gradients for a specific stereotype.
  
      Returns a piece of SVG code that defines these gradients for reference by other elements.
  '''
  tmplt = '''<linearGradient id="$role" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%"   stop-color="$c1" />
        <stop offset="100%" stop-color="$c2" />
      </linearGradient>'''
  tmplt = string.Template(tmplt)
  # Get all roles for which a gradient is defined, using a regular expression
  re_exp = '^\s*(.*)-%s-color[12]:'%stereotype
  roles = re.findall(re_exp, style.details.Details, re.MULTILINE)
  roles = set(roles)    # Remove duplicates
  roles.add(stereotype)
  
  # For each role, add a gradient definition
  gradients = []
  for role in roles:
    name = '%s-%s'%(role, stereotype)
    # Use QT to determine the RGB value, in case a color name was used.
    # Happily, the QT naming scheme for RGB equals the one used by SVG!
    c1, c2 = [QtGui.QColor(style.findItem(name, 'color%i'%i)).name() for i in [1, 2]]
    gradients.append(tmplt.substitute(locals(), role=escape(role)))
    
  return '\n'.join(gradients)


def extractSvgStyle(item):
  ''' Analyse a QGraphicsItem and extract the style information, formatted as SVG. '''
  details = {}
  if isinstance(item, QtGui.QAbstractGraphicsShapeItem) or \
     isinstance(item, QtGui.QGraphicsLineItem):
    pen = item.pen()
    stroke_color = pen.color().name()  # The QT hash format is the same as SVG's.
    stroke_width = pen.width()
    details['stroke'] = str(stroke_color)
    details['stroke-width'] = str(stroke_width)
    
  if isinstance(item, QtGui.QAbstractGraphicsShapeItem):
    brush = item.brush()
    fill_style   = brush.style()
    fill_color   = brush.color().name()
    
    if fill_style in [QtCore.Qt.LinearGradientPattern, QtCore.Qt.RadialGradientPattern]:
      role = item.role
      if not role:
        role = item.ROLE
      if not role:
        role = '<default>'
      fill_color = 'url(#%s)'%escape(role)
    else:
      details['opacity'] = str(brush.color().alphaF())

    details['fill'] = str(fill_color)

  if isinstance(item, QtGui.QGraphicsSimpleTextItem) or isinstance(item, QtGui.QGraphicsTextItem):
    f = item.font()
    details['font-family'] = str(f.family())
    if f.pointSize() >= 0:
      details['font-size'] = str(f.pointSizeF())+'pt'
    else:
      details['font-size'] = str(f.pixelSize())+'px'
  
  style = ';'.join([':'.join(d) for d in details.items()])
  return 'style="%s;"'%style


class Arrow(QtGui.QGraphicsPolygonItem, StyledItem):
  ''' The arrow that ends a line. The shape of the arrow is determined by the style '''
  def __init__(self, parent, style, role, arrow_type):
    QtGui.QGraphicsPolygonItem.__init__(self, parent=parent)
    self.arrow_type = arrow_type
    StyledItem.__init__(self, style, role)
  def applyStyle(self):
    points = self.style.getArrow(self.full_role, self.arrow_type)
    self.setPolygon(points)
    self.setPen(self.style.getPen(self.full_role))
  def exportSvg(self, flags=0):
    color = self.pen().color().name()
    tmpl = string.Template('<g transform="translate($x,$y) rotate($angle)">'
                           '<polyline points="$points" stroke="$color"/></g>')
    points = self.style.getArrow(self.full_role, self.arrow_type)
    points = ' '.join(['%i,%i'%(c.x(), c.y()) for c in points])
    x = self.x()
    y = self.y()
    angle = self.rotation()
    return tmpl.substitute(points=points, x=x, y=y, angle=angle, color=color)


class Line(QtGui.QGraphicsLineItem, StyledItem):
  def __init__(self, x1, y1, x2, y2, parent, style, role):
    QtGui.QGraphicsLineItem.__init__(self, x1, y1, x2, y2, parent)
    self.setFlag(QtGui.QGraphicsItem.ItemIsSelectable)
    self.__start = self.__end = None
    StyledItem.__init__(self, style, role)

  def applyStyle(self):
    self.setPen(self.style.getPen(self.full_role))
    has_start = self.style.getArrow(self.full_role, ArrowTypes.START)
    has_end   = self.style.getArrow(self.full_role, ArrowTypes.END)
    if self.__start:
      if has_start:
        self.__start.applyStyle()
      else:
        self.scene().removeItem(self.__start)
        self.__start = None
    elif has_start:
      self.__start = Arrow(self, self.style, self.role, ArrowTypes.START)
      self.__start.setPos(self.line().p1())
      self.__start.rotate(360 - self.line().angle())
      self.__start.applyStyle()
    if self.__end:
      if has_end:
        self.__end.applyStyle()
      else:
        self.scene().removeItem(self.__end)
        self.__end = None
    elif has_end:
      self.__end = Arrow(self, self.style, self.full_role, ArrowTypes.END)
      self.__end.setPos(self.line().p2())
      self.__end.rotate(self.line().angle())
      self.__end.applyStyle()
  def exportSvg(self, flags=0):
    tmplt = string.Template('''<g $style transform="translate($x,$y) rotate($angle)">
      <line x1="$x1" y1="$y1" x2="$x2" y2="$y2" $style />
      $start
      $end
    </g>''')
    l = self.line()
    x, y, angle = self.x(), self.y(), self.rotation()
    x1, y1, x2, y2 = l.x1(), l.y1(), l.x2(), l.y2()   # pylint: disable=W0612
    style = extractSvgStyle(self)                     # pylint: disable=W0612
    start = self.__start.exportSvg() if self.__start else ''
    end = self.__end.exportSvg() if self.__end else ''
    result = tmplt.substitute(locals())
    return result
    
class Text(QtGui.QGraphicsRectItem, StyledItem):
  ROLE = 'text'
  NO_PEN = QtGui.QPen(QtCore.Qt.NoPen)
  
  def __init__(self, txt, style, role, parent=None, apply=True):
    QtGui.QGraphicsRectItem.__init__(self, parent=parent)
    self.text = QtGui.QGraphicsTextItem(txt, parent=self)
    self.style, self.role = style, role
    StyledItem.__init__(self, style, role, apply=parent is None and apply)
    
  def setText(self, text):
    if text is None:
      text = ''
    self.text.setPlainText(text)
    
  def setPos(self, pos, y=None):
    ''' Overload QGraphicsItem.setPos; also moves the background. '''
    halign = self.style.getHAlign(self.full_role)
    valign = self.style.getVAlign(self.full_role)

    if isinstance(self.parentItem(), Block):
      # Use the parent rectangle to determine shape
      margin = self.style.getFloat('%s-margin'%self.full_role, 0)
      margin += self.style.getLineWidth(self.full_role)/2.0
      prect = self.parentItem().rect()
      rect = QtCore.QRectF(0, 0, prect.width()-2*margin, 
                           prect.height()-2*margin,)
      self.text.setTextWidth(rect.width())
      self.setRect(rect)
      QtGui.QGraphicsRectItem.setPos(self, margin, margin)
    else:
      rect = self.boundingRect()
      qt = QtCore.Qt
      dx = {qt.AlignLeft:0, qt.AlignHCenter:-rect.width()/2, qt.AlignRight:-rect.width()}[halign]
      dy = {qt.AlignTop:0,  qt.AlignVCenter:-rect.height()/2, qt.AlignBottom:-rect.height()}[valign]
      if y is None:
        x = pos.x() + dx
        y = pos.y() + dy
      else:
        x = pos + dx
        y += dy
      QtGui.QGraphicsRectItem.setPos(self, x, y)
      self.setRect(self.text.boundingRect())
    
  def applyStyle(self):
    self.text.setFont(self.style.getFont(self.full_role))
    self.setBrush(self.style.getBrush(self.full_role))
    self.setPen(self.NO_PEN)
    rect = self.text.boundingRect()
    self.setRect(rect)

  def exportSvg(self, flags=0):
    # SVG text position (0,0) is the text baseline;
    # PyQT text position (0,0) is the top left corner.
    # The difference equals
    
    if flags & NO_POS:
      x, y = 0, 0
    else:
      x, y = self.pos().x(), self.pos().y()
    
    # Determine the height of the text
    # SVG now has a 'em' unit, but it is not yet widely supported.
    # Thus we use the 'pt' unit to adjust the baseline of the text.
    f = self.text.font()
    if f.pointSize() >= 0:
      size = str(f.pointSizeF())+'pt'
    else:
      size = str(f.pixelSize())

    tmplt = '''<g  transform="translate($x, $y)">
                   <rect width="$width" height="$height" $background />
                   <text dy="$size" $style>$txt</text>
               </g>'''
    style = extractSvgStyle(self.text)
    background = extractSvgStyle(self)
    rect = self.rect()
    width = rect.width()
    height = rect.height()
    txt = str(self.text.toPlainText())
    return string.Template(tmplt).substitute(locals())


class ResizeHandle(QtGui.QGraphicsPolygonItem):
  ''' Class that handles resizing for blocks.
      Include this widget as a child in a corner of the block.
  '''
  points = [QtCore.QPointF(*p) for p in [[-20, 0], [0, -20], [0, 0]]]
  def __init__(self, parent):
    QtGui.QGraphicsPolygonItem.__init__(self, QtGui.QPolygonF(self.points), parent=parent)
    self.dragging = False
    self.start = None
    self.size = None
    self.setAcceptedMouseButtons(QtCore.Qt.LeftButton)
  def mousePressEvent(self, event):
    ''' Called when the user clicks on the resize handle. '''
    self.dragging = True
    self.start = event.scenePos()
    self.size = self.parentItem().rect().bottomRight()
    event.accept()
  def mouseReleaseEvent(self, event):
    ''' Called when the user releases a mouse button on the resize handle. '''
    event.accept()
    self.dragging = False
    self.parentItem().commitRect()
    
  def mouseMoveEvent(self, event):
    ''' Called when the user drags the mouse while over a resize handle. '''
    if self.dragging:
      event.accept()
      rect = self.parentItem().rect()
      rect.setBottomRight(event.scenePos() - self.start + self.size)
      self.parentItem().setRect(rect)
      self.setPos(rect.bottomRight())


class Block(QtGui.QGraphicsRectItem, StyledItem):
  def __init__(self, details, style, role, text=None, resizable=True):
    QtGui.QGraphicsRectItem.__init__(self, 0, 0, details.width, details.height)
    self.setFlag(QtGui.QGraphicsItem.ItemIsMovable)
    self.setFlag(QtGui.QGraphicsItem.ItemIsSelectable)
    self.connections = []
    StyledItem.__init__(self, style, role)
    if text is None:
      text = ''
    self.text = Text(text, style, self.full_role, self)
    if resizable:
      self.corner = ResizeHandle(self)
      self.corner.setPos(QtCore.QPointF(details.width, details.height))
    self.applyStyle()
      
  def addConnection(self, c):
    ''' Called when a connection is added to this block.
    '''
    if not c in self.connections:
      self.connections.append(c)
    
  def applyStyle(self):
    self.setPen(self.style.getPen(self.full_role))
    self.setBrush(self.style.getBrush(self.full_role))
    self.adjustText()
  
  def adjustText(self):
    if self.text:
      self.text.applyStyle()
      self.text.setPos(0, 0)
      
  def updatePos(self):
    ''' Called when position of the item has changed.
        Change the position in the database accordingly.
    '''
    self.details.x = self.x()
    self.details.y = self.y()
    for c in self.connections:
      c.updatePos()
    
  def mouseReleaseEvent(self, event):
    QtGui.QGraphicsRectItem.mouseReleaseEvent(self, event)
    commit = False
    if self.x() != self.details.x:
      self.details.x = self.x()
      commit = True
    if self.y() != self.details.y:
      self.details.y = self.y()
      commit = True
    if commit:
      self.scene().session.commit()
      
  def commitRect(self):
    rect = self.rect()
    self.details.width = rect.width()
    self.details.height = rect.height()

    self.scene().session.commit()
    self.adjustText()
  
  def fpPos(self):
    return self.scenePos().x(), self.scenePos().y() - self.rect().height()
  
  def exportSvg(self, flags=0):
    tmplt = '''<g  transform="translate($x, $y)" >
                 <rect width="$width" height="$height"  $style />
                 $txt
               </g>'''
    d = self.details.toDict()
    d['style'] = extractSvgStyle(self)
    txt = self.text.exportSvg()
    return string.Template(tmplt).substitute(d, txt=txt)
  
