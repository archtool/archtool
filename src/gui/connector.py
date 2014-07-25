'''
Implementation of an intelligent and flexible connector graphical element.

Created on Mar 20, 2014

@author: ehwaal
'''

from PyQt4 import QtGui, QtCore

from primitives_2d import Line, Text

def intersect(line, block):
  ''' Determine where a line intersects a block.
  '''
  x1, y1, x2, y2 = block.getCoords()
  points = [QtCore.QPointF(*p) for p in [(x1, y1), (x1, y2), (x2, y1), (x2, y2)]]
  lines = [QtCore.QLineF(*p) for p in [(points[0], points[1]),
                                       (points[0], points[2]),
                                       (points[1], points[3]),
                                       (points[2], points[3])]]
  
  p = QtCore.QPointF()
  for l in lines:
    if line.intersect(l, p) == 1:
      return p

class LineHandle(QtGui.QGraphicsRectItem):
  def __init__(self, pos, parent):
    rect = QtCore.QRectF(pos-QtCore.QPointF(-2,-2),
                         pos+QtCore.QPointF(2,2))
    QtGui.QGraphicsItem.__init__(self, rect, parent)

class Connection(Line):
  # TODO: start and end the line at the block edge.
  ROLE = 'connection'
  def __init__(self, details, start, end, style, *args, **kwds):
    self.details = details
    # Start and end are the BlockRepresentation details for this line.
    self.start = start
    self.end = end
    self.name = None
    start.addConnection(self)
    end.addConnection(self)

    Line.__init__(self, 0,0,0,0, None, style, details.style_role)
    
    if details.theConnection.Name:
      self.name = Text(details.theConnection.Name, style, self.full_role, self)
      
    self.updatePos()
      
  def applyStyle(self):
    self.setPen(self.style.getPen(self.ROLE))
    if self.name:
      self.name.applyStyle()

  def setRole(self, role):
    ''' Called by the style editing mechanism when the user changes the role. 
        The role is here only the user-determined part, and does not include the
        hard-coded part from ROLE.'''
    self.details.style_role = role
    Connection.setRole(self, '')
    
  def updatePos(self):
    ''' Called when one of the blocks has changed its position. '''
    line = QtCore.QLineF(self.start.x() + self.start.details.width/2, 
                         self.start.y() + self.start.details.height/2,
                         self.end.x() + self.end.details.width/2,
                         self.end.y() + self.end.details.height/2)
    z = min(self.start.zValue(),
            self.end.zValue())
    self.setZValue(z-0.1)

    self.setLine(line)
    if self.name:
      pos = (line.p1() + line.p2()) / 2
      self.name.setPos(pos)

    
  def fpPos(self):
    ''' Return the position where actions are placed.
        The position is in scene (absolute) coordinates.
    '''
    line = self.line()
    x = (line.x1() + line.x2())/2.0
    y = (line.y1() + line.y2())/2.0
    return x, y
  
