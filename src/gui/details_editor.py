'''
Created on Oct 6, 2013

@author: EHWAAL

Copyright (C) 2014 Evert van de Waal
This program is released under the conditions of the GNU General Public License.
'''
from PyQt4 import QtCore, QtGui
from sqlalchemy import Integer, Boolean, String, Text, DateTime, event
from datetime import datetime, timedelta
from statechange import StateChangeEditor, StateChangeView
from gui.design import PlannedItemForm, XRefEditorForm
import model


class XRefEditor(XRefEditorForm[1]):
  def __init__(self, details, session, parent, open_view):
    QtGui.QWidget.__init__(self, parent)
    
    self.details = details
    self.session = session
    self.open_view = open_view
    
    self.ui = XRefEditorForm[0]()
    self.ui.setupUi(self)
    
    self.ui.btnAdd.clicked.connect(self.onAddXref)
    self.ui.lstAItems.itemDoubleClicked.connect(self.onItemDoubleClick)

    for w, refs in [(self.ui.lstAItems, details.AItems),
                       (self.ui.lstBItems, details.BItems)]:
      for ref in refs:
        name = '.'.join([r.Name for r in ref.getParents()])
        name = ':'.join([ref.short_type, name])
        item = QtGui.QListWidgetItem(name, w)
        item.details = ref
      
    if isinstance(details, model.View):
      self.ui.btnCreate.hide()
    else:
      self.ui.btnCreate.clicked.connect(self.onCreate)

  def onAddXref(self):
    ''' Link an existing PlaneableItem to this one.
    
    Opens a tree window showing all PlanneableItems, sorted by
    type and parent-child relationships.
    '''
    def onAdd(details):
      for d in details:
        self.details.AItems.append(d)
        item = QtGui.QListWidgetItem(d.Name, self.ui.lstAItems)
        item.details = d
      self.session.commit()

    diag = PlannedItemSelector(self.session, self)
    diag.add_items.connect(onAdd)
    diag.exec_()
    

  def onCreate(self):
    ''' Create a new View and cross-reference it to this requirement.
    '''
    text, ok = QtGui.QInputDialog.getText(self, 'Nieuwe Use Case',
                                "Welke naam krijgt de Use Case?")
    if not ok:
      return

    # Create the Use Case
    uc = model.View(Name=str(text))
    self.details.AItems.append(uc)
    item = QtGui.QListWidgetItem(uc.Name, self.ui.lstAItems)
    item.details = uc
    self.session.commit()

  def onItemDoubleClick(self, item):
    ''' Called when the user double-clicks on an item.
        The action that is performed depends on the item: 
          Views: opening a view in the main window (through signals)
    '''
    details = item.details
    if isinstance(details, model.View):
      self.open_view.emit(details)



class PlannedItemSelector(PlannedItemForm[1]):
  add_items = QtCore.pyqtSignal(list)
  
  def __init__(self, session, parent):
    QtGui.QDialog.__init__(self, parent)
    self.ui = PlannedItemForm[0]()
    self.ui.setupUi(self)
    
    # Connect to signals
    self.ui.treeItems.itemSelectionChanged.connect(self.onSelectionChanged)
    self.ui.btnAdd.clicked.connect(self.onAdd)
    
    # Populate the tree
    tree = model.PlaneableItem.getTree(session)
    for type_name, details in tree.iteritems():
      top_item = QtGui.QTreeWidgetItem()
      top_item.setText(0, type_name)
      self.ui.treeItems.addTopLevelItem(top_item)
      self.addGeneration(top_item, details)

  def addGeneration(self, parent, details):
    ''' 
        details is a list of new details to be added to the parent.
    '''
    for d in details:
      new_item = QtGui.QTreeWidgetItem()
      new_item.setText(0, d.Name)
      new_item.setFlags(QtCore.Qt.ItemFlags(QtCore.Qt.ItemIsSelectable + 
                        QtCore.Qt.ItemIsEnabled))
      new_item.details = d
      parent.addChild(new_item)
      self.addGeneration(new_item, d.Children)

  def onSelectionChanged(self):
    selection = self.ui.treeItems.selectedItems()
    if len(selection) == 1:
      txt = selection[0].details.Description
      if not txt:
        txt = ''
      self.ui.txtDescription.setPlainText(txt)
      
  def onAdd(self):
    ''' Called when adding a PlaneableItems.
    '''
    selection = self.ui.treeItems.selectedItems()
    if len(selection) == 0:
      return
    self.add_items.emit([s.details for s in selection])
  


class DetailsViewer(QtGui.QWidget):
  open_view = QtCore.pyqtSignal(model.View)

  def __init__(self, parent, details, session):
    QtGui.QWidget.__init__(self, parent)
    self.vertical_layout = QtGui.QVBoxLayout(self)
    self.vertical_layout.setObjectName('vertical_layout')
    self.parent = parent
    self.details = details
    self.session = session
    cols = details.getColumns().values()
    names = []
    columns = []
    for c in cols:
      if c.primary_key:
        continue
      if len(c.foreign_keys) > 0:
        continue
      if c.name == 'ItemType':
        continue
      names.append(c.name)
      columns.append(c)
    
    self.names = names
    self.columns = columns
    edits = []
    formLayout = QtGui.QFormLayout()
    formLayout.setObjectName('formLayout')
    for i, n, t in zip(range(len(names)), names, columns):
      l = QtGui.QLabel(self)
      l.setText(n)
      formLayout.setWidget(i, QtGui.QFormLayout.LabelRole, l)
      e = self.__inputFactory(t, getattr(details, n))
      formLayout.setWidget(i, QtGui.QFormLayout.FieldRole, e)
      edits.append(e)
      
    self.vertical_layout.addLayout(formLayout)
    
    # If the details is a 'PlanneableItem', add some special items
    if isinstance(details, model.PlaneableItem):
      # Add a list of cross-references
      # Show only references where this Item is in the A role.
      self.xref_list = XRefEditor(details, session, self, self.open_view)
      self.vertical_layout.addWidget(self.xref_list)
      
      # Add a list of 'State Changes', and allow state changes to be added.
      for state in details.StateChanges:
        w = StateChangeView(self, state)
        self.vertical_layout.addWidget(w)
      b = QtGui.QPushButton('Add State Change', self)
      b.clicked.connect(lambda : StateChangeEditor.add(self, details, session))
      self.vertical_layout.addWidget(b)
      
    # Add database hooks to properly update when status updates are added.
    event.listen(model.PlaneableStatus, 'after_insert', self.onStateChangeInsert)
    
  def __inputFactory(self, column, value):
    ''' returns a specific QWidget depending on the constant '''
    type_ = column.type
    if hasattr(type_, 'enums'):
      widget = QtGui.QComboBox(self)
      widget.addItems(type_.enums)
      widget.getValue = lambda : str(widget.currentText())
      self.bindCallback(widget.activated, widget, column.name)
      if value:
        widget.setCurrentIndex(type_.enums.index(value))
    elif isinstance(type_, Boolean):
      widget = QtGui.QCheckBox(self)
      widget.getValue = lambda : widget.isChecked()
      self.bindCallback(widget.stateChanged, widget, column.name)
      if value:
        widget.setChecked(value)
    elif isinstance(type_, Integer):      
      widget = QtGui.QSpinBox(self)
      widget.getValue = lambda : widget.value()
      self.bindCallback(widget.valueChanged, widget, column.name)
      if value:
        widget.setValue(value)
    elif isinstance(type_, Text):
      widget = QtGui.QPlainTextEdit(self)
      widget.setFixedHeight(200)
      widget.getValue = lambda : str(widget.toPlainText()).decode('cp1252')
      self.bindCallback(widget.textChanged, widget, column.name)
      if value:
        widget.setPlainText(value)
    elif isinstance(type_, String) or isinstance(type_, model.WorkingWeek):
      # A working week does its own converting: just feed it a string.
      widget = QtGui.QLineEdit(self)
      widget.getValue = lambda : str(widget.text()).decode('cp1252')
      self.bindCallback(widget.textEdited, widget, column.name)
      if value:
        widget.setText(value)
    elif isinstance(type_, DateTime):
      fmt = '%d %b %Y'
      widget = QtGui.QLineEdit(self)
      widget.getValue = lambda : datetime.strptime(str(widget.text()), fmt)
      self.bindCallback(widget.textEdited, widget, column.name)
      if value:
        widget.setText(value.strftime(fmt))
    else:
      raise RuntimeError('Unsupported type %s'%type_.__class__)
    return widget
  
  def bindCallback(self, signal, widget, name):
    def onChange():
      setattr(self.details, name, widget.getValue())
    signal.connect(onChange)
    
  def onStateChangeInsert(self, mapper, connection, target):
    ''' Called when a new Status update is inserted in the database.
    '''
    # Check if the status update is for this detail (it probably is ;-)
    if target.Planeable != self.details.Id:
      return

    # Add the new status update.
    w = StateChangeView(self, target)
    self.vertical_layout.insertWidget(2, w)




class EffortOverview(QtGui.QTableWidget):
  ''' Show a table showing the amount of effort for each worker on a project.
      The horizontal axis is weeks, the vertical is the worker.
  '''
  def __init__(self, parent, project, workers):
    self.project = project
    self.workers = workers
    
    end = int(project.LastWeek)
    start = int(project.FirstWeek)
    years = end/100 - start/100
    weeks = (end%100) - (start%100) + 52 * years + 1

    QtGui.QTableWidget.__init__(self, len(workers), weeks, parent)
    start = model.WorkingWeek.fromString(project.FirstWeek)
    deltas = [timedelta(7*d) for d in range(weeks)]
    labels = [(start + d).strftime(model.week_format) for d in deltas]
    self.setHorizontalHeaderLabels(labels)
    self.setVerticalHeaderLabels([w.Name for w in workers])
    
    worker_ids = [w.Id for w in workers]
    for effort in project.Effort:
      # Skip the planned efforts (those that have week=None
      if effort.Week is None:
        continue
      column = labels.index(effort.Week)
      row = worker_ids.index(effort.Worker)
      item = QtGui.QTableWidgetItem(str(effort.Hours))
      item.details = effort
      self.setItem(row, column, item)
      
    self.itemChanged.connect(self.onItemChange)
  
  def onItemChange(self, item):
    hrs = float(str(item.text()))
    column, row = item.column(), item.row()
    if hasattr(item, 'details'):
      item.details.Hours = hrs
    else:
      effort = model.PlannedEffort(Worker=self.workers[row].Id, Project=self.project.Id,
                                   Week=self.project.FirstWeek+timedelta(7*column),
                                   Hours=hrs)
      self.project.Effort.append(effort)
    
    
    
class WorkerOverview(QtGui.QTableWidget):
  ''' A simple table with one column: the amount of time to be spent on each project.
      The projects are the rows.
  '''
  def __init__(self, parent, worker, projects):
    self.worker = worker
    self.projects = projects
    
    QtGui.QTableWidget.__init__(self, len(projects), 1, parent)
    
    # Fill the headers
    self.setHorizontalHeaderLabels([worker.Name])
    self.setVerticalHeaderLabels([p.Name for p in projects])
    
    # Find out if there is already an effort to be spent.
    for row, p in enumerate(projects):
      planned = None
      for e in p.Effort:
        if e.Worker == worker.Id and e.Week is None:
          planned = e.Hours
          break
      if not planned is None:
        item = QtGui.QTableWidgetItem(str(e.Hours))
        item.details = e
        self.setItem(row, 0, item)
        
    self.itemChanged.connect(self.onItemChange)
  def onItemChange(self, item):
    hrs = float(str(item.text()))
    column, row = item.column(), item.row()
    if hasattr(item, 'details'):
      item.details.Hours = hrs
    else:
      effort = model.PlannedEffort(Worker=self.worker.Id, Project=self.projects[row].Id,
                                   Week=None, Hours=hrs)
      self.projects[row].Effort.append(effort)
