'''
Created on Feb 7, 2014

@author: EHWAAL
'''

from PyQt4 import QtGui, QtCore
from details_editor import DetailsViewer
import model

class ViewerBase(QtGui.QWidget):
  def __init__(self, parent, decorator):
    QtGui.QWidget.__init__(self, parent)
    self.ui = decorator()
    self.ui.setupUi(self)
    
    self.session = None

  def getSession(self):
    return self.session
  
  def clean(self):
    raise NotImplementedError()
  
  def open(self, session):
    self.session = session
    self.clean()
    
  def openView(self, details):
    ''' Called when an items needs to be viewed.
    '''
    pass
      


class ViewerWithDetailsBase(ViewerBase):
  def __init__(self, *args):
    ViewerBase.__init__(self, *args)
    self.details_viewer = None

  def openDetailsViewer(self, details, read_only=False):
    ''' Called when a different block is selected. '''
    # Ensure there is no other viewer
    self.closeDetailsViewer()
    # Check there is something to view
    if details is None:
      return
    # Create a new viewer.
    widget = DetailsViewer(self.ui.areaDetails, details, self.session, read_only)
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



###############################################################################
##
class ViewerWithTreeBase(ViewerWithDetailsBase):
  def __init__(self, *args):
    ViewerWithDetailsBase.__init__(self, *args)
    self.tree_models = None
    
  def open(self, session):
    ViewerWithDetailsBase.open(self, session)
    # Populate the tree lists.    
    for widget, cls in self.tree_models.iteritems():
      widget.populateTree()

  def onTreeItemClicked(self, item):
    ''' Called when the user clicks on an item in a tree view.
        Causes a details viewer to be opened for the tiems.
    '''
    self.openDetailsViewer(item.details)
      
  def onTreeItemAdded(self, details):
    ''' Called when a new item was created in a tree.
        Cause the focus to shift to the details editor for this item.
    '''
    # First cause the details editor to be shown.
    self.onItemSelectionChanged(details)
    # Set the focus to the 'Name' field for the editor
    self.details_viewer.setFocusOnName()


  def onItemSelectionChanged(self, details):
    ''' Called when the current selection in a 2D view changes.
    '''
    self.openDetailsViewer(details)

