'''
Created on Feb 7, 2014

@author: EHWAAL
'''

from PyQt4 import QtGui, QtCore
from details_editor import DetailsViewer
import model
from util import mkMenu

class ViewerBase(QtGui.QWidget):
  def __init__(self, parent, decorator):
    QtGui.QWidget.__init__(self, parent)
    self.ui = decorator()
    self.ui.setupUi(self)
    
    self.session = None

  def getSession(self):
    return self.session
  
  def clean(self):
    raise NotImplementedError()
  
  def open(self, session):
    self.session = session
    self.clean()
    
  def openView(self, details):
    ''' Called when an items needs to be viewed.
    '''
    pass
      


class ViewerWithDetailsBase(ViewerBase):
  def __init__(self, *args):
    ViewerBase.__init__(self, *args)
    self.detail_items = {}    
    self.details_viewer = None

  def openDetailsViewer(self, details, read_only=False):
    ''' Called when a different block is selected. '''
    # Ensure there is no other viewer
    self.closeDetailsViewer()
    # Check there is something to view
    if details is None:
      return
    # Create a new viewer.
    widget = DetailsViewer(self.ui.areaDetails, details, self.session, read_only)
    self.ui.areaDetails.setWidget(widget)
    widget.show()
    self.ui.areaDetails.show()
    self.details_viewer = widget
    widget.open_view.connect(self.openView)
    
  def closeDetailsViewer(self):
    if self.details_viewer:
      # Automatically commit any changes from the editor
      with model.sessionScope(self.session):
        widget = self.ui.areaDetails.takeWidget()
        widget.close()
        self.ui.areaDetails.hide()
        self.details_viewer = None



###############################################################################
##
def createTreeItem(details):
  item = QtGui.QTreeWidgetItem()
  item.setText(0, details.Name)
  item.setFlags(QtCore.Qt.ItemFlags(QtCore.Qt.ItemIsEditable + 
                    QtCore.Qt.ItemIsDragEnabled + 
                    QtCore.Qt.ItemIsDropEnabled + 
                    QtCore.Qt.ItemIsSelectable + 
                    QtCore.Qt.ItemIsEnabled))
  item.details = details
  return item

def makeModelItemTree(tree, model_class, parent):
  ''' Turn a normal TreeWidget into a viewer for model items.
  '''
  # Create wrapper functions for event handlers
  def addHandler(checked=False):
    items = tree.selectedItems()
    if len(items) == 1:
      # Not a top-level item: try to find the ID of the item.
      parent_item = items[0].details.Id
    else:
      parent_item = None
      
    details = model_class(Name='new item',
                          Parent=parent_item)
    with model.sessionScope(parent.getSession()) as session:
      session.add(details)
    # As the session is closed, the new item is added to this tree.
    # Cause the item to be selected.
    parent.onTreeItemAdded(details)
    
      
  def deleteHandler(checked=False):
    session = parent.getSession()
    MB = QtGui.QMessageBox
    items = tree.selectedItems()
    if len(items) == 0:
      return
    reply = MB.question(parent, 'Weet u het zeker?',
                               'De geselecteerde items verwijderen?',
                               MB.Yes, MB.No)
    if reply != MB.Yes:
      return
    
    for item in items:
      # Check the item has no children
      if item.childCount() > 0:
        MB.critical(parent, 'Sorry', "Het item heeft kinderen", MB.Ok)
        return
      parent_item = item.parent()
      if parent_item:
        index = parent_item.indexOfChild(item)
        parent_item.takeChild(index)
      else:
        index = tree.indexOfTopLevelItem(item)
        tree.takeTopLevelItem(index)
      
      if isinstance(item.details, model.ArchitectureBlock):
        # check if there are connections or views of this block.
        if session.query(model.BlockRepresentation).\
                        filter(model.BlockRepresentation.Block==item.details.Id).count() != 0:
          reply = MB.question(parent, 'Weet u het zeker?',
                                     'Het blok wordt gebruikt in views. Toch verwijderen?',
                                     MB.Yes, MB.No)
          if reply != MB.Yes:
            return
        
      session.delete(item.details)
    try:
      session.commit()
    except:
      session.rollback()
      raise
    
  # Install the handlers as menu items
  actions = [('Add', addHandler, {}), ('Delete', deleteHandler, {})]
  mkMenu(actions, parent, tree)

  # Cause items to be deselected when clicking in empty space.
  def createHandler(widget):
    def myPress(ev):
      widget.clearSelection()
      QtGui.QTreeWidget.mousePressEvent(widget, ev)
  tree.mousePressEvent = createHandler(tree)
  
  def dropEvent(event):
    ''' Replaces the dropEvent handler for the tree widgets.
    '''
    # Check that the drop is from within the widget.
    if event.source() != tree:
      event.ignore()
      return
    # Find out which item is dropped on.
    item = tree.itemAt(event.pos())
    # Check it is not dropped on itself
    if item in tree.selectedItems():
      event.ignore()
      return
    # Change the action from IGNORE to MOVE
    event.setDropAction(QtCore.Qt.MoveAction)
    # Get the current list of children
    children = None
    if item:
      children = [item.child(i) for i in range(item.childCount())]
    # Do the drop
    result = QtGui.QTreeWidget.dropEvent(tree, event)
    # Find out which item was dropped on, and administrate the changes.
    with model.sessionScope(parent.getSession()):
      if item:
        new_children = [item.child(i) for i in range(item.childCount())]
        new_children = [ch for ch in new_children if ch not in children]
        parent_item = item.details.Id
        for ch in new_children:
          ch.details.Parent = parent_item
      else:
        # The dragged item has become a top-level item.
        # Find out which item it was from the mime data.
        details = parent.drop2Details(event)
        details.Parent = None

  # Override the dropEvent handler.
  tree.dropEvent = dropEvent
  
  # Cause the parent to be informed when details are changed.
  tree.itemChanged.connect(parent.onItemChanged)



class ViewerWithTreeBase(ViewerWithDetailsBase):
  def __init__(self, *args):
    ViewerWithDetailsBase.__init__(self, *args)
    self.tree_models = None
    
  def open(self, session):
    ViewerWithDetailsBase.open(self, session)
    # Populate the tree lists.    
    for widget, cls in self.tree_models.iteritems():
      root_items = self.session.query(cls).filter(cls.Parent==None).all()
      self.populateTree(widget, root_items)

  def populateTree(self, widget, root_items):
    def addChildren(parent_item):
      # Add all children
      for c in parent_item.details.Children:
        item = createTreeItem(c)
        self.detail_items.setdefault(widget, {})[c.Id] = item
        parent_item.addChild(item)
        addChildren(item)
    # Add the root items and their children
    for r in root_items:
      item = createTreeItem(r)
      self.detail_items.setdefault(widget, {})[r.Id] = item
      widget.addTopLevelItem(item)
      addChildren(item)
      
  def onTreeItemClicked(self, item):
    ''' Called when the user clicks on an item in a tree view.
        Causes a details viewer to be opened for the tiems.
    '''
    self.openDetailsViewer(item.details)
      
  def onTreeItemAdded(self, details):
    ''' Called when a new item was created in a tree.
        Cause the focus to shift to the details editor for this item.
    '''
    # First cause the details editor to be shown.
    self.onItemSelectionChanged(details)
    # Set the focus to the 'Name' field for the editor
    self.details_viewer.setFocusOnName()


