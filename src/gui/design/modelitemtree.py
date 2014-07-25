'''
Created on May 11, 2014

@author: EHWAAL
'''



from PyQt4 import QtGui, QtCore
import model
from gui.util import mkMenu



class ModelItemTree(QtGui.QTreeWidget):
  def __init__(self, *args, **kwds):
    QtGui.QTreeWidget.__init__(self, *args, **kwds)
    self.model_class = None
    self.session_parent = None
  def setModelClass(self, cls, parent):
    self.model_class = cls
    self.session_parent = parent

    # Install the handlers as menu items
    actions = [('Add', self.addHandler, {}), ('Delete', self.deleteHandler, {})]
    mkMenu(actions, parent, self)

    # Cause the parent to be informed when details are changed.
    self.itemChanged.connect(parent.onItemChanged)

  def addHandler(self, checked=False):
    ''' Add a new instance of the model class.
    '''
    items = self.selectedItems()
    if len(items) == 1:
      # Not a top-level item: try to find the ID of the item.
      parent_item = items[0].details.Id
    else:
      parent_item = None

    details = self.model_class(Name='new item',
                          Parent=parent_item)
    with model.sessionScope(self.session_parent.getSession()) as session:
      session.add(details)
    # As the session is closed, the new item is added to this tree.
    # Cause the item to be selected.
    self.session_parent.onTreeItemAdded(details)


  def deleteHandler(self, checked=False):
    session = self.session_parent.getSession()
    MB = QtGui.QMessageBox
    items = self.selectedItems()
    if len(items) == 0:
      return
    reply = MB.question(self.session_parent, 'Weet u het zeker?',
                               'De geselecteerde items verwijderen?',
                               MB.Yes, MB.No)
    if reply != MB.Yes:
      return

    for item in items:
      # Check the item has no children
      if item.childCount() > 0:
        MB.critical(self.session_parent, 'Sorry', "Het item heeft kinderen", MB.Ok)
        return
      parent_item = item.parent()
      if parent_item:
        index = parent_item.indexOfChild(item)
        parent_item.takeChild(index)
      else:
        index = self.indexOfTopLevelItem(item)
        self.takeTopLevelItem(index)

      if isinstance(item.details, model.ArchitectureBlock):
        # check if there are connections or views of this block.
        if session.query(model.BlockRepresentation).\
                        filter(model.BlockRepresentation.Block==item.details.Id).count() != 0:
          reply = MB.question(self.session_parent, 'Weet u het zeker?',
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

  # Cause items to be deselected when clicking in empty space.
  def mousePressEvent(self, ev):
    self.clearSelection()
    QtGui.QTreeWidget.mousePressEvent(self, ev)


  def dropEvent(self, event):
    ''' Replaces the dropEvent handler for the tree widgets.
    '''
    # Check that the drop is from within the widget.
    if event.source() != self:
      event.ignore()
      return
    # Find out which item is dropped on.
    item = self.itemAt(event.pos())
    # Check it is not dropped on itself
    if item in self.selectedItems():
      event.ignore()
      return
    # Change the action from IGNORE to MOVE
    event.setDropAction(QtCore.Qt.MoveAction)
    # Get the current list of children
    children = None
    if item:
      children = [item.child(i) for i in range(item.childCount())]
    # Do the drop
    result = QtGui.QTreeWidget.dropEvent(self, event)
    # Find out which item was dropped on, and administrate the changes.
    with model.sessionScope(self.session_parent.getSession()):
      if item:
        new_children = [item.child(i) for i in range(item.childCount())]
        new_children = [ch for ch in new_children if ch not in children]
        parent_item = item.details.Id
        for ch in new_children:
          ch.details.Parent = parent_item
      else:
        # The dragged item has become a top-level item.
        # Find out which item it was from the mime data.
        details = self.session_parent.drop2Details(event)
        details.Parent = None



