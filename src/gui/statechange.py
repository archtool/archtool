'''
Created on Oct 31, 2013

@author: EHWAAL

Copyright (C) 2014 Evert van de Waal
This program is released under the conditions of the GNU General Public License.
'''

from PyQt4 import QtGui, QtCore
from model import PlaneableStatus, REQUIREMENTS_STATES, ManDay, ENCODING, Worker
from gui.design import StatusEditorForm
from gui.design import StatusViewForm


class StateChangeView(StatusViewForm[1]):
  def __init__(self, parent, details, session=None):
    QtGui.QWidget.__init__(self, parent)
    self.ui = StatusViewForm[0]()
    self.ui.setupUi(self)
    self.details = details
    self.session = session if session else parent.session
    
    msg = '%s:%s'%(details.Status, details.TimeStamp.strftime('%Y-%m-%d %H:%M:%S'))
    self.ui.grpBox.setTitle(msg)
    d = details.Description if details.Description else ''
    self.ui.lblText.setText(d)
    t = details.TimeRemaining if details.TimeRemaining else '-'
    self.ui.lblTime.setText('Schatting: %s'%t)
    self.ui.btnEdit.clicked.connect(self.edit)
    if session is not None:
      self.ui.btnEdit.hide()
  def updateValues(self):
    self.ui.lblText.setText(self.details.Description)
    self.ui.lblTime.setText('Schatting: %s'%self.details.TimeRemaining)
    self.ui.grpBox.setTitle('%s:%s'%(self.details.Status, 
                           self.details.TimeStamp.strftime('%Y-%m-%d %H:%M:%S')))
  def edit(self):
    if self.session is None:
      return
    workers = self.session.query(Worker).all()
    diag = StateChangeEditor(self, workers, self.details)
    r = diag.exec_()
    if r == QtGui.QDialog.Accepted:
      diag.getDetails(self.details)
      self.updateValues()


class StateChangeEditor(StatusEditorForm[1]):
  def __init__(self, parent_widget, workers, value=None):
    QtGui.QDialog.__init__(self, parent_widget)
    self.ui = StatusEditorForm[0]()
    self.ui.setupUi(self)
    self.ui.cmbStatus.addItems(REQUIREMENTS_STATES.values())
    self.ui.cmbAssigned.addItems([w.Name for w in workers])
    self.workers = workers
    if value:
      if value.Description:
        self.ui.edtDescription.setPlainText(value.Description)
      self.ui.cmbStatus.setCurrentIndex(REQUIREMENTS_STATES.values().index(value.Status))
      if value.TimeRemaining:
        self.ui.edtTimeRemaining.setText(str(value.TimeRemaining))
      if value.AssignedTo:
        self.ui.cmbAssigned.setCurrentIndex(workers.index(value.theWorker))

  def getDetails(self, details):
    details.Description=str(self.ui.edtDescription.toPlainText()).decode(ENCODING)
    details.Status=str(self.ui.cmbStatus.currentText())
    details.TimeRemaining=ManDay.fromString(str(self.ui.edtTimeRemaining.text()))
    if self.ui.cmbAssigned.currentIndex() >= 0:
      details.AssignedTo=self.workers[self.ui.cmbAssigned.currentIndex()].Id
    else:
      details.AssignedTo = None
    
  @staticmethod
  def add(parent_widget, parent_details, session):
    workers = session.query(Worker).all()
    copy_from = parent_details.StateChanges[-1] if parent_details.StateChanges else None
    diag = StateChangeEditor(parent_widget, workers, copy_from)
    r = diag.exec_()
    if r == QtGui.QDialog.Accepted:
      new = PlaneableStatus()
      diag.getDetails(new)
      parent_details.StateChanges.append(new)

