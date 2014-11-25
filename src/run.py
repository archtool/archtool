#!/usr/bin/python
'''
Created on Sep 25, 2013

@author: EHWAAL

Copyright (C) 2014 Evert van de Waal
This program is released under the conditions of the GNU General Public License.
'''

import sys
import re
import os.path
import logging
import traceback

from functools import partial

from PyQt4 import QtCore, QtGui
from gui.design import MainWindowForm
from gui.viewers import ArchitectureView, PlanningView
from gui.workitem_view import WorkitemView
from gui.styles import Styles
from gui.details_editor import CsvImportEditor
from req_export import exportRequirementQuestions, exportRequirementsOverview
from export import export, importData, loadCsv
from export.req_document import exportRequirementsDocument
import model
from model import config, SQLITE_URL_PREFIX
from model.update import updateDatabase
from controller import Controller


# FIXME: Nieuwe rollen kunnen toevoegen in de style editor.

# TODO: Een view kunnen representeren als een Sequence Diagram ipv Collaboration Diagram.
# TODO: Een Use Case droppen in een andere Use Case, dit wordt dan een blokje.
# TODO: Dubbel-klik op een Use Case blokje opent deze use case.
# TODO: Navigeren van acties naar views waarin deze voorkomt
# TODO: De schatting van een (groep) Use Cases opvragen.
# TODO: Diffs kunnen laten zien, en een document met alleen de wijzigingen kunnen genereren, of de
#       wijzigingen gehighlight (vanaf een bepaalde datum / versie)
# TODO: Grote workitems moeten kunnen worden toebedeeld aan meerdere mensen, en hun time-remaining schattingen samengevoegd.
# TODO: Export SRS documents as Word format.
# TODO: Edit the configuration...
# TODO: Voor een Use Case het tekening type selecteren.
# TODO: Implement support for attachements
# TODO: Multi-user support (user logs in, username is added to the logs)
# TODO: Undo is session-based (do not undo things done in another session).





def reportError(msg):
  def decorate(func):
    def doIt(*args, **kwds):
      try:
        return func(*args, **kwds)
      except:
        traceback.print_exc()
        QtGui.QMessageBox.critical(None, 'An error occurred', msg)
    return doIt
  return decorate



class ArchitectureTool(MainWindowForm[1]):
  def __init__(self):     
    # Setup UI first.
    QtGui.QMainWindow.__init__(self, None)
    
    self.current_url = None
    self.centralwidget = None
    
    self.setStyleSheet('font: %spt "%s";'%(config.getConfig('font_size'), 
                                         config.getConfig('font_name')))
    #self.setStyleSheet('font: 12 "MS Shell Dlg 2";')
    #self.setStyleSheet('font: 12pt "MS Shell Dlg 2";')
    self.ui = MainWindowForm[0]()
    self.ui.setupUi(self)


    for action, func in [(self.ui.actionNew, self.onNew),
                         (self.ui.actionOpen, self.onOpen),
                         (self.ui.actionArchitecture, self.onArchitectureView),
                         (self.ui.actionPlanning, self.onPlanningView),
                         (self.ui.actionExport_as_CSV, self.exportCsv),
                         (self.ui.actionNew_from_CSV, self.newFromCsv),
                         (self.ui.actionWork_Items, self.onWorkItemView),
                         (self.ui.actionRequirements_Document, self.onRequirementsDocument),
                         (self.ui.actionOpen_Database, self.onOpenDatabase)
                         ]:
      action.triggered.connect(func)

    # Add the recent files to the menu
    self.setRecentFileMenu()

    # Open the most recent file
    recent = config.getRecentFiles()
    if len(recent) > 0:
      self.open(url=recent[0])

    # Monkey-patch the menu to show its tooltips. I don't believe QT developers are so arrogant
    # they purposely disable tooltips in menu's!
    def handleMenuHovered(action):
      QtGui.QToolTip.showText(
            QtGui.QCursor.pos(), action.toolTip(),
            self.ui.menuRecent_Files, self.ui.menuRecent_Files.actionGeometry(action))
    self.ui.menuRecent_Files.hovered.connect(handleMenuHovered)


  def setRecentFileMenu(self):
    self.ui.menuRecent_Files.clear()
    # Add the recent files to the menu
    recent = config.getRecentFiles()
    for f in recent:
      a = QtGui.QAction(os.path.basename(f), self)
      a.triggered.connect(partial(self.open, url=f))
      # Mask any passwords
      f_nopasswd = re.sub(':[^/]+?@', ':***@', f)
      # TODO: make this a tool tip, not a status tip.
      a.setToolTip(f_nopasswd)
      self.ui.menuRecent_Files.addAction(a)


  def onNew(self, fname=None):
    if not fname:
      fname = str(QtGui.QFileDialog.getSaveFileName(self, "Open an architecture model",
                                                  '.', "*.db"))
    if fname == '':
      return

    if self.centralwidget:
      self.centralwidget.clean()
    self.open(url=SQLITE_URL_PREFIX+fname, new=True)
    # Write the version number to the database
    self.session.add(model.DbaseVersion())
    self.session.commit()

  def newFromCsv(self):
    ''' Create a new database from a CSV file exported earlier.
    '''
    diag = CsvImportEditor(self)
    result = diag.exec_()
    if result != QtGui.QDialog.Accepted:
      return

    if self.centralwidget:
      self.centralwidget.close()

    url = diag.burp()
    csvname = diag.csv_file
    if not(csvname and url):
      return

    model.createDatabase(url)
    # Import and create the database
    data = loadCsv(csvname)
    importData(data, url)
    # Open the database
    self.open(url=url)

  def onOpenDatabase(self):
    ''' Open a remote database instead of a local file.
    '''
    url = QtGui.QInputDialog.getText(self, 'Open a database', 'Url:')
    if not url[1]:
      return

    url = str(url[0])
    self.open(url=url)

  def onOpen(self):
    ''' Open an existing database.
    No check for outstanding changes necessary: all changes are
    stored immediatly.
    '''
    fname = str(QtGui.QFileDialog.getOpenFileName(self, "Open an architecture model", 
                                                  '.', "*.db"))
    if fname == '':
      return
    
    self.open(url=SQLITE_URL_PREFIX+fname)


  @reportError('Could not open the database.\n\nSee output for more details')
  def open(self, triggered=False, url=None, new=False):
    ''' Actually open a specific database.
        Called after the user has selected a database.
    '''
    if not new and url.startswith(SQLITE_URL_PREFIX):
      # Check if the file already exists.
      fname = url.split(SQLITE_URL_PREFIX)[-1]
      if not os.path.exists(fname):
        QtGui.QMessageBox.critical(self, 'File does not exist', 'The file %s does not appear to exist anymore'%fname)
        return
    if self.centralwidget:
      self.centralwidget.close()

    model.open(url, create=True)
    self.session = model.SessionFactory()
    Controller.setSession(self.session)

    # Check the version, if it exists
    versions = self.session.query(model.DbaseVersion).all()
    if len(versions) > 0:
      if versions[0].Version < model.VERSION:
        # Try to convert the model.
        q = QtGui.QMessageBox.question(self, 'Old database model', 'This file uses an old ' +\
                 'version of the database. Conversion is necessary  in order to continue.',
                buttons=QtGui.QMessageBox.Ok | QtGui.QMessageBox.Cancel,
                defaultButton=QtGui.QMessageBox.Ok)
        self.session = None
        if q != QtGui.QMessageBox.Ok:
          self.centralwidget.clean()
          return
        # User wants to convert the model.
        updateDatabase(model.the_engine, url)
        self.open(url=url)
        return
    
    Styles.load(self.session)
    self.centralwidget = ArchitectureView(self)
    self.setCentralWidget(self.centralwidget)
    self.centralwidget.open(self.session)

    self.setWindowTitle("Architecture Tool: %s"%url.split('/')[-1])
    config.addRecentFile(url)
    self.current_url = url

    # Update the recent file menu
    self.setRecentFileMenu()
    
  def onArchitectureView(self, triggered=False, cls=ArchitectureView):
    ''' Open the Architecture View in the central window.
    
        The function is also used to open other views...
    '''
    if not isinstance(self.centralwidget, cls):
      self.centralwidget.clean()
      self.centralwidget.close()

      self.centralwidget = cls(self)
      self.setCentralWidget(self.centralwidget)
      self.centralwidget.open(self.session)
    
  def onPlanningView(self):
    ''' Open the Planning View in the central window.
    '''
    # Use the onArchitectureView to open the PlanningView widget
    self.onArchitectureView(cls=PlanningView)
    
  def onWorkItemView(self):
    ''' Open the Work Item view in the central window.
    '''
    self.onArchitectureView(cls=WorkitemView)
    
  def exportCsv(self):
    ''' Export the current model as a CSV file.
    '''
    # Check a database is opened.
    if model.the_engine is None:
      return
    name = self.current_url.split('/')[-1].split('.')[0]
    # First ask the user for the file to save to.
    fname = str(QtGui.QFileDialog.getSaveFileName(self, 'export as CSV', '%s.csv'%name , '*.csv'))
    if fname == '':
      return
    # Then export the database
    export(fname, model.the_engine)
  
  def onRequirementsDocument(self):
    ''' Called when the user wants to generate a requirements document. 
        Requirements documents are generated from one top element, and include
        all its child elements.
    '''
    # Find the possible top requirements for the document, and let the user choose one.
    tops = self.session.query(model.Requirement.Name).filter(model.Requirement.Parent==None).all()
    tops = [t[0] for t in tops]
    top_item, ok = QtGui.QInputDialog.getItem(self, "Requirements Document", 
              "Vanaf welk requirement wilt u het document genereren?", tops, editable=False)
    if ok and str(top_item) != '':
      top_item = str(top_item)
      exportRequirementsDocument(self.session, top_item)


  def customEvent(self, ev):
    ''' Custom event handler.
        Custom events are expected to follow the command pattern.
    '''
    try:
      ev.execute(self)
    except:
      logging.exception('Exception while handling custom event.')

def run():
  ''' Start the GUI.
  '''
  app = QtGui.QApplication(sys.argv)
  myapp = ArchitectureTool()
  #myapp.open('sqlite:///archmodel.db')
  myapp.show()
  sys.exit(app.exec_())


if __name__ == '__main__':
  run()
