'''
Created on Sep 26, 2013

@author: EHWAAL

Copyright (C) 2014 Evert van de Waal
This program is released under the conditions of the GNU General Public License.
'''

import model
import string
from urlparse import urlparse
import os.path
from model.config import currentFile
from PyQt4 import QtGui, QtCore
import sqlalchemy as sql
from primitives_2d import Block, Text, Line, NO_POS, extractSvgGradients
from connector import Connection
from styles import Styles, Style
from controller import Controller, cmnds


# TODO: Allow copy - paste of blocks between views.
# TODO: Separate a functionpoint sequence number from its Z-order.
# TODO: Support re-ordering multiple items.
# TODO: children are contained by and on top of parents.
# TODO: Have two types of view: one where actions shown on a link are from the connection (Architecture),
#       and one where the actions shown on a link are from an object (UML).
# FIXME: rename architecture block is not shown in open viewer.
# FIXME: delete architecture block is not shown in viewer.

MIME_TYPE = 'application/x-qabstractitemmodeldatalist'

theController = Controller.get()


class NoDetailsFound(Exception):
  ''' Exception that is raised when looking for a widget at a certain place 
      and not finding anything.
  '''
  pass

class BlockItem(Block):
  ''' Representation of an architecture block.
  '''
  ROLE = 'archblock'
  def __init__(self, style, rep_details, block_details):
    self.details = rep_details
    self.block_details = block_details
    Block.__init__(self, rep_details, style, self.details.style_role, block_details.Name)
    self.applyStyle()
  def setRole(self, role):
    ''' Called by the style editing mechanism when the user changes the role. 
        The role is here only the user-determined part, and does not include the
        hard-coded part from ROLE.'''
    self.details.style_role = role
    Block.setRole(self, role)
    self.applyStyle()
  def menuFactory(self, view):
    ''' Factory function for creating a right-click menu.

    :param view: The view where the right-click menu is requested.
    :return: An instance of QtGui.QMenu
    '''
    details = self.block_details
    def bind(n):
      ''' Utility: bind a menu action trigger to the right function '''
      return lambda: view.addExistingAction(n, details.Id)

    definition = list(view.standard_menu_def)
    # Add the dynamic menu items
    nr_items = len(view.scene.selectedItems())
    if nr_items in [0, 1]:
      definition += [('Create New Child Block', view.onAddChildBlock),
                     ('New Action', view.onNewAction),
                     ('---', None)]
      for fp in details.FunctionPoints:
        definition.append((fp.Name, bind(fp.Id)))
    if nr_items == 2:
      definition = [('Connect blocks', view.onConnect)]

    return mkMenu(definition, view)


class AnnotationItem(Block):
  ''' Representation of an annotation. '''
  ROLE = 'annotation'
  def __init__(self, style, details):
    # TODO: Take into account the anchor position
    self.details = details
    Block.__init__(self, details, style, details.style_role, details.Description)
    self.applyStyle()
  def setRole(self, role):
    ''' Called by the style editing mechanism when the user changes the role. 
        The role is here only the user-determined part, and does not include the
        hard-coded part from ROLE.'''
    self.details.style_role = role
    Block.setRole(self, role)
    self.applyStyle()
  def menuFactory(self, view):
    ''' Factory function for creating a right-click menu.

    :param view: The view where the right-click menu is requested.
    :return: An instance of QtGui.QMenu
    '''
    details = self.details
    return mkMenu(view.standard_menu_def, view)

    
class FunctionPoint(Text):
  ROLE = 'functionpoint'
  def __init__(self, details, fp, anchor, style):
    if details.SequenceNr:
      text = '%s: %s'%(details.SequenceNr, fp.Name)
    else:
      text = fp.Name
    role = details.style_role
    self.anchor = anchor
    self.details = details
    self.fp = fp
    self.arrow = None
    Text.__init__(self, text, style, role, apply=False)
    
    self.setFlag(QtGui.QGraphicsItem.ItemIsSelectable)
    self.setFlag(QtGui.QGraphicsItem.ItemIsMovable)
    
    if isinstance(self.anchor, BlockItem):
      self.arrow = None
    else:
      # Add the arrow.
      length = style.getFloat('%s-arrow-%s-length'%(role, self.ROLE), 1.0)
      self.arrow = Line(-10*length, 0, 0, 0, self, style, (role, self.ROLE))

    self.applyStyle()

  def applyStyle(self):
    Text.applyStyle(self)
    if self.arrow:
      self.arrow.applyStyle()
    self.updatePos()
  def setRole(self, role):
    ''' Called by the style editing mechanism when the user changes the role. 
        The role is here only the user-determined part, and does not include the
        hard-coded part from ROLE.'''
    self.details.style_role = role
    self.arrow.setRole(role)
    Text.setRole(self, role)
    self.applyStyle()
    
  def exportSvg(self):
    tmplt = '''
               <g transform="translate($x,$y)">
                 $arrow
                 $txt
               </g>
    '''
    arrow=self.arrow.exportSvg() if self.arrow else ''
    txt = Text.exportSvg(self, NO_POS)  # The text position is the position of the group.
    d = dict(text=str(self.text.toPlainText()),
             x=self.x(), y=self.y(),
             txt=txt,
             arrow = arrow)
    xml = string.Template(tmplt).substitute(d)
    return xml

  def anchorPos(self):
    x, y = self.anchor.fpPos()
    order = self.details.order_on_target
    x += 10*order
    y -= 20*order
    return x, y
    
  def updatePos(self):
    p = self.parentItem()
    if self.details.SequenceNr:
      text = '%s: %s'%(self.details.SequenceNr, self.fp.Name)
    else:
      text = self.fp.Name
    self.setText(text)
    x, y = self.anchorPos()
    x += self.details.Xoffset
    y += self.details.Yoffset
    self.setPos(x,y)
    #print 'background rect:', p.rect(), p.pos(), self.pos()
    if self.arrow:
      angle = -self.anchor.line().angle()
      if self.fp.isResponse:
        angle += 180.0
      self.arrow.setRotation(angle)
      self.arrow.setPos(self.style.getOffset('%s-arrow-%s'%(self.role, self.ROLE), 
                                        default=[-10,10]))
      
  def mouseReleaseEvent(self, event):
    Text.mouseReleaseEvent(self, event)
    self.scene().session.commit()
      
  def mouseMoveEvent(self, event):
    # Get the current position
    p = self.pos()
    Text.mouseMoveEvent(self, event)
    
    # If moved, make it permanent
    if self.pos() != p:
      np = self.pos()
      self.details.Xoffset += np.x() - p.x()
      self.details.Yoffset += np.y() - p.y()

  def menuFactory(self, view):
    ''' Factory function for creating a right-click menu.

    :param view: The view where the right-click menu is requested.
    :return: An instance of QtGui.QMenu
    '''
    definition = list(view.standard_menu_def)
    return mkMenu(definition, view)


def getDetails(item, dont_raise=False):
  while item:
    if hasattr(item, 'details'):
      return item.details, item
    item = item.parentItem()
  if dont_raise:
    return None, None
  raise NoDetailsFound('Kon geen details vinden')
      

class MyScene(QtGui.QGraphicsScene):
  SELECT_PEN = QtGui.QPen()
  SELECT_PEN.setStyle(QtCore.Qt.DashLine)
  def __init__(self, details, drop2Details, session):
    '''
    drop2Details: a callback function that finds the details
    belonging to the item that was dropped.
    '''
    QtGui.QGraphicsScene.__init__(self)
    self.drop2Details = drop2Details
    self.session = session
    self.details = details

    # TODO: Remove all references to data bits except self.anchors
    self.connections = {}   # Connection.Id : Connection
    self.connection_items = {} # Connection.Id : connection item.
    self.all_details = []   # An ordered list of (fptoview, functionpoint) tuples
    self.known_fps = set()
    
    self.connectLine = None
    
    self.styles = Styles.style_sheet.getStyle(details.style)
    self.styles.subscribe(lambda _: self.applyStyle())
    
    # Add the existing blocks
    blocks, annotations, connections, actions = theController.getViewElements(self.details)
    self.anchors = {}    # Anchor.Id : Item tuples
    self.block_details = {} # ArchBlock.Id : ArchBlock
    self.block_items = {}   # ArchBlock.Id : BlockItem

    for block in blocks:
      self.anchors[block.Id] = block
      self.addBlock(block, add_connections=False)

    # Add the existing annotations
    for a in annotations:
      self.addAnnotation(a)
    
    # Add existing connections
    for connection in connections:
      self.anchors[connection.Id] = connection
      self.addConnection(connection)

    # Add the actions
    self.processActions(actions)
    self.fpviews = {}   # model.FpRepresentation : FunctionPoint
    self.last_leftclick_pos = None
    self.select_rect = None
    
    for fpview, fpdetails in actions:
      self.addAction(fpview, fpdetails)


    sql.event.listen(model.FunctionPoint, 'after_update', self.onFpUpdate)
    sql.event.listen(model.FpRepresentation, 'after_update', self.onFp2UseCaseUpdate)
    sql.event.listen(model.Annotation, 'after_update', self.onAnnotationUpdate)
    
    self.sortItems()
    
  def close(self):
    ''' Called when the TwoDView closes. '''
    sql.event.remove(model.FunctionPoint, 'after_update', self.onFpUpdate)
    sql.event.remove(model.FpRepresentation, 'after_update', self.onFp2UseCaseUpdate)
    sql.event.remove(model.Annotation, 'after_update', self.onAnnotationUpdate)
    
  def applyStyle(self):
    ''' Re-apply the styles to all items. '''
    for i in self.items():
      if hasattr(i, 'applyStyle'):
        i.applyStyle()
  
  def sortFunctionPoints(self):
    ''' Sort the details in all_details. This is a list of (FpRepresentation, FunctionPoint) tuples.
        Sort them by the Order element of the FpRepresentation record.
    '''
    self.all_details = sorted(self.all_details, key=lambda x:x[0].Order)
    self.processActions(self.all_details)
    
  def sortItems(self):
    for item in self.anchors.values():
      order = item.details.Order
      order = order if order is not None else 0.0
      item.setZValue(order)

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
    

  def addAction(self, fpview, fpdetails, anchor_item = None):
    ''' Attach an action to the given item.
    
        fpview: an model.FpRepresentation instance.
        fpdetails: the associated model.FunctionPoint instance.
        anchor_item: A QGraphicsItem that is the parent for this fp.

    '''
    self.all_details.append((fpview, fpdetails))
    self.known_fps.add(fpdetails)
    self.processActions(self.all_details)
    fp = fpdetails
    # Find the anchor, if not already specified.
    if anchor_item is None:
      anchor_item = self.anchors[fpview.AnchorPoint]
    item = FunctionPoint(fpview, fp, anchor_item, self.styles)
    self.fpviews[fpview] = item
    self.addItem(item)
    self.anchors[fpview.Id] = item

  def dragEnterEvent(self, event):
    if event.mimeData().hasFormat(MIME_TYPE):
      event.accept()
      
  def dragMoveEvent(self, event):
    if event.mimeData().hasFormat(MIME_TYPE):
      event.accept()
  
  def dropEvent(self, event):
    details = self.drop2Details(event)

    coods = event.scenePos()
    order = len(self.anchors)
    new_details = theController.execute(cmnds.AddBlockRepresentation(details, self.details.Id,
                                               coods, order))
    if new_details:
      self.addBlock(new_details)
      self.selectItem(new_details)

  def selectItem(self, details):
    ''' Ensure a specific item is selected, and all other items de-selected.
    '''
    for i in self.items():
      sel = True if getattr(i, 'details', None) == details else False
      i.setSelected(sel)
    
  def addBlock(self, rep_details, add_connections=True):
    coods = QtCore.QPointF(rep_details.x, rep_details.y)
    block_details = rep_details.theBlock
    block = BlockItem(self.styles, rep_details, block_details)
    self.anchors[rep_details.Id] = block
    self.addItem(block)
    block.setPos(coods)
    
    self.block_details[rep_details.Id] = block_details
    self.block_items[rep_details.Id] = block
        
  def addAnnotation(self, details):
    coods = QtCore.QPointF(details.x, details.y)
    block = AnnotationItem(self.styles, details)
    details.item = block
    self.addItem(block)
    block.setPos(coods)
    self.anchors[details.Id] = block
            
  def addConnection(self, connection_repr):
    # Find BlockRepr ids for all starts and ends
    start = self.anchors[connection_repr.Start]
    end = self.anchors[connection_repr.End]
    item = Connection(connection_repr, start, end, self.styles)
    item.setFlag(QtGui.QGraphicsItem.ItemIsSelectable)
    item.applyStyle()
    self.addItem(item)
    self.anchors[connection_repr.Id] = item
    self.connections[connection_repr.Id] = connection_repr
    self.connection_items[connection_repr.Id] = item

  def mousePressEvent(self, event):
    ''' Record the position of the most recent mouse click, for area select.
    '''
    if event.button() == QtCore.Qt.LeftButton:
      self.last_leftclick_pos = event.scenePos()
    else:
      self.last_leftclick_pos = None
    return QtGui.QGraphicsScene.mousePressEvent(self, event)

  def mouseReleaseEvent(self, event):
    ''' Handle a possible area select
    '''
    if event.button() == QtCore.Qt.LeftButton:
      if self.select_rect is not None:
        # Do an area select
        area = QtGui.QPainterPath()
        area.addRect(self.select_rect.boundingRect())
        self.setSelectionArea(area)
        # Delete the selection rectangle
        self.removeItem(self.select_rect)
        self.select_rect = None

    self.last_leftclick_pos = None

    return QtGui.QGraphicsScene.mouseReleaseEvent(self, event)

    
  def mouseMoveEvent(self, event):
    QtGui.QGraphicsScene.mouseMoveEvent(self, event)

    items = self.selectedItems()

    if len(items) > 0:
      # Move the derived items when dragging
      if event.buttons() != QtCore.Qt.LeftButton:
        return
      # Update the details without committing the changes
      for it in items:
        # Only update the model: the positions of the graphics item were already changed.
        if not hasattr(it, 'updatePos'):
          # Don't update positions of items that do not support that, like lines.
          continue
        it.updatePos()
        
      # Move function points as well.
      for d, it in self.fpviews.iteritems():
        if not it in items:
          it.updatePos()

    if len(items) == 0:
      if self.last_leftclick_pos is None:
        self.last_leftclick_pos = event.scenePos()
      # Draw the box for region select.
      if event.buttons() != QtCore.Qt.LeftButton:
        return

      if self.select_rect is None:
        # Create a rectangle for showing the region being selected
        self.select_rect = QtGui.QGraphicsRectItem(scene = self)
        self.select_rect.setPen(self.SELECT_PEN)

      # Update the position of the selection rectangle
      x = min(event.scenePos().x(), self.last_leftclick_pos.x())
      y = min(event.scenePos().y(), self.last_leftclick_pos.y())
      width = abs(event.scenePos().x() - self.last_leftclick_pos.x())
      height = abs(event.scenePos().y() - self.last_leftclick_pos.y())
      self.select_rect.setRect(x, y, width, height)

        
  def onFpUpdate(self, mapper, connection, target):
    # Check if the detail is being shown
    if target not in self.known_fps:
      return
    for view, fp in self.all_details:
      if fp == target:
        self.fpviews[view].updatePos()

  def onFp2UseCaseUpdate(self, mapper, connection, target):
    # Check if the fp2uc is actually shown in this view
    if target not in self.fpviews:
      return
    self.fpviews[target].updatePos()
    
  def onAnnotationUpdate(self, mapper, connection, target):
    if hasattr(target, 'item'):
      target.item.text.setText(target.Description)

  def exportSvg(self):
    ''' Determine the SVG representation of this view,
        and return it as a string.
        
        String templates are filled-in to create the SVG code,
        no formal XML parsing is applied.
    '''
    # TODO: Order the items in their Z-order.
    tmpl = '''<?xml version="1.0" encoding="UTF-8" standalone="no"?>
    <!-- Created with Archtool -->
    <svg    xmlns:dc="http://purl.org/dc/elements/1.1/"
   xmlns:cc="http://web.resource.org/cc/"
   xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
   xmlns:svg="http://www.w3.org/2000/svg"
   xmlns="http://www.w3.org/2000/svg">
   <g transform="translate($x, $y)">
      $gradients
      $lines
      $blocks
      $fps
      $annotations
    </g></svg>'''

    connections = [a for a in self.anchors.values() if isinstance(a, Connection)]
    annotations = [a for a in self.anchors.values() if isinstance(a, AnnotationItem)]
    gradients = '\n'.join([extractSvgGradients(self.styles, t) for t in [BlockItem.ROLE,
                                                                         AnnotationItem.ROLE]])
    gradients += extractSvgGradients(self.styles, AnnotationItem.ROLE)
    blocks = '\n'.join([b.exportSvg() for b in self.block_items.values()])
    fps    = '\n'.join([fp.exportSvg() for fp in self.fpviews.values()])
    lines  = '\n'.join([c.exportSvg() for c in connections])
    annotations = '\n'.join([a.exportSvg() for a in annotations])
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

  MOVE_UP     = 1
  MOVE_DOWN   = 2
  MOVE_TOP    = 3
  MOVE_BOTTOM = 4

  def __init__(self, details, drop2Details, session):
    scene = MyScene(details, drop2Details, session)
    QtGui.QGraphicsView.__init__(self, scene)
    for hint in [QtGui.QPainter.Antialiasing, QtGui.QPainter.TextAntialiasing]:
      self.setRenderHint(hint)
    self.setAcceptDrops(True)
    #self.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)
    #a = QtGui.QAction('Nieuw Blok', self)
    #self.addAction(a)
    #a.triggered.connect(self.onAddBlock)
    # TODO: Implement copy to use case
    self.menu_noitem = mkMenu([('New Block', self.onAddBlock),
                               ('New Annotation', self.onAddAnnotation),
                               ('Copieer naar Nieuw View', self.onCopyToUseCase),
                               ('Export as SVG', self.exportSvg)], self)
    up = lambda _:self.onChangeItemOrder(self.MOVE_UP)
    down = lambda _:self.onChangeItemOrder(self.MOVE_DOWN)
    top = lambda _:self.onChangeItemOrder(self.MOVE_TOP)
    bottom = lambda _:self.onChangeItemOrder(self.MOVE_BOTTOM)
    self.standard_menu_def = [('Move Up', up),
                              ('Move Down', down),
                              ('Move Top', top),
                              ('Move Bottom', bottom),
                              ('---', None),
                              ('Delete', self.onDeleteItem)]
    self.scene = scene
    self.details = details
    self.last_rmouse_click = None
    self.session = session
    self.scene.selectionChanged.connect(self.onSelectionChanged)
    self.selection_order = []
    
  def close(self):
    ''' Overload of the QWidget close function. '''
    self.scene.close()
    QtGui.QGraphicsView.close(self)
    
  def mouseReleaseEvent(self, event):
    ''' The mouse press event is intercepted in order to remember the position
    of the right-click action, when adding an object using a right-click menu.
    '''
    print 'Mouses release at', event.pos()
    if event.button() == QtCore.Qt.RightButton:
      self.contextMenuEvent(event)
      event.accept()
    else:
      # Forward left-click mouse events.
      QtGui.QGraphicsView.mouseReleaseEvent(self, event)

  @staticmethod
  def mkMenu(*args):
    return mkMenu(*args)

  def contextMenuEvent(self, event):
    ''' Called when the context menu is requested in the view.
        The function checks what the mouse was pointing at when the menu
        was requested, so the right menu can be shown.
    '''
    self.last_rmouse_click = event.pos()
    print 'right-click at:', self.last_rmouse_click
    item = self.itemAt(event.pos())
    details, item = getDetails(item, dont_raise=True)
    #print item.details, item.details.Name
    menu = None
    if item is None:
      menu = self.menu_noitem
    else:
      menu = item.menuFactory(self)
    menu.exec_(self.mapToGlobal(event.pos()))
    event.accept()
    
  def onConnect(self):
    ''' Called when two blocks are connected '''
    items = self.scene.selectedItems()
    if len(items) != 2:
      return

    source, target = [getDetails(i)[0] for i in self.selection_order]
    details = theController.execute(cmnds.AddConnectionRepresentation(source, target,
                                                                      self.details.Id))
    self.scene.addConnection(details)
    self.scene.clearSelection()

  def onAddBlock(self, triggered, parent=None):
    ''' Called to add a new block to the view. '''
    text, ok = QtGui.QInputDialog.getText(self, 'New Block',
                                "Please specify the block name.")
    if not ok:
      return
    
    text = str(text)
    pos = self.mapToScene(self.last_rmouse_click)
    block_details = theController.execute(cmnds.AddNewBlock(text, parent))
    repr_details = theController.execute(cmnds.AddBlockRepresentation(block_details,
                                                                      self.details.Id,
                                                                      pos,
                                                                      len(self.scene.anchors)))
    self.scene.addBlock(repr_details)
    self.scene.selectItem(repr_details)

  def onAddChildBlock(self, triggered=False):
    ''' Called to create a new child block.
    '''
    item = self.itemAt(self.last_rmouse_click)
    parent, item = getDetails(item)
    self.onAddBlock(False, parent=parent)


  def onReverseConnection(self, triggered=False):
    ''' Called when the user wants to reverse the direction of a connection.
    '''
    # Retrieve the ConnectionRepresentation
    item = self.itemAt(self.last_rmouse_click)
    details, item = getDetails(item)
    details.Start, details.End = details.End, details.Start

    # Redraw the connection
    self.scene.removeItem(item)
    self.scene.addConnection(details)

    
  def onAddAnnotation(self, triggered=False):
    ''' Called to add a new annotation to the view. '''
    pos = self.mapToScene(self.last_rmouse_click)
    item = self.itemAt(self.last_rmouse_click)
    anchor_id = None
    pos = self.mapToScene(self.last_rmouse_click)

    if item:
      anchor, item = getDetails(item)
      anchor_id = anchor.Id
      pos = QtCore.QPointF(0.0, 0.0)

    details = theController.execute(cmnds.AddAnnotation(self.details.Id, pos, anchor_id,
                                                        len(self.scene.anchors)))
    self.scene.addAnnotation(details)
    self.scene.selectItem(details)


  def keyPressEvent(self, ev):
    ''' Overload for the standard Widget key press event handler
    '''
    # Catch the 'delete' key
    if ev.key() == QtCore.Qt.Key_Delete:
      ev.accept()
      # Check if anything is selected
      if len(self.scene.selectedItems()) == 0:
        return
      # Ask the user if he wants to delete
      q = QtGui.QMessageBox.question(self, 'Confirm Delete', 'Are you sure you want to delete the '
              'current selected items?',
              buttons=QtGui.QMessageBox.Ok | QtGui.QMessageBox.Cancel,
              defaultButton=QtGui.QMessageBox.Ok)
      if q != QtGui.QMessageBox.Ok:
        return
      self.onDelete()
      return
    return QtGui.QGraphicsView.keyPressEvent(self, ev)


  def deleteItems(self, items):
    ''' Delete a set of items
    '''
    to_remove = [] # A list of all graphic items to remove.
    # Use a scoped session to ensure the consistency of the database.
    with model.sessionScope(self.session) as session:
      for item in items:
        to_remove.append(item)
        # When deleting a block, remove the connections as well.
        # Deleting a block means only the representation is removed from the view,
        # so remove only the line, leave the connection in the model.
        details = item.details
        if isinstance(details, model.BlockRepresentation):
          block_id = details.Id
          for con in self.scene.connections.values():
            if con.Start == block_id or con.End == block_id:
              to_remove.append(self.scene.connection_items[con.Id])
        elif isinstance(details, model.ConnectionRepresentation):
          session.delete(details)
          # When deleting connections, check that there are no functionpoints on it.
          nr_fps = self.session.query(sql.func.count(model.FunctionPoint.Id)).\
                          filter(model.FunctionPoint.Connection==details.Id).one()[0]
          if nr_fps > 0:
            raise RuntimeError('Can not delete connection: has function points!')

        # Also check for annotations anchored on the item!
        session.delete(details)
    # No errors: actually delete the items from the drawing.
    for it in to_remove:
      self.scene.removeItem(it)


  def onDelete(self):
    ''' Delete the items that are currently selected.
    '''
    items = [getDetails(i)[1] for i in self.scene.selectedItems()]
    self.deleteItems(items)
    
    
  def onDeleteItem(self):
    ''' Deletes the block located at the last known right-click
    location.
    '''
    item = self.itemAt(self.last_rmouse_click)
    details, item = getDetails(item)
    to_remove = [item]
    self.deleteItems(to_remove)


  def onNewAction(self):
    ''' Create a new action and add it to either a connection or a block. '''
    text, ok = QtGui.QInputDialog.getText(self, 'Nieuwe Actie',
                                "Welke naam krijgt de actie?")
    if not ok:
      return
    
    # Create the new action ('Function Point')
    item = self.itemAt(self.last_rmouse_click)
    details, item = getDetails(item)
    fp = theController.execute(cmnds.AddNewAction(details, str(text)))
    # Also create the link to the FP in the view.
    self.addExistingAction(fp.Id, details.Id)
    
  def addExistingAction(self, fp_id, anchor_id):
    ''' Show an already existing action in the current view. '''
    _, item = getDetails(self.itemAt(self.last_rmouse_click))
    fprepr, fp = theController.execute(cmnds.AddExistingAction(self.details, fp_id, anchor_id))

    # Cause the action to be shown in the View.
    self.scene.addAction(fprepr, fp, item)
    self.scene.selectItem(fprepr)
    
  def onChangeItemOrder(self, direction):
    ''' Called to move a drawing item in the Z direction. This function supports
        moving to top, bottom, up and down.
    '''
    item, _ = getDetails(self.itemAt(self.last_rmouse_click))
    #print 'Original item order:', item.Order, item.Id
    A = model.Anchor
    # The Order determines the Z location. Zero is the bottom.
    items = self.session.query(A).\
                               filter(A.View==item.View).\
                               order_by(A.Order).all()
    # Find out where this item is
    index = items.index(item)
    # Check if the item can be moved
    if direction in [self.MOVE_DOWN, self.MOVE_BOTTOM]:
      if index == 0:
        return
    elif index == len(items)-1:
      return

    # Perform the actual move
    if direction == self.MOVE_DOWN:
      items[index], items[index-1] = items[index-1], items[index]
    elif direction == self.MOVE_UP:
      items[index], items[index+1] = items[index+1], items[index]
    elif direction == self.MOVE_BOTTOM:
      items.pop(index)
      items.insert(0, item)
    elif direction == self.MOVE_TOP:
      items.pop(index)
      items.append(item)

    # Normalize the orders
    for count, it in enumerate(items):
      it.Order = count
    # Commit them to the database and diagram.
    self.session.commit()
    self.scene.sortItems()

  def normalizeActions(self):
    ''' Cause the order field for the actions in the view to be normalised.'''
    actions = self.session.query(model.FpRepresentation).\
                               filter(model.FpRepresentation.View==self.details.Id).\
                               order_by(model.FpRepresentation.Order.asc()).all()
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
      elif details.__class__ == model.FpRepresentation:
        details = self.session.query(model.FunctionPoint).\
                       filter(model.FunctionPoint.Id == details.FunctionPoint).one()
      elif details.__class__ == model.ConnectionRepresentation:
        details = details.theConnection
      self.selectedItemChanged.emit(details)
      self.selection_order = items
    elif len(items) == 0:
      self.selection_order = []
    elif len(items) >= 2:
      for i in items:
        if i not in self.selection_order:
          self.selection_order.append(i)
    Style.current_style.set(self.scene.styles)
    Style.current_object.set(items)

  def exportSvg(self):
    ''' Called when the user wants to export a view as SVG file.
        The SVG is stored as a file containing the model and view names.
    '''
    svg = self.scene.exportSvg()
    path = self.details.getParents()
    model_url = currentFile()
    model_name = urlparse(model_url)[2]
    dirname, basename = os.path.split(model_name)
    fname = '%s.%s.svg'%(basename, '.'.join([p.Name for p in path]))
    fname = os.path.join(dirname, fname)
    with open(fname, 'w') as f:
      f.write(svg)
    QtGui.QMessageBox.information(self, 'SVG Exported',
                                 'The diagram was exported as %s'%fname)

