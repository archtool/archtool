'''
Created on Sep 26, 2013

@author: EHWAAL

Copyright (C) 2014 Evert van de Waal
This program is released under the conditions of the GNU General Public License.
'''
import math
import model
import string
from model.config import getConfig
import inspect
from PyQt4 import QtGui, QtCore
import sqlalchemy as sql


# TODO: Allow addition of a child within view
# TODO: Ensure parents are below children
# TODO: Allow area select
# TODO: Allow copy - paste of blocks between views.
# TODO: Maak robuust voor meerdere instanties van het zelfde blok.
# TODO: Verwijderen van geselecteerde elementen met Delete knop.

# FIXME: delete block in view leaves block outline on screen
# FIXME: rename architecture block is not shown in open viewer.


# TODO: Add annotations (squares regions with a comment attached).
# FIXME: Zorg dat bij het aanmaken van iets nieuws, dit meteen geselecteerd is.

MIME_TYPE = 'application/x-qabstractitemmodeldatalist'

ItemColor = QtGui.QColor('darkslateblue')
ItemSelectedColor = QtGui.QColor('deepskyblue')
ConnectorColor = QtGui.QColor('slateblue')

ConnectionPen = QtGui.QPen(ConnectorColor, 3,
              QtCore.Qt.SolidLine, QtCore.Qt.RoundCap, QtCore.Qt.RoundJoin)


BLOCK_WIDTH  = 100
BLOCK_HEIGHT = 30

class NoDetailsFound(Exception):
  ''' Exception that is raised when looking for a widget at a certain place 
      and not finding anything.
  '''
  pass

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


class BlockItem(QtGui.QGraphicsRectItem):
  ''' Representation of an architecture block.
  '''
  Pen = QtGui.QPen(ItemColor, 1,
                QtCore.Qt.SolidLine, QtCore.Qt.RoundCap, QtCore.Qt.RoundJoin)
  SelectedPen = QtGui.QPen(ItemSelectedColor, 3,
                QtCore.Qt.SolidLine, QtCore.Qt.RoundCap, QtCore.Qt.RoundJoin)

  def __init__(self, rep_details, block_details):
    QtGui.QGraphicsRectItem.__init__(self, 0, 0, rep_details.width, rep_details.height)
    self.setPen(self.Pen)
    self.details = rep_details
    self.setFlag(QtGui.QGraphicsItem.ItemIsMovable)
    self.setFlag(QtGui.QGraphicsItem.ItemIsSelectable)
    self.text = QtGui.QGraphicsTextItem(block_details.Name, parent=self)
    self.text.setPos(QtCore.QPointF(10, 1))
    self.text.setFont(QtGui.QFont(getConfig('font_name'),
                                  getConfig('font_size')))
    
    
    self.corner = ResizeHandle(self)
    self.corner.setPos(QtCore.QPointF(rep_details.width, rep_details.height))
    self.block_details = block_details
    
  def exportSvg(self):
    tmplt = '''<g  transform="translate($x, $y)">
                 <rect width="$width" height="$height" fill="white" stroke="black" />
                 <text x=10 y=1 dy=1em style="font-family:$font; font-size:$font_size;">$Name</text>
               </g>'''
    d = self.details.toDict()
    d.update(self.block_details.toDict())
    return string.Template(tmplt).substitute(d, font=getConfig('font_name'),
                                                font_size=17.0/12*getConfig('font_size'))
  
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
      
  def fpPos(self):
    return self.x(), self.y() - self.rect().height()
  
  def commitRect(self):
    rect = self.rect()
    self.details.width = rect.width()
    self.details.height = rect.height()

    self.scene().session.commit()

  def setColor(self):
    if not self.details.Color:
      self.details.Color = 2
    color = self.scene().block_colors[self.details.Color]
    Gradient = QtGui.QLinearGradient(0, 0, 100, 100)
    Gradient.setColorAt(0, QtGui.QColor('white'))
    Gradient.setColorAt(1, color)
    brush = QtGui.QBrush(Gradient)
    self.setBrush(brush)


class FunctionPoint(QtGui.QGraphicsTextItem):
  class Arrow(QtGui.QGraphicsPolygonItem):
    points = [QtCore.QPointF(*p) for p in [[-10, 0], [10, 0], [5, 5], [10, 0], [5, -5], [10,0]]]
    Pen = QtGui.QPen(ItemColor, 1,
                  QtCore.Qt.SolidLine, QtCore.Qt.RoundCap, QtCore.Qt.RoundJoin)
    def __init__(self, parent):
      QtGui.QGraphicsPolygonItem.__init__(self, QtGui.QPolygonF(self.points), parent=parent)
      self.setPen(self.Pen)
      self.setPos(-10, 10)
    def exportSvg(self):
      tmpl = string.Template('<g transform="translate($x,$y) rotate($angle)"><polyline points="$points" stroke="black"/></g>')
      points = ' '.join(['%i,%i'%(c.x(), c.y()) for c in self.points])
      x = self.x()
      y = self.y()
      angle = self.rotation()
      return tmpl.substitute(points=points, x=x, y=y, angle=angle)
  def __init__(self, details, fp, connection):
    text = '%s: %s'%(details.Order, fp.Name)
    QtGui.QGraphicsTextItem.__init__(self, text)
    self.setFlag(QtGui.QGraphicsItem.ItemIsSelectable)
    self.connection = connection
    self.details = details
    self.fp = fp
    self.setFont(QtGui.QFont(getConfig('font_name'),
                             getConfig('font_size')))
    self.setFlag(QtGui.QGraphicsItem.ItemIsMovable)
    
    if isinstance(self.connection, BlockItem):
      self.arrow = None
    else:
      # Add the arrow.
      self.arrow = self.Arrow(self)
    self.move()
  def exportSvg(self):
    tmplt = '''
               <g transform="translate($x,$y)">
                 $arrow
                 <text dy=1em style="font-family:$font; font-size:$font_size;">$text</text>
               </g>
    '''
    arrow=self.arrow.exportSvg() if self.arrow else ''
    d = dict(text=str(self.toPlainText()),
             x=self.x(), y=self.y()+self.boundingRect().height(),
             font=getConfig('font_name'),
             font_size=17.0/12*getConfig('font_size'),
             arrow = arrow)
    xml = string.Template(tmplt).substitute(d)
    return xml

  def anchorPos(self):
    x, y = self.connection.fpPos()
    order = self.details.order_on_target
    x += 10*order
    y -= 20*order
    return x, y
    
  def move(self):
    x, y = self.anchorPos()
    x += self.details.Xoffset
    y += self.details.Yoffset
    self.setPos(x,y)
    text = '%s: %s'%(self.details.Order, self.fp.Name)
    self.setPlainText(text)
    if self.arrow:
      angle = -self.connection.line().angle()
      if self.fp.isResponse:
        angle += 180.0
      self.arrow.setRotation(angle)

  def mouseReleaseEvent(self, event):
    QtGui.QGraphicsTextItem.mouseReleaseEvent(self, event)
    commit = False
    xa, ya = self.anchorPos()
    x = self.x() - xa
    y = self.y() - ya
    if x != self.details.Xoffset:
      self.details.Xoffset = x
      commit = True
    if y != self.details.Yoffset:
      self.details.Yoffset = y
      commit = True
    if commit:
      self.scene().session.commit()

class Connection(QtGui.QGraphicsLineItem):
  def __init__(self, details, start, end, *args, **kwds):
    QtGui.QGraphicsLineItem.__init__(self, *args, **kwds)
    self.details = details
    # Start and end are the BlockRepresentation details for this line.
    self.start = start
    self.end = end
  def fpPos(self):
    ''' Return the position where actions are placed.
    '''
    line = self.line()
    x = (line.x1() + line.x2())/2.0
    y = (line.y1() + line.y2())/2.0
    return x, y
  
  def exportSvg(self):
    ''' Return a piece of SVG code representing the connection. '''
    tmplt = string.Template('<line x1="$x1" y1="$y1" x2="$x2" y2="$y2" stroke="black" />')
    l = self.line()
    x1, y1, x2, y2 = l.x1(), l.y1(), l.x2(), l.y2()
    return tmplt.substitute(x1=x1, y1=y1, x2=x2, y2=y2)


def getDetails(item, dont_raise=False):
  while item:
    if hasattr(item, 'details'):
      return item.details, item
    item = item.parentItem()
  if dont_raise:
    return None, None
  raise NoDetailsFound('Kon geen details vinden')
      

class MyScene(QtGui.QGraphicsScene):
  def __init__(self, details, drop2Details, session, block_colors):
    '''
    drop2Details: a callback function that finds the details
    belonging to the item that was dropped.
    '''
    QtGui.QGraphicsScene.__init__(self)
    self.drop2Details = drop2Details
    self.session = session
    self.details = details
    self.connections = {}   # Connection.Id : Connection
    self.connection_items = {} # Connection.Id : connection item.
    self.all_details = []   # An ordered list of (fptoview, functionpoint) tuples
    self.known_fps = set()
    self.block_colors = block_colors
    
    self.connectLine = None
    
    # Add the existing blocks and connections
    self.block_repr = {}    # BlockRepr.Id : BlockRepr
    # FIXME: Replace block_details with a relationship in the model.
    self.block_details = {} # ArchBlock.Id : ArchBlock
    self.block_items = {}   # ArchBlock.Id : BlockItem
    q = self.session.query(model.BlockRepresentation).order_by(model.BlockRepresentation.Order)
    blocks = q.filter(model.BlockRepresentation.View == details.Id).all()
    for block in blocks:
      self.block_repr[block.Id] = block
      self.addBlock(block, add_connections=False)
    
    # Add connections that are relevant for this view.
    hidden = self.session.query(model.HiddenConnection.Connection).\
                 filter(model.HiddenConnection.View == self.details.Id).all()
    q = self.session.query(model.Connection)
    known_blocks = set([d.Block for d in self.block_repr.values()])
    for connection in q:
      # Skip connections that are hidden
      if connection.Id in hidden:
        continue
      # Show connections for which start and end are drawn
      if connection.Start in known_blocks and \
         connection.End in known_blocks:
        self.addConnection(connection)
#
    # self.fp_details is sorted by 'order'.
    all_details = self.session.query(model.FpToView, model.FunctionPoint).\
                     filter(model.FpToView.View==self.details.Id).\
                     filter(model.FunctionPoint.Id == model.FpToView.FunctionPoint).\
                     order_by(model.FpToView.Order.asc()).all()
    
    self.processActions(all_details)
    self.fpviews = {}   # model.FpToView : FunctionPoint
    
    for fpview, fpdetails in all_details:        
      self.addAction(fpview, fpdetails)
      
    sql.event.listen(model.FunctionPoint, 'after_update', self.onFpUpdate)
    sql.event.listen(model.FpToView, 'after_update', self.onFp2UseCaseUpdate)
    
    self.sortBlocks(blocks)
  
  def sortFunctionPoints(self):
    ''' Sort the details in all_details. This is a list of (FpToView, FunctionPoint) tuples.
        Sort them by the Order element of the FpToView record.
    '''
    self.all_details = sorted(self.all_details, key=lambda x:x[0].Order)
    self.processActions(self.all_details)
    
  def sortBlocks(self, blocks):
    for count, b in enumerate(blocks):
      graphic = self.block_items[b.Id]
      graphic.setZValue(count)

  @staticmethod
  def processActions(all_details):
    ''' Determines how many actions are listed for each element.
    '''
    connections = {}
    blocks = {}
    for fp1, fp2 in all_details:
      connection = fp2.Connection
      block = fp2.Block
      if connection:
        others = connections.get(connection, 0)
        fp1.order_on_target = others
        connections[connection] = others + 1
      else:
        others = blocks.get(block, 0)
        fp1.order_on_target = others
        blocks[block] = others + 1
    

  def addAction(self, fpview, fpdetails, parent_item = None):
    ''' Attach an action to the given item.
    
        fpview: an model.FpToView instance.
        pfdetails: the associated model.FunctionPoint instance.

    '''
    self.all_details.append((fpview, fpdetails))
    self.known_fps.add(fpdetails)
    self.processActions(self.all_details)
    fp = fpdetails
    if parent_item is None:
      if fp.Connection != None:
        # FIXME: This does not work for multiple connections...
        parent_items = [self.connection_items[fp.Connection]]
      else:
        block_reprs = [b.Id for b in self.block_repr.values() if b.Block==fp.Block]
        parent_items = [self.block_items[rep] for rep in block_reprs]
    else:
      parent_items = [parent_item]
    for parent in parent_items:
      item = FunctionPoint(fpview, fp, parent)
      self.fpviews[fpview] = item
      self.addItem(item)

  def dragEnterEvent(self, event):
    if event.mimeData().hasFormat(MIME_TYPE):
      event.accept()
      
  def dragMoveEvent(self, event):
    if event.mimeData().hasFormat(MIME_TYPE):
      event.accept()
  
  def dropEvent(self, event):
    details = self.drop2Details(event)
    print 'got:', details

    coods = event.scenePos()
    
    if isinstance(details, model.ArchitectureBlock):
      new_details = model.BlockRepresentation(Block=details.Id,
                                              View = self.details.Id,
                                              x = coods.x(),
                                              y = coods.y(),
                                              height = BLOCK_HEIGHT,
                                              width = BLOCK_WIDTH,
                                              Order = len(self.block_repr))
      self.session.add(new_details)
      self.session.commit()
      
      self.addBlock(new_details)
    
  def addBlock(self, rep_details, add_connections=True):
    self.block_repr[rep_details.Id] = rep_details
    coods = QtCore.QPointF(rep_details.x, rep_details.y)
    # FIXME: use a relationship in the model for this!
    block_details = self.session.query(model.ArchitectureBlock).\
                          filter(model.ArchitectureBlock.Id == rep_details.Block).first()
    block = BlockItem(rep_details, block_details)
    self.addItem(block)
    block.setPos(coods)
    block.setColor()
    
    self.block_details[rep_details.Id] = block_details
    self.block_items[rep_details.Id] = block
    
    # TODO: Add any connections to the new block, if there are
    if add_connections:
      blocks_in_view = self.session.query(model.BlockRepresentation.Block).\
                          filter(model.BlockRepresentation.View==self.details.Id)
      blocks_in_view = [b[0] for b in blocks_in_view]
      for con in self.session.query(model.Connection).filter(model.Connection.Start==block_details.Id).\
                    filter(model.Connection.End.in_(blocks_in_view)):
        self.addConnection(con)
      for con in self.session.query(model.Connection).filter(model.Connection.End==block_details.Id).\
                    filter(model.Connection.Start.in_(blocks_in_view)):
        self.addConnection(con)
        
            
  def addConnection(self, connection):
    # Find BlockRepr ids for all starts and ends
    starts = [i for i, block in self.block_details.iteritems() if block.Id==connection.Start]
    ends   = [i for i, block in self.block_details.iteritems() if block.Id==connection.End]
    for s_id in starts:
      start = self.block_repr[s_id]
      for e_id in ends:
        end = self.block_repr[e_id]
        line = QtCore.QLineF(start.x + start.width/2, 
                             start.y + start.height/2,
                             end.x + end.width/2,
                             end.y + end.height/2)
        item = Connection(connection, start, end, line)
        item.setPen(ConnectionPen)
        z = min(self.block_items[s_id].zValue(), self.block_items[e_id].zValue())
        item.setZValue(z-0.1)
        item.setFlag(QtGui.QGraphicsItem.ItemIsSelectable)
        self.addItem(item)
        self.connections[connection.Id] = connection
        self.connection_items[connection.Id] = item
    
  def mouseMoveEvent(self, event):
    QtGui.QGraphicsScene.mouseMoveEvent(self, event)
    
    # Move the derived items when dragging
    if event.buttons() != QtCore.Qt.LeftButton:
      return
    
    items = self.selectedItems()

    if len(items) > 0:
      # Update the details without committing the changes
      for it in items:
        it.details.x = it.x()
        it.details.y = it.y()
      # Move the connections as well.
      # For simplicity, just move all connections. If this takes too much time, 
      # in future this can be optimized.
      for it in self.connection_items.itervalues():
        start, end = it.start, it.end
        line = QtCore.QLineF(start.x + start.width/2, 
                     start.y + start.height/2,
                     end.x + end.width/2,
                     end.y + end.height/2)
        it.setLine(line)
        z = min(self.block_items[start.Id].zValue(),
                self.block_items[end.Id].zValue())
        it.setZValue(z-0.1)
        
      for d, it in self.fpviews.iteritems():
        if not it in items:
          it.move()
        
        
  def onFpUpdate(self, mapper, connection, target):
    # Check if the detail is being shown
    if target not in self.known_fps:
      return
    for view, fp in self.all_details:
      if fp == target:
        self.fpviews[view].move()

  def onFp2UseCaseUpdate(self, mapper, connection, target):
    # Check if the fp2uc is actually shown in this view
    if target not in self.fpviews:
      return
    self.fpviews[target].move()

  def exportSvg(self):
    # Order the items in their Z-order.
    # Export the svg items as XML nodes
    tmpl = '''<svg><g transform="translate($x, $y)">
    $lines
    $blocks
    $fps
    </g></svg>'''

    blocks = '\n'.join([b.exportSvg() for b in self.block_items.values()])
    fps    = '\n'.join([fp.exportSvg() for fp in self.fpviews.values()])
    lines  = '\n'.join([c.exportSvg() for c in self.connection_items.values()])
    rect = self.sceneRect()
    x = -rect.x()
    y = -rect.y()
    result = string.Template(tmpl).substitute(locals())
    return result
    
      
      

def mkMenu(definition, parent):
  ''' Utility to create a menu from a configuration structure.'''
  menu = QtGui.QMenu(parent)
  for action, func in definition:
    if action == '---':
      menu.addSeparator()
    else:
      a = QtGui.QAction(action, parent)
      menu.addAction(a)
      a.triggered.connect(func)
  return menu


class TwoDView(QtGui.QGraphicsView):
  ''' The TwoDView renders the MyScene, showing the architecture view.
  '''
  selectedItemChanged = QtCore.pyqtSignal(object)
  def __init__(self, details, drop2Details, session, block_colors):
    scene = MyScene(details, drop2Details, session, block_colors)
    QtGui.QGraphicsView.__init__(self, scene)
    self.block_colors = block_colors
    for hint in [QtGui.QPainter.Antialiasing, QtGui.QPainter.TextAntialiasing]:
      self.setRenderHint(hint)
    self.setAcceptDrops(True)
    #self.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)
    #a = QtGui.QAction('Nieuw Blok', self)
    #self.addAction(a)
    #a.triggered.connect(self.onAddBlock)
    # TODO: Implement copy to use case
    self.menu_noitem = mkMenu([('Nieuw Blok', self.onAddBlock),
                               ('Copieer naar Nieuw View', self.onCopyToUseCase),
                               ('Exporteer als SVG', self.exportSvg)], self)
    self.menu_action = mkMenu([('Eerder', self.onAdvance),
                    ('Later', self.onRetard),
                    ('---', None),
                    ('Detailleer Actie', self.onRefineAction),
                    ('Verwijder Actie', self.onDeleteItem)], self)
    self.scene = scene
    self.details = details
    self.last_rmouse_click = None
    self.session = session
    self.scene.selectionChanged.connect(self.onSelectionChanged)
    
  def mouseReleaseEvent(self, event):
    ''' The mouse press event is intercepted in order to remember the position
    of the right-click action, when adding an object using a right-click menu.
    '''
    if event.button() == QtCore.Qt.RightButton:
      self.last_rmouse_click = event.pos()
      self.contextMenuEvent(event)
    else:
      # Forward left-click mouse events.
      QtGui.QGraphicsView.mouseReleaseEvent(self, event)
      
  def menuActionDetails(self, details, definition=None):
    ''' Construct the details for a right-click menu that
    allows the addition of function points.
    '''
    if definition is None:
      definition = []

    definition += [('Nieuwe Actie', self.onNewAction),
                  ('---', None)]
    def bind(n):
      ''' Utility: bind a menu action trigger to the right function '''
      return lambda: self.addExistingAction(n)
    #for fp in details.FunctionPoints:
    for fp in details.FunctionPoints:
      definition.append((fp.Name, bind(fp.Id)))
    return definition
  
  def contextMenuEvent(self, event):
    ''' Called when the context menu is requested in the view.
        The function checks what the mouse was pointing at when the menu
        was requested, so the right menu can be shown.
    '''
    item = self.itemAt(event.pos())
    details, _ = getDetails(item, dont_raise=True)
    #print item.details, item.details.Name
    menu = None
    if item is None:
      menu = self.menu_noitem
    elif isinstance(details, model.Connection):
      # Create the menu for a connection
      definition = self.menuActionDetails(details, [('Verbergen', self.onHideConnection),
                                                    ('---', None),
                                                    ('Verwijder Verbinding', self.onDeleteItem)])
      menu = mkMenu(definition, self)
    elif isinstance(details, model.FpToView):
      # Use the action menu
      menu = self.menu_action
    else:
      # It must be an architecture block.
      # If two blocks are selected, allow them to be connected.
      if len(self.scene.selectedItems()) == 2:
        definition = [('Verbind blokken', self.onConnect)]
      else:
        block = self.scene.block_details[details.Id]
        definition = self.menuActionDetails(block, [('Move Up', self.onRetard),
                                                    ('Move Down', self.onAdvance),
                                                    ('---', None),
                                                    ('Verwijder Blok', self.onDeleteItem)])
      menu = mkMenu(definition, self)
    menu.exec_(self.mapToGlobal(event.pos()))
    event.accept()
    
  def onConnect(self):
    ''' Called when two blocks are connected '''
    # FIXME: check if this connection should run between more blocks.
    items = self.scene.selectedItems()
    if len(items) != 2:
      return
    
    source, target = [getDetails(i)[0].Block for i in items]
    details = model.Connection(Start=source, End=target)
    self.session.add(details)
    self.session.commit()
    self.scene.addConnection(details)
    self.scene.clearSelection()

  def onAddBlock(self, triggered):
    ''' Called to add a new block to the view. '''
    text, ok = QtGui.QInputDialog.getText(self, 'Nieuw Blok',
                                "Welke naam krijgt het blok?")
    if not ok:
      return
    
    text = str(text)
    block_details = model.ArchitectureBlock(Name=text, Parent=self.details.Parent)
    self.session.add(block_details)
    self.session.commit()
    pos = self.mapToScene(self.last_rmouse_click)
    repr_details = model.BlockRepresentation(Block=block_details.Id, View=self.details.Id, 
                                             x=pos.x(), y=pos.y(), 
                                             Order = len(self.scene.block_repr),
                                             width=BLOCK_WIDTH, height=BLOCK_HEIGHT)
    self.session.add(repr_details)
    self.session.commit()
    self.scene.addBlock(repr_details)
    
  def onDeleteItem(self):
    ''' Deletes the block located at the last known right-click
    location.
    '''
    item = self.itemAt(self.last_rmouse_click)
    details, item = getDetails(item)
    to_remove = [item]
    # Use a scoped session to ensure the consistency of the database.
    with model.sessionScope(self.session) as session:
      # When deleting a block, remove the connections as well.
      # Deleting a block means only the representation is removed from the view,
      # so remove only the line, leave the connection in the model.
      if isinstance(details, model.BlockRepresentation):
        block_id = details.Block
        for con in self.scene.connections.values():
          if con.Start == block_id or con.End == block_id:
            to_remove.append(self.scene.connection_items[con.Id])
      elif isinstance(details, model.Connection):
        session.delete(details)
        # When deleting connections, check that there are no functionpoints on it.
        nr_fps = self.session.query(sql.func.count(model.FunctionPoint.Id)).\
                        filter(model.FunctionPoint.Connection==details.Id).one()[0]
        if nr_fps > 0:
          raise RuntimeError('Can not delete connection: has function points!')
      session.delete(details)
    for it in to_remove:
      self.scene.removeItem(it)
      
  def onHideConnection(self):
    ''' Hide a connection. '''
    item = self.itemAt(self.last_rmouse_click)
    connection, item = getDetails(item)
    if not isinstance(connection, model.Connection):
      return
    
    # Check if there are any actions on this connection in this view
    actions = self.session.query(model.FpToView, model.FunctionPoint.Connection).\
                   filter(model.FpToView.View==self.details.Id).\
                   filter(model.FunctionPoint.Connection.Id==connection.Id).all()
    if len(actions) > 0:
      # Ask the user if he is sure.
      MB = QtGui.QMessageBox
      reply = MB.question(self, 'Weet u het zeker?',
                                 'De verbinding heeft acties in deze view. Toch verbergen?',
                                 MB.Yes, MB.No)
      if reply != MB.Yes:
        return

    # Start a transaction
    with model.sessionScope(self.session) as session:
      # Add the 'Hide' record.
      session.add(model.HiddenConnection(View=self.details.Id, Connection=connection.Id))
      # Delete any fp2uc records (leave the functionpoints!)
      for a in actions:
        session.delete(a)
      # Delete the connection item.
      self.scene.removeItem(item)
    
  def onNewAction(self):
    ''' Create a new action and add it to either a connection or a block. '''
    text, ok = QtGui.QInputDialog.getText(self, 'Nieuwe Actie',
                                "Welke naam krijgt de actie?")
    if not ok:
      return
    
    # Create the new action ('Function Point')
    item = self.itemAt(self.last_rmouse_click)
    details, item = getDetails(item)
    # Determine if adding an action to a block or to a connection.
    if isinstance(details, model.Connection):
      fp = model.FunctionPoint(Name=str(text), Connection=details.Id, Parent=None)
    else:
      fp = model.FunctionPoint(Name=str(text), Block=details.Block, Parent=None)
    self.session.add(fp)
    self.session.commit()
    # Also create the link to the FP in the view.
    self.addExistingAction(fp.Id)
    
  def addExistingAction(self, fp_id):
    ''' Show an already existing action in the current view. '''
    order=self.session.query(sql.func.count(model.FpToView.Id)).\
                             filter(model.FpToView.View==self.details.Id).one()[0]
    fp = self.session.query(model.FunctionPoint).filter(model.FunctionPoint.Id==fp_id).one()
    fp2uc = model.FpToView(FunctionPoint=fp_id, View=self.details.Id, Order=order)
    self.session.add(fp2uc)
    self.session.commit()
    _, item = getDetails(self.itemAt(self.last_rmouse_click))
    self.scene.addAction(fp2uc, fp, item)
    
  def onAdvance(self, triggered, retard=False):
    ''' Called to move either a block or an action forward. '''
    item, _ = getDetails(self.itemAt(self.last_rmouse_click))
    cls = item.__class__
    items = self.session.query(cls).\
                               filter(cls.View==item.View).\
                               order_by(cls.Order).all()
    # Find out where this item is
    index = items.index(item)
    if not retard:
      # Check if it is already the first item
      if index == 0:
        return
      # Swap them
      items[index], items[index-1] = items[index-1], items[index]
    else:
      # Check if it already is the final item
      if index == len(items)-1:
        return
      # Swap the relevant items
      items[index], items[index+1] = items[index+1], items[index]
    # Normalize the orders
    for count, it in enumerate(items):
      it.Order = count
    self.session.commit()
    if cls == model.FpToView:
      self.scene.sortFunctionPoints()
    else:
      self.scene.sortBlocks(items)
      
  def onRetard(self, triggered):
    ''' Called to move either a block or an action backwards. '''
    self.onAdvance(triggered, retard=True)

  def normalizeActions(self):
    ''' Cause the order field for the actions in the view to be normalised.'''
    actions = self.session.query(model.FpToView).\
                               filter(model.FpToView.View==self.details.Id).\
                               order_by(model.FpToView.Order.asc()).all()
    for count, details in enumerate(actions):
      details.Order = count
    self.session.commit()
    
  def onRefineAction(self):
    ''' Called when the user wants to refine an action in a Use Case. '''
    fpview, _ = getDetails(self.itemAt(self.last_rmouse_click))
    # Add a new view that refers to the indicated function point
    fp = fpview.FunctionPoint
    view = fpview.View
    
    new_view = model.View(Name=fp.Name, Parent=view, Refinement=fp)
    self.session.add(new_view)
    # TODO: Cause the new view to be opened!
    
    
  def setColor(self, Id):
    ''' Set the color for the currently selected blocks '''
    for item in self.scene.selectedItems():
      if isinstance(item, BlockItem):
        item.details.Color = Id
        item.setColor()
    self.session.commit()
    
  def onCopyToUseCase(self):
    ''' Called to copy a view, to be the basis for a new view. '''
    # TODO: Implement copy to use case
    pass
  
  
  def onSelectionChanged(self):
    ''' Called when the items that are selected is changed.
        Causes a signal to be published so that the details viewer can be uipdated.'''
    # Check one item is selected.
    items = self.scene.selectedItems()
    if len(items) == 1:
      details = items[0].details
      if details.__class__ == model.BlockRepresentation:
        details = self.scene.block_details[details.Id]
      elif details.__class__ == model.FpToView:
        details = self.session.query(model.FunctionPoint).\
                       filter(model.FunctionPoint.Id == details.FunctionPoint).one()
      self.selectedItemChanged.emit(details)

  def exportSvg(self):
    print self.scene.exportSvg()

  