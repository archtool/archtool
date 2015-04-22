'''
Created on Sep 26, 2013

@author: EHWAAL

Copyright (C) 2014 Evert van de Waal
This program is released under the conditions of the GNU General Public License.
'''

from PyQt4 import QtCore, QtGui
from design import ArchitectureViewForm, ProjectViewForm, TreeViewForm
import model
from util import mkMenu, showWidgetDialog
from view_2d import TwoDView, MIME_TYPE, getDetails, MyScene
from details_editor import EffortOverview, WorkerOverview, StyleEditor, EstimateDetails
from req_export import exportRequirementQuestions, exportRequirementsOverview
from viewer_base import ViewerWithTreeBase
import sqlalchemy
from sqlalchemy import event
import logging
from styles import Style
from controller import Controller


theController = Controller.get()
  
  
###############################################################################
##

class PlanningView(ViewerWithTreeBase):
  def __init__(self, parent):
    ViewerWithTreeBase.__init__(self, parent, ProjectViewForm[0])
    
    tree_models = {self.ui.treeProjects:model.Project}
    self.tree_models = tree_models
    for widget, model_class in tree_models.iteritems():
      widget.setModelClass(model_class, self)
      widget.itemClicked.connect(self.onTreeItemClicked)
      
    # Add a context menu to the workers viewer
    actions = [('Add', self.onAddWorker), ('Delete', self.onDeleteWorker)]
    mkMenu(actions, self, self.ui.lstWorkers)

    # Add a context menu to the projects viewer
    self.ui.treeProjects.item_actions.append(('Planning Details', self.onEstimateDetails))

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
    workers = self.session.query(model.Worker).all()
    for details in workers:
      item = QtGui.QListWidgetItem(details.Name, self.ui.lstWorkers)
      item.details = details
      
  def onItemChanged(self, item, column):
    # TODO: Implement
    pass
  
  def onViewPlanning(self, item, column):
    project = item.details
    workers = self.session.query(model.Worker).all()
    
    for actual, area in [(False, self.ui.areaPlanned), (True, self.ui.areaActual)]:
      widget = EffortOverview(self, project, workers, actual)
      area.setWidget(widget)
      widget.show()
      area.show()

  def onEstimateDetails(self):
    # Commit any outstanding changes
    self.session.commit()
    with model.sessionScope(self.session) as session:
      project = self.ui.treeProjects.currentItem().details
      widget = EstimateDetails(None, project)
      action = QtGui.QAction('Export as CSV', self)
      action.triggered.connect(widget.exportCsv)

      result = showWidgetDialog(self, widget, [action])
      if result != QtGui.QDialog.Accepted:
        # Rollback any changes made while editing
        session.rollback()

  
  def onViewWorker(self, item):
    return
    # TODO: Allow the default hours to be edited.
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
      session.add(worker)

    item = QtGui.QListWidgetItem(worker.Name, self.ui.lstWorkers)
    item.details = worker
    
  def onDeleteWorker(self, triggered=False):
    selection = self.ui.lstWorkers.selectedItems()
    if len(selection) == 0:
      return
    
    with model.sessionScope(self.session) as session:
      for item in selection:
        session.delete(item.details)
    for item in selection:
      index = self.ui.lstWorkers.row(item)
      _ = self.ui.lstWorkers.takeItem(index)

###############################################################################
##

class ArchitectureView(ViewerWithTreeBase):
  ''' Viewer showing requirements and Use Cases.
  '''
  DoubleClickItem = QtCore.pyqtSignal(object)

  def __init__(self, parent):
    ViewerWithTreeBase.__init__(self, parent, ArchitectureViewForm[0])

    self.current_stereotype = ''

    # Create the tree model viewers
    tree_models = {self.ui.wdgBlocks:model.ArchitectureBlock,
                   self.ui.wdgViews:model.View,
                     self.ui.wdgRequirements:model.Requirement,
                     self.ui.wdgBugs:model.Bug,
                     self.ui.wdgActions:model.FunctionPoint}
    self.tree_models = tree_models

    for widget, model_class in tree_models.iteritems():
      widget.ui = TreeViewForm[0]()
      widget.ui.setupUi(widget)
      widget.ui.tree.setModelClass(model_class, self)
      widget.ui.tree.itemClicked.connect(self.onTreeItemClicked)
      widget.ui.tree.setFinder(widget.ui.edtFind, widget.ui.btnFind)
      if widget is self.ui.wdgViews:
        widget.ui.tree.itemDoubleClicked.connect(self.onView)

    self.ui.tabGraphicViews.tabCloseRequested.connect(self.onTabCloseRequested)
    self.ui.tabGraphicViews.currentChanged.connect(self.onTabChanged)

    self.ui.cmbRole.activated.connect(self.onRoleChanged)
    
    self.ui.btnShowStyles.clicked.connect(self.onShowStyles)
    self.stateWindow = StyleEditor()
    self.stateWindow.hide()

    self.ui.chkFunctionFP.stateChanged.connect(lambda i: theController.setFpAsCall(bool(i)))
    
        
    # Add database hooks to properly update when items are added.
    for cls in [model.ArchitectureBlock, model.View, model.Requirement, model.Bug,
                model.FunctionPoint]:
      event.listen(cls, 'after_update', self.onDetailUpdate)
      event.listen(cls, 'after_insert', self.onDetailInsert)
      #FIXME: also handle deletes.
    self.hasEvents = True
      
      
  def close(self):
    ''' Overrides the QWidget.close. '''
    # Unsubscribe to database events.
    for cls in [model.ArchitectureBlock, model.View, model.Requirement, model.Bug,
                model.FunctionPoint]:
      try:
        event.remove(cls, 'after_update', self.onDetailUpdate)
        event.remove(cls, 'after_insert', self.onDetailInsert)
      except sqlalchemy.exc.InvalidRequestError:
        # No event handlers were found: ignore.
        pass
    self.hasEvents = False

    ViewerWithTreeBase.close(self)
    

  def clean(self):
    ''' Create a new database and connect to it.
      No check for outstanding changes necessary: all changes are
      stored immediatly.
    '''
    # Clean up all tree widgets
    for widget in self.tree_models:
      widget.ui.tree.clear()
      
    # Close all views in the tab window
    while self.ui.tabGraphicViews.count() > 0:
      self.onTabCloseRequested(0)
      
    self.closeDetailsViewer()



  def open(self, session):
    ViewerWithTreeBase.open(self, session)
    self.stateWindow.session = session

    # Create the drop-down list for stylesheets
    stylesheets = self.session.query(model.Style.Name).all()
    stylesheets = [s[0] for s in stylesheets]
    self.ui.cmbRole.clear()
        
  def onShowStyles(self):      
    self.stateWindow.show()

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
    widget = None
    for i in range(self.ui.tabGraphicViews.count()):
      view = self.ui.tabGraphicViews.widget(i)
      if view.details == details:
        # The view is already shown: bring it to the front.
        self.ui.tabGraphicViews.setCurrentIndex(i)
        widget = view

    if widget is None:
      # Add a new tab
      viewer = TwoDView(details, self.drop2Details, self.session)
      self.ui.tabGraphicViews.addTab(viewer, details.Name)
      self.ui.tabGraphicViews.setCurrentWidget(viewer)
      viewer.selectedItemChanged.connect(self.onItemSelectionChanged)
      viewer.scene.open_view.connect(self.openView)


  def onTabCloseRequested(self, index):
    widget = self.ui.tabGraphicViews.widget(index)
    self.ui.tabGraphicViews.removeTab(index)
    widget.close()

  def onTabChanged(self, index):
    self.updateRole()

  def onRoleChanged(self, _):
    # If the index is 0, the roles are not changed.
    if self.ui.cmbRole.currentIndex() == 0:
      return
    objs = Style.current_object.get()
    if objs:
      txt = str(self.ui.cmbRole.currentText())
      for obj in objs:
        obj.setRole(txt)

  def onItemSelectionChanged(self, details):
    ''' Overload of the function inherited from the viewer base.
    '''
    ViewerWithTreeBase.onItemSelectionChanged(self, details)
    self.updateRole()

  def updateRole(self):
    widget = self.ui.tabGraphicViews.currentWidget()
    if widget is None:
      return
    items = widget.scene.selectedItems()
    # Check if all items are of the same stereotype
    stereotypes = set()
    current_roles = set()
    for i in items:
      _, item = getDetails(i)
      stereotypes.add(item.ROLE)
      current_roles.add(item.role)
    if len(stereotypes) != 1:
      return

    stereotype = stereotypes.pop()
    if stereotype != self.current_stereotype:
      self.stereotype = stereotype
      # Fill the list of available roles
      self.ui.cmbRole.clear()
      roles = widget.scene.styles.findApplicableRoles(stereotype)
      # Add the default and empty role
      roles = ['--', '<default>'] + roles
      self.ui.cmbRole.addItems(roles)
      # If all items have the same role, select it
      if len(current_roles) == 1:
        role = current_roles.pop()
        index = 1 if not role else self.ui.cmbRole.findText(role)
        self.ui.cmbRole.setCurrentIndex(index)

    
  def filterRequirementsTree(self, prios, states):
    for item in self.ui.treeRequirements.detail_items.values():
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
    for widget, table in self.tree_models.items():
      if isinstance(details, table):
        return widget
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
      logging.error('onDetailUpdate called for wrong target %r'%target)
      return
    
    item = widget.detail_items.get(target.Id, None)
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
    parent = widget.detail_items[details.Parent] if details.Parent else None
    if parent:
      parent.addChild(new_item)
    else:
      widget.addTopLevelItem(new_item)

    if edit:    
      widget.setCurrentItem(new_item)
      widget.editItem(new_item)
    
    widget.detail_items[details.Id] = new_item

  def onStyleSheetChanged(self, index):
    ''' Called when the user selects a new style sheet for the current view.
    '''
    return
    # TODO: Re-implement
    # Get the ID of the style referred to
    name = str(self.ui.cmbStyleSheet.currentText())
    id = self.session.query(model.Style.Id).filter(model.Style.Name==name).one()[0]
    # Set the stylesheet in the current View
    view = self.ui.tabGraphicViews.currentWidget()
    if view:
      details = view.details
      details.style = id
