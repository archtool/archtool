'''
Created on Oct 31, 2013

@author: EHWAAL
'''

from PyQt4 import QtGui, QtCore
from model import PlaneableStatus, REQUIREMENTS_STATES, ManDay
from gui.design import StatusEditorForm
from gui.design import StatusViewForm


class StateChangeView(StatusViewForm[1]):
  def __init__(self, parent, details):
    QtGui.QWidget.__init__(self, parent)
    self.ui = StatusViewForm[0]()
    self.ui.setupUi(self)
    self.details = details
    
    msg = '%s:%s'%(details.Status, details.TimeStamp.strftime('%Y-%m-%d %H:%M:%S'))
    self.ui.grpBox.setTitle(msg)
    d = details.Description if details.Description else ''
    self.ui.lblText.setText(d)
    t = details.TimeRemaining if details.TimeRemaining else '-'
    self.ui.lblTime.setText('Schatting: %s'%t)
    self.ui.btnEdit.clicked.connect(self.edit)
  def updateValues(self):
    self.ui.lblText.setText(self.details.Description)
    self.ui.lblTime.setText('Schatting: %s'%self.details.TimeRemaining)
    self.ui.grpBox.setTitle('%s:%s'%(self.details.Status, 
                           self.details.TimeStamp.strftime('%Y-%m-%d %H:%M:%S')))
  def edit(self):
    diag = StateChangeEditor(self, self.details)
    r = diag.exec_()
    if r == QtGui.QDialog.Accepted:
      diag.getDetails(self.details)
      self.updateValues()


class StateChangeEditor(StatusEditorForm[1]):
  def __init__(self, parent_widget, value=None):
    QtGui.QDialog.__init__(self, parent_widget)
    self.ui = StatusEditorForm[0]()
    self.ui.setupUi(self)
    self.ui.cmbStatus.addItems(REQUIREMENTS_STATES)
    if value:
      if value.Description:
        self.ui.edtDescription.setPlainText(value.Description)
      self.ui.cmbStatus.setCurrentIndex(REQUIREMENTS_STATES.index(value.Status))
      if value.TimeRemaining:
        self.ui.edtTimeRemaining.setText(str(value.TimeRemaining))
  def getDetails(self, details):
    details.Description=str(self.ui.edtDescription.toPlainText()).decode('cp1252')
    details.Status=str(self.ui.cmbStatus.currentText())
    details.TimeRemaining=ManDay.fromString(str(self.ui.edtTimeRemaining.text()))
    
  @staticmethod
  def add(parent_widget, parent_details, session):
    diag = StateChangeEditor(parent_widget)
    r = diag.exec_()
    if r == QtGui.QDialog.Accepted:
      new = PlaneableStatus()
      diag.getDetails(new)
      parent_details.StateChanges.append(new)
      session.commit()

