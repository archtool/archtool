'''
Created on Sep 25, 2013

@author: EHWAAL

Copyright (C) 2014 Evert van de Waal
This program is released under the conditions of the GNU General Public License.
'''

from PyQt4 import QtCore, QtGui
from gui.design import MainWindowForm
from gui.viewers import ArchitectureView, PlanningView
from gui.workitem_view import WorkitemView
from gui.util import bindLambda
from req_export import exportRequirementQuestions, exportRequirementsOverview
from export import export
from sqlalchemy import event
from sqlalchemy.engine import Engine
import sys
import model
from model import config
import os.path


# FIXME: Bij het openen van een file of het maken van een nieuwe, de recent files aanpassen.

# TODO: Een verbinding tussen blokken kunnen verbergen, bv. passtimehandlr->displaycontentgen in BusDetectieOpEntryLus
# TODO: Navigeren van acties naar views waarin deze voorkomt
# TODO: De richting van een verbinding tussen blokken kunnen zien en omdraaien
# TODO: De schatting van een (groep) Use Cases opvragen.
# TODO: Een Use Case exporteren als SVG plaatje.


SQLITE_URL_PREFIX = 'sqlite:///'



@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


class ArchitectureTool(MainWindowForm[1]):
  def __init__(self):     
    # Setup UI first.
    QtGui.QMainWindow.__init__(self, None)
    
    self.current_url = None
    
    self.setStyleSheet('font: %spt "%s";'%(config.getConfig('font_size'), 
                                         config.getConfig('font_name')))
    #self.setStyleSheet('font: 12 "MS Shell Dlg 2";')
    #self.setStyleSheet('font: 12pt "MS Shell Dlg 2";')
    self.ui = MainWindowForm[0]()
    self.ui.setupUi(self)
    self.centralwidget = ArchitectureView(self)
    self.setCentralWidget(self.centralwidget)


    for action, func in [(self.ui.actionNew, self.onNew),
                         (self.ui.actionOpen, self.onOpen),
                         (self.ui.actionArchitecture, self.onArchitectureView),
                         (self.ui.actionPlanning, self.onPlanningView),
                         (self.ui.actionExport_as_CSV, self.exportCsv),
                         (self.ui.actionNew_from_CSV, self.newFromCsv),
                         (self.ui.actionWork_Items, self.onWorkItemView),
                         #(self.ui.actionRequirements_Document)
                         ]:
      action.triggered.connect(func)

    # Add the recent files to the menu
    recent = config.getRecentFiles()
    for f in recent:
      a = QtGui.QAction(os.path.basename(f), self)
      a.triggered.connect(bindLambda(self.open, {'url':f}))
      self.ui.menuRecent_Files.addAction(a)

    # Open the most recent file
    if len(recent) > 0:
      self.open(url=recent[0])
      
  def onNew(self):
    fname = str(QtGui.QFileDialog.getSaveFileName(self, "Open an architecture model", 
                                                  '.', "*.db"))
    if fname == '':
      return
    
    self.centralwidget.clean()
    self.open(url=SQLITE_URL_PREFIX+fname, new=True)
    # Write the version number to the database
    self.session.add(model.DbaseVersion())
    self.session.commit()

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
    model.changeEngine(model.create_engine(url))
    self.session = model.SessionFactory()
    self.centralwidget.open(self.session)

    self.setWindowTitle("Architecture Tool: %s"%url.split('/')[-1])
    config.addRecentFile(url)
    self.current_url = url
    
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
  
  def newFromCsv(self):
    ''' Create a new database from a CSV file exported earlier.
    '''
    csvname = str(QtGui.QFileDialog.getOpenFileName(self, "Open an architecture model", 
                                                  '.', "*.db"))
    if csvname == '':
      return
    fname = str(QtGui.QFileDialog.getSaveFileName(self, "Naar welke database wordt geschreven?", 
                                                  '.', "*.db"))
    if fname == '':
      return
    # Import and create the database
    importCsv(csvname, fname)
    # Open the database
    self.open(url=SQLITE_URL_PREFIX+fname)


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
