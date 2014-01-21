'''
Created on Sep 26, 2013

@author: EHWAAL
'''

from PyQt4 import QtCore, QtGui
from design import ArchitectureViewForm, ProjectViewForm
import model
from util import bindLambda, mkMenu
from view_2d import TwoDView, MIME_TYPE
from details_editor import DetailsViewer, EffortOverview, WorkerOverview
from req_export import exportRequirementQuestions, exportRequirementsOverview
from sqlalchemy import event
import logging


DEFAULT_COLORS = ['#ffffff', 'Cornflower Blue', '#00529c', 
                  '#f2f2f2', '#838383']

# TODO: move the makeModelItemTree to a MyTree, and promote the relevant widgets.


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

###############################################################################
##

class ViewerBase(ArchitectureViewForm[1]):
  def __init__(self, parent, decorator):
    QtGui.QWidget.__init__(self, parent)
    self.ui = decorator()
    self.ui.setupUi(self)
    
    self.session = None
    self.detail_items = {}    
    self.details_viewer = None
    self.tree_models = None

  def getSession(self):
    return self.session
  
  def clean(self):
    raise NotImplementedError()
  
  def open(self, session):
    self.session = session
    self.clean()
    
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
      
  def openDetailsViewer(self, details):
    ''' Called when a different block is selected. '''
    # Ensure there is no other viewer
    self.closeDetailsViewer()
    # Check there is something to view
    if details is None:
      return
    # Create a new viewer.
    widget = DetailsViewer(self.ui.areaDetails, details, self.session)
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

  def onTreeItemClicked(self, item):
    ''' Called when the user clicks on an item in a tree view.
        Causes a details viewer to be opened for the tiems.
    '''
    self.openDetailsViewer(item.details)
      
  def onItemSelectionChanged(self, details):
    ''' Called when the current selection in a 2D view changes.
    '''
    self.openDetailsViewer(details)
    
  def openView(self, details):
    ''' Called when an items needs to be viewed.
    '''
    pass
      

  
###############################################################################
##

class PlanningView(ViewerBase):
  def __init__(self, parent):
    ViewerBase.__init__(self, parent, ProjectViewForm[0])
    
    tree_models = {self.ui.treeProjects:model.Project}
    self.tree_models = tree_models
    for widget, model_class in tree_models.iteritems():
      makeModelItemTree(widget, model_class, self)
      widget.itemClicked.connect(self.onTreeItemClicked)
      
    # Add a context menu to the workers viewer
    actions = [('Add', self.onAddWorker, {}), ('Delete', self.onDeleteWorker, {})]
    mkMenu(actions, self, self.ui.lstWorkers)
    
    # If a project is double-clicked, the planning overview is shown.
    self.ui.treeProjects.itemDoubleClicked.connect(self.onViewPlanning)
    # If a worker is double-clicked, the worker overview is shown.
    self.ui.lstWorkers.itemDoubleClicked.connect(self.onViewWorker)
    # If a worker is selected, his/her details are shown.
    self.ui.lstWorkers.itemClicked.connect(lambda item: self.openDetailsViewer(item.details))

  def clean(self):
    pass

  def open(self, session):
    ViewerBase.open(self, session)
    
    # Populate the workers list.
    all = self.session.query(model.Worker).all()
    for details in all:
      item = QtGui.QListWidgetItem(details.Name, self.ui.lstWorkers)
      item.details = details
      
  def onItemChanged(self, item, column):
    # TODO: Implement
    pass
  
  def onViewPlanning(self, item, column):
    project = item.details
    workers = self.session.query(model.Worker).all()
    
    widget = EffortOverview(self, project, workers)
    self.ui.areaOverview.setWidget(widget)
    widget.show()
    self.ui.areaOverview.show()
  
  def onViewWorker(self, item):
    worker = item.details
    projects = self.session.query(model.Project).all()
    
    widget = WorkerOverview(self, worker, projects)
    self.ui.areaOverview.setWidget(widget)
    widget.show()
    self.ui.areaOverview.show()
    
  def onAddWorker(self, triggered=False):
    text, ok = QtGui.QInputDialog.getText(self, 'Nieuwe Werker',
                                "Welke naam krijgt de nieuwe werker?")
    if not ok:
      return
    
    worker = model.Worker(Name=str(text))
    with model.sessionScope(self.session) as session:
      self.session.add(worker)

    item = QtGui.QListWidgetItem(worker.Name, self.ui.lstWorkers)
    item.details = worker
    
  def onDeleteWorker(self, triggered=False):
    selection = self.ui.lstWorkers.selectedItems()
    if len(selection) == 0:
      return
    
    with model.sessionScope(self.session) as session:
      for item in selection:
        self.session.delete(item.details)
    for item in selection:
      index = self.ui.lstWorkers.row(item)
      _ = self.ui.lstWorkers.takeItem(index)

###############################################################################
##

class ArchitectureView(ViewerBase):
  ''' Viewer showing requirements and Use Cases.
  '''
  REGTBL_COLUMNS = ['Name', 'Priority', 'Status']
  DoubleClickItem = QtCore.pyqtSignal(object)

  def __init__(self, parent):
    ViewerBase.__init__(self, parent, ArchitectureViewForm[0])
    
    self.color_buttons = []
    
    # Make the context menus for the tree widgets.
    tree_models = {self.ui.treeBlocks:model.ArchitectureBlock,
                     self.ui.treeUseCases:model.View,
                     self.ui.treeRequirements:model.Requirement}
    self.tree_models = tree_models

    for widget, model_class in tree_models.iteritems():
      makeModelItemTree(widget, model_class, self)
      widget.itemClicked.connect(self.onTreeItemClicked)
    self.ui.treeUseCases.itemDoubleClicked.connect(self.onView)
            
    self.ui.tabGraphicViews.tabCloseRequested.connect(self.onTabCloseRequested)
    
    self.fillFilterBoxes()
    
    self.ui.tblRequirements.cellClicked.connect(self.onCellClicked)
        
    # Add database hooks to properly update when items are added.
    for cls in [model.ArchitectureBlock, model.View, model.Requirement]:
      event.listen(cls, 'after_update', self.onDetailUpdate)
      event.listen(cls, 'after_insert', self.onDetailInsert)
      #FIXME: also handle deletes.

  def clean(self):
    ''' Create a new database and connect to it.
      No check for outstanding changes necessary: all changes are
      stored immediatly.
    '''
    # Clean up all tree widgets
    for widget in [self.ui.treeBlocks, self.ui.treeUseCases, 
                   self.ui.treeRequirements, self.ui.tblRequirements]:
      widget.clear()
      
    # Close all views in the tab window
    while self.ui.tabGraphicViews.count() > 0:
      self.onTabCloseRequested(0)
      
    # Clean up the internal object caches
    self.detail_items = {self.ui.treeBlocks:{},
                         self.ui.treeUseCases:{},
                         self.ui.treeRequirements:{},
                         self.ui.tblRequirements:{}} # ID, QTreeWidgetItem tuples
    
    self.tbl_requirements = {} # tbl item : requirement details.
    self.closeDetailsViewer()



  def open(self, session):
    ViewerBase.open(self, session)
    
    # Populate the requirements table
    if False:
      all = self.session.query(model.Requirement).all()
      for req in all:
        self.addTableElement(req)

    # Load the pallette
    colors = self.session.query(model.ColorPalette).all()
    if not colors:
      colors = [model.ColorPalette(Color=color) for color in DEFAULT_COLORS]
      self.session.add_all(colors)
      self.session.commit()
    self.block_colors = {c.Id:QtGui.QColor(c.Color) for c in colors}
    self.showPaletteButtons()
    
  def onItemChanged(self, item, column):
    new_name = str(item.text(0))
    if new_name != item.details.Name:
      item.details.Name = new_name
      # Ensure the changes are committed.
      with model.sessionScope(self.session):
        pass

  def onView(self, item):
    ''' Called when the user double-clicks on a View.
    '''
    details = item.details
    self.openView(details)
    
  def openView(self, details):
    ''' Open a 2D viewer for a 'View' item.
    
        Used as a slot for QT Signals.
    '''
    # Check if this view is already open.
    for i in range(self.ui.tabGraphicViews.count()):
      view = self.ui.tabGraphicViews.widget(i)
      if view.details == details:
        # The view is already shown: bring it to the front.
        self.ui.tabGraphicViews.setCurrentIndex(i)
        return
    # Add a new tab
    viewer = TwoDView(details, self.drop2Details, self.session, self.block_colors)
    self.ui.tabGraphicViews.addTab(viewer, details.Name)
    self.ui.tabGraphicViews.setCurrentWidget(viewer)
    viewer.selectedItemChanged.connect(self.onItemSelectionChanged)

    
  def onTabCloseRequested(self, index):
    widget = self.ui.tabGraphicViews.widget(index)
    self.ui.tabGraphicViews.removeTab(index)
    widget.close()
    
  def onSetColor(self, triggered, color_id):
    ''' Called when the user clicks on one of the color buttons.
    calls the current view (if any) to set the color.
    '''
    # Get the current view
    view = self.ui.tabGraphicViews.currentWidget()
    if not view:
      return
    
    view.setColor(color_id)
    

  def fillFilterBoxes(self):
    ''' Fill the boxes that are used to determine a filter with the items
    that can be filtered on: the different states and the different priorities.
    '''
    self.req_stat_filters = []
    self.req_prio_filters = []
    for box, options, l in [
              (self.ui.grpReqStatFilter, model.REQUIREMENTS_STATES, 
               self.req_stat_filters),
              (self.ui.grpReqPrioFilter, model.PRIORITIES, 
               self.req_prio_filters)]:
      layout = box.layout()
      for status in options:
        w = QtGui.QCheckBox(box)
        w.setChecked(False)
        w.setText(status)
        layout.addWidget(w)
        w.stateChanged.connect(self.onFilterRequirements)
        l.append(w)
        
        
    lbls = model.Requirement.getFields() + ['Status']
    lbls.remove('Description')
    lbls.remove('Id')
    self.ui.tblRequirements.setHorizontalHeaderLabels(self.REGTBL_COLUMNS)
    
  def showPaletteButtons(self):
    ''' Read the palette colors, and show them as buttons in the viewer.
    '''
    for btn in self.color_buttons:
      btn.close()

    colors = self.session.query(model.ColorPalette).all()

    buttons = []
    for c in colors:
      btn = QtGui.QToolButton(self.ui.layoutWidget)
      name = self.block_colors[c.Id].name()
      btn.setStyleSheet("background-color:\"%s\";"%name)
      btn.setText('')
      self.ui.horizontalLayout_2.addWidget(btn)
      btn.clicked.connect(bindLambda(self.onSetColor, {'color_id':c.Id}))
      menu = QtGui.QMenu(self)
      a = QtGui.QAction('Change Color', self)
      a.triggered.connect(bindLambda(self.onChangePalette, {'color_id':c.Id,
                                                            'btn':btn}))
      btn.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)
      btn.addAction(a)
      buttons.append(btn)
    self.color_buttons = buttons

        
  def onChangePalette(self, triggered, color_id, btn):
    ''' Called when the user changes one of the colors in the palette.
    '''
    color = QtGui.QColorDialog.getColor(self.block_colors[color_id], self)
    self.block_colors[color_id] = color
    name =color.name()
    btn.setStyleSheet("background-color:\"%s\";"%name)
    c = self.session.query(model.ColorPalette).filter(model.ColorPalette.Id == color_id).one()
    c.Color = str(name)
    self.session.commit()
    

  def onFilterRequirements(self, value):
    prios  = [s for s, w in zip(model.PRIORITIES, self.req_prio_filters) if w.isChecked()]
    states = [s for s, w in zip(model.REQUIREMENTS_STATES, self.req_stat_filters) if w.isChecked()]
    prios = set(prios)
    states = set(states)
    self.filterRequirementsTree(prios, states)
    self.filterRequirementsTable(prios, states)
    
  def filterRequirementsTable(self, prios, states):
    # Clear the table and build it anew
    self.ui.tblRequirements.clearContents()
    requirements = []
    for requirement in self.session.query(model.Requirement):
      # Apply the filter
      if requirement.Priority not in prios:
        continue
      if len(requirement.StateChanges) == 0:
        if model.REQUIREMENTS_STATES[0] not in states:
          continue
      elif requirement.StateChanges[0].Status not in states:
        continue
      # This requirement passes the filter: add it to the table.
      requirements.append(requirement)
      
    # Set the dimensions of the table
    self.ui.tblRequirements.setRowCount(len(requirements))
    # Fill the table
    for row, req in enumerate(requirements):
      self.ui.tblRequirements.setItem(row, 0, QtGui.QTableWidgetItem(req.Name))
      if req.Description:
        self.ui.tblRequirements.setItem(row, 1, QtGui.QTableWidgetItem(req.Description))
      self.ui.tblRequirements.setItem(row, 2, QtGui.QTableWidgetItem(req.Priority))
      if len(req.StateChanges) > 0:
        state = req.StateChanges[0]
        self.ui.tblRequirements.setItem(row, 3, QtGui.QTableWidgetItem(state.Status))
        if state.TimeRemaining:
          self.ui.tblRequirements.setItem(row, 4, QtGui.QTableWidgetItem(str(state.TimeRemaining)))
        else:
          self.ui.tblRequirements.setItem(row, 4, QtGui.QTableWidgetItem('-'))
      else:
        self.ui.tblRequirements.setItem(row, 3, QtGui.QTableWidgetItem(model.REQUIREMENTS_STATES[0]))
        self.ui.tblRequirements.setItem(row, 4, QtGui.QTableWidgetItem('-'))
      self.tbl_requirements[self.ui.tblRequirements.item(row, 0)] = req
      
  def onCellClicked(self, row, column):
    item = self.ui.tblRequirements.item(row, 0)
    requirement = self.tbl_requirements[item]
    if requirement:
      self.onItemSelectionChanged(requirement)
    
  def filterRequirementsTree(self, prios, states):
    for item in self.detail_items[self.ui.treeRequirements].values():
      disable = False
      if item.details.Priority not in prios:
        disable = True
      if len(item.details.StateChanges) == 0:
        disable = model.PRIORITIES[0] not in prios
      elif item.details.StateChanges[0].Status not in states:
        disable = True
      if item.childCount() > 0:
        # Never disable parent requirements.
        disable = False
      item.setDisabled(disable)

  def onRequirementReport(self, checked, widget):
    items = widget.selectedItems()
    if len(items) == 0:
      return
    
    fname = str(QtGui.QFileDialog.getSaveFileName(self, "Save report to which file?", 
                                                  '.', "*.rst"))
    if fname == '':
      return
    out = file(fname, 'w')
    
    chapters = [i.details for i in items]
    exportRequirementsOverview(self.session, out, chapters)
    
  def onRequirementQuestions(self, checked, widget):
    items = widget.selectedItems()
    if len(items) == 0:
      return
    
    fname = str(QtGui.QFileDialog.getSaveFileName(self, "Save report to which file?", 
                                                  '.', "*.rst"))
    if fname == '':
      return
    out = file(fname, 'w')
    
    chapters = [i.details for i in items]
    exportRequirementQuestions(self.session, out, chapters)    

  def getTreeWidget(self, details):
    if isinstance(details, model.ArchitectureBlock):
      return self.ui.treeBlocks
    elif isinstance(details, model.View):
      return self.ui.treeUseCases
    elif isinstance(details, model.Requirement):
      return self.ui.treeRequirements
    return None
  
  def drop2Details(self, event):
    ''' This function determines which item was dropped when a view
    receives a drop event.
    
    The drop event originated from one of the three tree widgets.
    '''
    data = event.mimeData().data(MIME_TYPE)
    stream  = QtCore.QDataStream(data, QtCore.QIODevice.ReadOnly)
    stream.setByteOrder(QtCore.QDataStream.BigEndian)

    # Decode the drop data
    # First 4 32-bits integers representing row, column, nr of items and Qt.ItemDataRole
    # are stored
    _row = stream.readInt32()
    _column = stream.readInt32()
    _map_items = stream.readInt32()
    _key = stream.readInt32()    
    # Next is a QVariant of the data set as UserRole to the TreeWidgetItem 
    drop_path = QtCore.QVariant()
    stream >> drop_path #pylint: disable=W0104
    
    source = event.source()
    items = source.findItems(drop_path.toString(), 
                  QtCore.Qt.MatchFixedString|QtCore.Qt.MatchRecursive, 0)
    return items[0].details
    
    
  def onDetailUpdate(self, mapper, connection, target):
    ''' Called when a change to the database model is committed.
    '''
    widget = self.getTreeWidget(target)
    if widget is None:
      loggin.error('onDetailUpdate called for wrong target %r'%target)
      return
    
    item = self.detail_items[widget].get(target.Id, None)
    if item is None:
      logging.error('Detail not shown in tree: %r'%target)
      return
    old_text = str(item.text(0))
    if old_text != target.Name:
      item.setText(0, target.Name)
      
  def onDetailInsert(self, mapper, connection, target):
    ''' Called when a new item is inserted in the database.
    '''
    self.addItem(target)

  def addItem(self, details, edit=False):
    ''' Add an item to a tree widget.
    '''
    widget = self.getTreeWidget(details)
    if widget is None:
      return
    new_item = QtGui.QTreeWidgetItem()
    new_item.setText(0, details.Name)
    new_item.setFlags(QtCore.Qt.ItemFlags(QtCore.Qt.ItemIsEditable + 
                      QtCore.Qt.ItemIsDragEnabled + 
                      QtCore.Qt.ItemIsDropEnabled + 
                      QtCore.Qt.ItemIsSelectable + 
                      QtCore.Qt.ItemIsEnabled))
    new_item.details = details
    if details.Parent:
      parent = self.detail_items[widget][details.Parent]
      parent.addChild(new_item)
    else:
      widget.addTopLevelItem(new_item)

    if edit:    
      widget.setCurrentItem(new_item)
      widget.editItem(new_item)
    
    self.detail_items[widget][details.Id] = new_item

