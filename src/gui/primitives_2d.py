'''
Created on Feb 17, 2014

@author: EHWAAL
'''

from PyQt4 import QtGui, QtCore
from styles import Styles, ArrowTypes, StyledItem
from math import atan2, pi
import string


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
  def exportSvg(self):
    tmpl = string.Template('<g transform="translate($x,$y) rotate($angle)"><polyline points="$points" stroke="black"/></g>')
    points = ' '.join(['%i,%i'%(c.x(), c.y()) for c in self.points])
    x = self.x()
    y = self.y()
    angle = self.rotation()
    return tmpl.substitute(points=points, x=x, y=y, angle=angle)


class Line(QtGui.QGraphicsLineItem, StyledItem):
  def __init__(self, x1, y1, x2, y2, parent, style, role):
    QtGui.QGraphicsLineItem.__init__(self, x1, y1, x2, y2, parent)
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
    elif has_start:
      self.__start = Arrow(self, self.style, self.role, ArrowTypes.START)
      self.__start.setPos(self.line().p1())
      self.__start.rotate(360 - self.line().angle())
    if self.__end:
      if has_end:
        self.end.applyStyle()
      else:
        self.scene().removeItem(self.__end)
    elif has_end:
      self.__end = Arrow(self, self.style, self.role, ArrowTypes.END)
      self.__end.setPos(self.line().p2())
      self.__end.rotate(self.line().angle())
    
    
class Text(QtGui.QGraphicsTextItem, StyledItem):
  def __init__(self, txt, style, role):
    QtGui.QGraphicsTextItem.__init__(self, txt)
    self.style, self.role = style, role
    Text.applyStyle(self)
  def applyStyle(self):
    self.setFont(self.style.getFont(self.full_role))


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
    self.text = None
    if text:
      self.text = QtGui.QGraphicsTextItem(text, parent=self)
    if resizable:
      self.corner = ResizeHandle(self)
      self.corner.setPos(QtCore.QPointF(details.width, details.height))
    StyledItem.__init__(self, style, role)
    
  def applyStyle(self):
    self.setPen(self.style.getPen(self.full_role))
    self.setBrush(self.style.getBrush(self.full_role))
    if self.text:
      self.text.setFont(self.style.getFont(self.full_role))
      self.text.setPos(self.style.getOffset(self.full_role, default=[10, 1]))
    
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
  
  def fpPos(self):
    return self.x(), self.y() - self.rect().height()
  

  def exportSvg(self):
    tmplt = '''<g  transform="translate($x, $y)">
                 <rect width="$width" height="$height" fill="white" stroke="black" />
                 <text x=10 y=1 dy=1em style="font-family:$font; font-size:$font_size;">$Name</text>
               </g>'''
    d = self.details.toDict()
    d.update(self.block_details.toDict())
    return string.Template(tmplt).substitute(d, font=getConfig('font_name'),
                                                font_size=17.0/12*getConfig('font_size'))
  
