'''
Created on Sep 26, 2013

@author: EHWAAL

Copyright (C) 2014 Evert van de Waal
This program is released under the conditions of the GNU General Public License.
'''

from functools import partial
from PyQt4 import QtCore, QtGui
from design import ArchitectureViewForm, ProjectViewForm
import model
from util import mkMenu
from view_2d import TwoDView, MIME_TYPE
from details_editor import EffortOverview, WorkerOverview, StateEditor
from req_export import exportRequirementQuestions, exportRequirementsOverview
from viewer_base import ViewerWithTreeBase, makeModelItemTree
from sqlalchemy import event
import logging


# TODO: move the makeModelItemTree to a MyTree, and promote the relevant widgets.


  
  
###############################################################################
##

class PlanningView(ViewerWithTreeBase):
  def __init__(self, parent):
    ViewerWithTreeBase.__init__(self, parent, ProjectViewForm[0])
    
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
    ViewerWithTreeBase.open(self, session)
    
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

class ArchitectureView(ViewerWithTreeBase):
  ''' Viewer showing requirements and Use Cases.
  '''
  REGTBL_COLUMNS = ['Name', 'Priority', 'Status']
  DoubleClickItem = QtCore.pyqtSignal(object)

  def __init__(self, parent):
    ViewerWithTreeBase.__init__(self, parent, ArchitectureViewForm[0])
    
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
    self.ui.btnShowStyles.stateChanged.connect(self.onShowStyles)
    self.stateWindow = StateEditor()
    self.stateWindow.hide()
    
        
    # Add database hooks to properly update when items are added.
    for cls in [model.ArchitectureBlock, model.View, model.Requirement]:
      event.listen(cls, 'after_update', self.onDetailUpdate)
      event.listen(cls, 'after_insert', self.onDetailInsert)
      #FIXME: also handle deletes.
      
      
  def close(self):
    ''' Overrides the QWidget.close. '''
    # Unsubscribe to database events.
    for cls in [model.ArchitectureBlock, model.View, model.Requirement]:
      event.remove(cls, 'after_update', self.onDetailUpdate)
      event.remove(cls, 'after_insert', self.onDetailInsert)
      
    ViewerWithTreeBase.close(self)
    

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
    ViewerWithTreeBase.open(self, session)
    
    # Populate the requirements table
    if False:
      all = self.session.query(model.Requirement).all()
      for req in all:
        self.addTableElement(req)
        
  def onShowStyles(self, state):      
    if not state:
      self.stateWindow.hide()
    else:
      self.stateWindow.show()

  def onItemChanged(self, item, column):
    new_name = str(item.text(0))
    if new_name != item.details.Name:
      item.details.Name = new_name
      # Ensure the changes are committed.
      with model.sessionScope(self.session):
        pass

  def onItemSelectionChanged(self, details):
    ''' Called when the current selection in a 2D view changes.
    '''
    self.openDetailsViewer(details)

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
    viewer = TwoDView(details, self.drop2Details, self.session)
    self.ui.tabGraphicViews.addTab(viewer, details.Name)
    self.ui.tabGraphicViews.setCurrentWidget(viewer)
    viewer.selectedItemChanged.connect(self.onItemSelectionChanged)

    
  def onTabCloseRequested(self, index):
    widget = self.ui.tabGraphicViews.widget(index)
    self.ui.tabGraphicViews.removeTab(index)
    widget.close()
    
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

