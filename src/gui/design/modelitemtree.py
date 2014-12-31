'''
Created on May 11, 2014

@author: EHWAAL
'''


from weakref import proxy
from functools import partial

from PyQt4 import QtGui, QtCore
import model
from sqlalchemy import or_, func
from sqlalchemy.orm import subqueryload
from gui.util import mkMenu



class Finder(object):
  def __init__(self, tree, edit, button):
    self.tree = proxy(tree)
    self.edit = edit
    self.button = button
    self.txt = ''
    self.button.clicked.connect(self.onButton)

  def onButton(self):
    txt = str(self.edit.text())
    self.txt = txt
    if txt:
      self.tree.applyFilter(txt)
    else:
      self.tree.populateTree()


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


class ModelItemTree(QtGui.QTreeWidget):
  def __init__(self, *args, **kwds):
    QtGui.QTreeWidget.__init__(self, *args, **kwds)
    self.model_class = None
    self.session_parent = None
    self.filter = None
    self.detail_items = {}
    self.item_actions = [('Delete', self.deleteHandler)]
    self.std_actions = [('Add', self.addHandler)]

  def contextMenuEvent(self, ev):
    index = self.indexAt(ev.pos())
    if index.isValid():
      actions = self.item_actions
    else:
      actions = self.std_actions
    menu = mkMenu(actions, self.session_parent)
    menu.exec_(self.mapToGlobal(ev.pos()))

  def setFinder(self, edit, button):
    self.filter = Finder(self, edit, button)
  def setModelClass(self, cls, parent):
    self.setContextMenuPolicy(QtCore.Qt.DefaultContextMenu)
    self.model_class = cls
    self.session_parent = parent

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

  def populateTree(self):
    self.clear()
    self.detail_items = {}
    cls = self.model_class
    session = self.session_parent.session
    # Get all elements to be shown in the tree, eager load all Children.
    root_items = session.query(cls).options(subqueryload(cls.Children)).all()
    # Filter so that only the root items remain.
    # The Children are reachable through the 'Children' field.
    root_items = [r for r in root_items if r.Parent==None]

    def addChildren(parent_item):
      # Add all children
      for c in parent_item.details.Children:
        item = createTreeItem(c)
        self.detail_items[c.Id] = item
        parent_item.addChild(item)
        addChildren(item)

    # Add the root items and their children
    for r in root_items:
      item = createTreeItem(r)
      self.detail_items[r.Id] = item
      self.addTopLevelItem(item)
      addChildren(item)


  def applyFilter(self, txt):
    ''' Show only items that match the filter.
    '''
    # Find all elements that match the filter in either name or description.
    # Stupid SQL wildcard requires me to try four different patterns.
    session = self.session_parent.session
    c = self.model_class
    txt = txt.upper()
    fltr1 = '%s'%txt
    fltr2 = '%s%%'%txt
    fltr3 = '%%%s'%txt
    fltr4 = '%%%s%%'%txt

    n = func.upper(c.Name)
    d = func.upper(c.Description)
    all = session.query(c).filter(or_(n.like(fltr1),
                                      n.like(fltr2),
                                      n.like(fltr3),
                                      n.like(fltr4),
                                      d.like(fltr1),
                                      d.like(fltr2),
                                      d.like(fltr3),
                                      d.like(fltr4))).all()
    # Make items to show these records, without the hierarchy
    self.clear()
    self.detail_items = {}
    for rec in all:
      item = createTreeItem(rec)
      self.detail_items[rec.Id] = item
      self.addTopLevelItem(item)

