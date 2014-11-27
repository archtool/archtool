'''
Created on Feb 7, 2014

@author: EHWAAL
'''

from functools import partial
from PyQt4 import QtCore, QtGui
from design import WorkitemViewForm
from details_editor import DetailsViewer
from viewer_base import ViewerWithDetailsBase
import model
from sqlalchemy import or_


# TODO: Default status must be Open: selecting Open must also show those without status.
# TODO: Add filter showing current projects
# TODO: Show 'Take this Item' when an item is selected. 

def wrapListViewer(widget, parent):
  pass




class WorkitemView(ViewerWithDetailsBase):
  def __init__(self, parent):
    ViewerWithDetailsBase.__init__(self, parent, WorkitemViewForm[0])
    
    self.tables = [self.ui.tblCurrent, self.ui.tblItems]
    self.table_contents = {w:[] for w in self.tables}
    self.session = None

    # fill the filter lists
    layouts = [self.ui.grpType.layout(),
               self.ui.grpPrio.layout(),
               self.ui.grpStatus.layout()]
    elements = [model.PlaneableItem.getItemTypeNames(),
                model.PRIORITIES.itervalues(),
                model.REQUIREMENTS_STATES.itervalues()]
    for layout, texts in zip(layouts, elements):
      for txt in texts:
        btn = QtGui.QRadioButton(txt, parent=self)
        layout.addWidget(btn)
        btn.clicked.connect(self.onFilterChange)
    # Also hook the existing 'all' buttons
    self.ui.btnAllPrios.clicked.connect(self.onFilterChange)
    self.ui.btnAllTypes.clicked.connect(self.onFilterChange)
    self.ui.btnAllStates.clicked.connect(self.onFilterChange)
    
    # Hook the items table, for when the user selects a row.
    for tbl in self.tables:
      tbl.cellDoubleClicked.connect(partial(self.onCellDoubleClicked, widget=tbl))
    
    # Hook the Assign button
    self.ui.btnAssign.clicked.connect(self.onAssign)

    # Hook the worker selection combo box
    self.ui.cmbWorker.currentIndexChanged.connect(self.onWorkerChange)
            

  def open(self, session):
    self.session = session
    ViewerWithDetailsBase.open(self, session)
    # fill the combo boxes
    users = session.query(model.Worker.Name).order_by(model.Worker.Name).all()
    self.ui.cmbWorker.addItems([str(u[0]) for u in users])
    # Show the items with the default filter
    self.onFilterChange(None)
    self.onWorkerChange()
    
  def clean(self):
    self.ui.tblItems.clearContents()
    self.table_contents = {w:[] for w in self.tables}
    for wdg in [self.ui.cmbWorker, self.ui.cmbProject]:
      wdg.clear()
  
  def onCellDoubleClicked(self, row, column, widget):
    if row < len(self.table_contents[widget]):
      item = self.table_contents[widget][row]
      DetailsViewer.createAsWindow(item[0], self.session)

  def onWorkerChange(self):
    worker = str(self.ui.cmbWorker.currentText())
    if not worker:
      return
    worker_id = self.session.query(model.Worker.Id).filter(model.Worker.Name==worker).one()[0]
    items = self.getItems(status=model.OPEN_STATES,
                          assigned_to=worker_id)
    self.table_contents[self.ui.tblCurrent] = items
    self.fillCurrentTable(items)
    
    
  def fillCurrentTable(self, items):
    ''' Fill the table with the items currently assigned to the worker.
    '''
    self.ui.tblCurrent.clearContents()
    self.ui.tblCurrent.setRowCount(len(items))
    for row, item in enumerate(items):
      for col, txt in enumerate(['%4i'%item[0].Id, item[0].Name, item[0].Priority, item[3]]):
        if not txt is None:
          self.ui.tblCurrent.setItem(row, col, QtGui.QTableWidgetItem(str(txt)))

    self.ui.tblCurrent.resizeColumnsToContents()


  def fillFiltererdTable(self, items):
    ''' Show a list of items.
        These items must have the following structure:
          tuple(PlaneableItem, Status, AssignedTo '''
    self.ui.tblItems.clearContents()

    # Set the dimensions of the table
    self.ui.tblItems.setRowCount(len(items))

    workers = dict(self.session.query(model.Worker.Id, model.Worker.Name).all())

    # Fill the table
    for row, item in enumerate(items):
      worker = workers[item[2]] if item[2] else ''
      for col, txt in enumerate(['%4i'%item[0].Id, item[0].Name, item[0].Priority, item[1], worker]):
        if not txt is None:
          self.ui.tblItems.setItem(row, col, QtGui.QTableWidgetItem(txt))

    self.ui.tblItems.resizeColumnsToContents()
    

  def onAssign(self, _checked):
    ''' Called when the user wants to assign an item to a user. '''
    worker = str(self.ui.cmbWorker.currentText())
    index  = self.ui.tblItems.currentRow()
    item   = self.table_contents[self.ui.tblItems][index]
    worker_id = self.session.query(model.Worker.Id).filter(model.Worker.Name==worker).one()[0]
    status = model.PlaneableStatus(Planeable=item[0].Id, AssignedTo=worker_id,
                                   Status=item[1], TimeRemaining=item[3], TimeSpent=item[4])
    with model.sessionScope(self.session):
      self.session.add(status)
    
    # Update the views
    self.onWorkerChange()
    self.onFilterChange(False)

  
  def onFilterChange(self, _checked):
    ''' Called when the filter selection has changed.
        There are three parts to the filter: the type of item being shown,
        the priority of the item, the status of the item'''
    layouts = [self.ui.grpType.layout(),
               self.ui.grpPrio.layout(),
               self.ui.grpStatus.layout()]
    selections = []
    for layout in layouts:
      for index in range(layout.count()):
        btn = layout.itemAt(index).widget()
        if not isinstance(btn, QtGui.QRadioButton):
          continue
        if btn.isChecked():
          txt = str(btn.text())
          if txt.lower() == 'all':
            txt = None
          selections.append(txt)
          break
    items = self.getItems(*selections)
    self.table_contents[self.ui.tblItems] = items
    self.fillFiltererdTable(items)
    
    
  def getItems(self, item_type=None, priority=None, status=None, assigned_to=None):
    ''' Query the database to get all work items meeting the filters in one go. '''
    stmt = model.PlaneableStatus.getLatestQuery(self.session).subquery()
    base = self.session.query(model.PlaneableItem, stmt.c.Status, stmt.c.AssignedTo,
                              stmt.c.TimeRemaining, stmt.c.TimeSpent).\
                             outerjoin(stmt)
    if not item_type is None:
      base = base.filter(model.PlaneableItem.ItemType==item_type)
    if not priority is None:
      base = base.filter(model.PlaneableItem.Priority==priority)
    if not status is None:
      if isinstance(status, list):
        condition = stmt.c.Status.in_(status)
      else:
        condition = stmt.c.Status == status
      if model.REQUIREMENTS_STATES.OPEN in status:
        condition = or_(condition, stmt.c.Status == None)
      base = base.filter(condition)
    if assigned_to:
      base = base.filter(stmt.c.AssignedTo == assigned_to)
      
    return base.all()
      