''' Unit tests from directly within QT
'''

__author__ = 'ehwaal'

import unittest
import os
import posixpath
import sys
import traceback
import threading
import time
import shutil

from PyQt4.QtTest import QTest
from PyQt4 import QtGui, QtCore
from PyQt4.QtCore import Qt
from threading import Thread
import run
import model
from model import config
from gui.view_2d import BlockItem, Connection
from gui.statechange import StateChangeEditor

sys.path.append('../src')


class QuickThread(QtCore.QThread):
  ''' Class that quickly creates a Qt Thread and runs it.
  '''
  def __init__(self, target, *args, **kwds):
    QtCore.QThread.__init__(self)
    self.target = target
    self.args = args
    self.kwds = kwds
    self.start()

  def run(self):
    ''' The new thread '''
    self.target(*self.args, **self.kwds)


class AddBlockEvent(QtCore.QEvent):
  ''' Custom event to add a new block.
  '''
  def __init__(self, editor):
    QtCore.QEvent.__init__(self, QtCore.QEvent.User+1)
    self.editor = editor
  def execute(self, _form):
    self.editor.onAddBlock(True)


class MemFuncCallEvent(QtCore.QEvent):
  def __init__(self, f, *args, **kwds):
    QtCore.QEvent.__init__(self, QtCore.QEvent.User+1)
    self.f = f
    self.args = args
    self.kwds = kwds
  def execute(self, _form):
    self.f(*self.args, **self.kwds)

class Test(unittest.TestCase):
  ''' Test the Archtool GUI from within QT.
  '''

  TEST_DB = os.path.normpath(os.path.join(os.path.dirname(__file__), 'test.db'))
  TEST_URL = 'sqlite:////%s'%posixpath.normpath(TEST_DB)
  CONFIG_DB = os.path.normpath(os.path.join(os.path.dirname(__file__), 'config.db'))
  CONFIG_URL = 'sqlite:////%s'%posixpath.normpath(CONFIG_DB)

  APP = None

  @classmethod
  def setUpClass(cls):
    ''' Create the QT Application wherein the windows are shown.
    '''
    Test.APP = QtGui.QApplication(sys.argv)

  def setUp(self):
    ''' Prepare the tests.
    '''
    # Delete any existing test database
    if os.path.exists(self.TEST_DB):
      os.remove(self.TEST_DB)

    # Delete any existing test configuration
    if os.path.exists(self.CONFIG_DB):
      os.remove(self.CONFIG_DB)

    # Patch the configuration so that the test config will be used.
    config.ConfigManager.the_config = None
    config.CONFIG_URL = self.CONFIG_URL

    # Start the actual Architecture Tool
    self.form = run.ArchitectureTool()
    self.form.onNew(self.TEST_DB)
    self.form.show()
    QTest.qWaitForWindowShown(self.form)

  def tearDown(self):
    ''' Clean up after the test
    '''
    # Close the form
    self.form.close()
    QTest.qWait(100)
    self.form = None


  def sendEnter(self, w):
    self.APP.postEvent(w, QtGui.QKeyEvent(QtCore.QEvent.KeyPress,
                                          Qt.Key_Return,
                                          Qt.KeyboardModifiers()))
    self.APP.postEvent(w, QtGui.QKeyEvent(QtCore.QEvent.KeyRelease,
                                          Qt.Key_Return,
                                          Qt.KeyboardModifiers()))

  def answer(self, s):
    def run():
      while True:
        w = self.APP.activeModalWidget()
        if w and w != self.form:
          break
        time.sleep(0.1)

      w = w.focusWidget()
      if True:
        for ch in s:
          m = Qt.NoModifier
          if ch >= 'a' and ch <= 'z':
            o = ord(ch) - 32
          else:
            if ch >= 'A' and ch <='Z':
              m = Qt.ShiftModifier
            o = ord(ch)
          self.APP.postEvent(w, QtGui.QKeyEvent(QtCore.QEvent.KeyPress, o,
                                                Qt.KeyboardModifiers(m), ch))
          self.APP.postEvent(w, QtGui.QKeyEvent(QtCore.QEvent.KeyRelease, o,
                                                Qt.KeyboardModifiers(m), ch))
      else:
        QTest.keyClicks(w, s)
      self.sendEnter(w)

    th = threading.Thread(target=run)
    th.start()

  def postGuiFunc(self, f, *args, **kwds):
    ''' Insert an event so that a GUI function is called within the QT thread.
    '''
    self.APP.postEvent(self.form, MemFuncCallEvent(f, *args, **kwds))

  def test_Requirements(self):
    ''' Test adding and editing some requirements.
    '''
    cw = self.form.centralwidget
    self.assertIsInstance(cw, run.ArchitectureView)
    # Get the window that is shown inside the current TAB window
    cw.ui.tabWidget.setCurrentWidget(cw.ui.treeRequirements)

    QTest.qWait(100)

    # Add a new requirement
    cw.ui.treeRequirements.addHandler()
    QTest.qWait(100)
    self.assertEqual(cw.ui.treeRequirements.topLevelItemCount(), 1)

    # Check a database record has been created.
    r = self.form.session.query(model.Requirement).all()
    self.assertEqual(len(r), 1)
    # Check the values in the details editor
    self.assertEqual(cw.details_viewer.edits[0].currentText(), 'Functional')
    self.assertEqual(cw.details_viewer.edits[1].text(), 'new item')
    self.assertEqual(cw.details_viewer.edits[2].toPlainText(), '')
    self.assertEqual(cw.details_viewer.edits[3].currentText(), 'Must')

    # Change the name and check the name in the database can be edited.
    name = 'Requirement 1'
    cw.details_viewer.edits[1].setText(name)
    cw.details_viewer.edits[1].textEdited.emit(name)
    QTest.qWait(100)
    self.assertEqual(r[0].Name, name)

    # Commit the change and check the list is updated
    # Normally, the database is committed when the user selects something.
    self.form.session.commit()
    it = cw.ui.treeRequirements.topLevelItem(0)
    self.assertEqual(it.text(0), name)

    # Create a new requirement, as child from the first one.
    # Select the first requirement.
    it.setSelected(True)
    # Create the new item
    cw.ui.treeRequirements.addHandler()
    QTest.qWait(100)
    # Check the database and GUI structures
    self.assertEqual(cw.ui.treeRequirements.topLevelItemCount(), 1)
    r = self.form.session.query(model.Requirement).all()
    self.assertEqual(len(r), 2)
    self.assertEqual(r[1].Parent, r[0].Id)
    self.assertEqual(it.childCount(), 1)
    self.assertEqual(it.child(0).childCount(), 0)
    # Ensure the new item is editable
    name2 = 'Requirement 2'
    cw.details_viewer.edits[1].setText(name2)
    cw.details_viewer.edits[1].textEdited.emit(name2)
    QTest.qWait(100)
    self.assertEqual(r[1].Name, name2)
    self.assertEqual(r[0].Name, name)

    # Add a status change.
    self.postGuiFunc(StateChangeEditor.add, cw.details_viewer, r[1], self.form.session)
    while True:
      QTest.qWait(100)

    # TODO: Try to drag the child item away from the first requirement.

    # TODO: Add a cross-reference to a Use Case.


  def testUseCaseDrawing(self):
    ''' Test creating and editing a 2D drawing.
    '''
    # Create a Use Case
    cw = self.form.centralwidget
    cw.ui.treeUseCases.addHandler()
    it = cw.ui.treeUseCases.topLevelItem(0)
    # Open the 2D editor.
    cw.ui.treeUseCases.itemDoubleClicked.emit(it, 0)
    editor = cw.ui.tabGraphicViews.currentWidget()

    # Add two new Architecture Blocks
    editor.last_rmouse_click = QtCore.QPoint(100, 100)
    self.APP.postEvent(self.form, AddBlockEvent(editor))
    self.answer('Block 1')
    QTest.qWait(200)
    editor.last_rmouse_click = QtCore.QPoint(300, 100)
    self.APP.postEvent(self.form, AddBlockEvent(editor))
    self.answer('Block 2')
    QTest.qWait(200)
    self.assertEqual(cw.ui.treeBlocks.topLevelItemCount(), 2)
    # Make a private session for use within the testing thread.
    session = model.SessionFactory()
    self.assertEqual(session.query(model.ArchitectureBlock).count(), 2)

    # Connect the two blocks
    scene = editor.scene
    for b in scene.anchors.values():
      b.setSelected(True)
    # TODO: Test if the option to connect blocks is shown in the context menu.
    self.postGuiFunc(editor.onConnect)
    QTest.qWait(100)
    self.assertEqual(session.query(model.BlockConnection).count(), 1)
    self.assertEqual(session.query(model.ConnectionRepresentation).count(), 1)

    # Add an Action to the connection and to a block.
    self.postGuiFunc(scene.clearSelection)
    editor.last_rmouse_click = QtCore.QPoint(168, 235)
    self.postGuiFunc(editor.onNewAction)
    self.answer('Actie 1')
    QTest.qWait(100)
    self.assertEqual(session.query(model.FunctionPoint).count(), 1)

    # Add an Action to the connection
    editor.last_rmouse_click = QtCore.QPoint(245, 190)
    self.postGuiFunc(editor.onNewAction)
    self.answer('Actie 2')
    QTest.qWait(100)
    self.assertEqual(session.query(model.FunctionPoint).count(), 2)


    # Add an Annotation
    self.postGuiFunc(scene.clearSelection)
    editor.last_rmouse_click = QtCore.QPoint(100, 300)
    self.postGuiFunc(editor.onAddAnnotation)
    QTest.qWait(100)
    self.assertEqual(session.query(model.Annotation).count(), 1)


    # Create a second 'Block 2' and connect it
    # Hack the scene so that the last block is dropped
    block = session.query(model.ArchitectureBlock).all()[-1]
    scene.drop2Details = lambda x: block
    ev = QtGui.QDropEvent(QtCore.QPoint(300, 300), Qt.DropActions(), QtCore.QMimeData(),
                          Qt.MouseButtons(1), Qt.KeyboardModifiers())
    self.postGuiFunc(editor.dropEvent, ev)
    while True:
      QTest.qWait(100)
      break

    # Select the first and third block.
    scene.clearSelection()
    for b in [scene.anchors[i] for i in [1, 7]]:
      b.setSelected(True)
    self.postGuiFunc(editor.onConnect)
    QTest.qWait(100)
    # Check there is just one BlockConnection with two ConnectionRepresentation
    self.assertEqual(session.query(model.BlockConnection).count(), 1)
    self.assertEqual(session.query(model.ConnectionRepresentation).count(), 2)

    # Export to SVG
    if os.path.exists('test.db.new item.svg'):
      os.remove('test.db.new item.svg')
    self.postGuiFunc(editor.exportSvg)
    self.answer('')   # Close the pop-up
    QTest.qWait(100)
    self.assertTrue(os.path.exists('test.db.new item.svg'))

    # Pause to show the result
    while True:
      QTest.qWait(200)
      break
    pass # For breakpoint

    # Delete the actions
    scene.clearSelection()
    for a in scene.fpviews.values():
      a.setSelected(True)
    self.postGuiFunc(editor.onDelete)
    QTest.qWait(100)
    self.assertEqual(session.query(model.FpRepresentation).count(), 0)

    # Delete the Annotation
    self.postGuiFunc(scene.clearSelection)
    editor.last_rmouse_click = QtCore.QPoint(120, 253)
    self.postGuiFunc(editor.onDeleteItem)
    QTest.qWait(100)
    self.assertEqual(session.query(model.Annotation).count(), 0)

    # Delete the blocks
    scene.clearSelection()
    for a in scene.items():
      if isinstance(a, BlockItem):
        a.setSelected(True)
    self.postGuiFunc(editor.onDelete)
    QTest.qWait(100)
    self.assertEqual(session.query(model.BlockRepresentation).count(), 0)
    # All the connections must have been deleted as well.
    self.assertEqual(session.query(model.ConnectionRepresentation).count(), 0)
    self.assertEqual(len([i for i in scene.items() if isinstance(i, Connection)]), 0)

  def testExistingUseCase(self):
    ''' Test whether an existing Use case can be shown and exported to SVG properly.
        Also tests moving objects up and down (Z-order).
    '''
    # Copy the test_base database to a new location.
    BASE_DB = 'test_base.db'
    NEW_DB = 'test_new.db'
    if os.path.exists(NEW_DB):
      os.remove(NEW_DB)
    shutil.copy(BASE_DB, NEW_DB)

    # Open the database
    self.form.onNew(NEW_DB)

    # Open all the Use Cases.
    session = model.SessionFactory()
    for details in session.query(model.View).all():
      self.form.centralwidget.openView(details)

    QTest.qWait(100)

    # Ensure the 'Overview' view is on top.
    overview = session.query(model.View).filter(model.View.Name=='Overview').one()
    self.form.centralwidget.openView(overview)

    editor = self.form.centralwidget.ui.tabGraphicViews.currentWidget()
    scene = editor.scene

    # Move the 'Archtool' block to the back.
    editor.last_rmouse_click = QtCore.QPoint(255, 116)
    self.postGuiFunc(editor.onChangeItemOrder, editor.MOVE_TOP)
    QTest.qWait(100)
    rep = session.query(model.Anchor).filter(model.Anchor.Id==10).one()
    self.assertEqual(rep.Order, 7)

    editor.last_rmouse_click = QtCore.QPoint(255, 116)
    self.postGuiFunc(editor.onChangeItemOrder, editor.MOVE_DOWN)
    QTest.qWait(100)
    session.refresh(rep)
    self.assertEqual(rep.Order, 6)

    editor.last_rmouse_click = QtCore.QPoint(255, 116)
    self.postGuiFunc(editor.onChangeItemOrder, editor.MOVE_UP)
    QTest.qWait(100)
    session.refresh(rep)
    self.assertEqual(rep.Order, 7)

    editor.last_rmouse_click = QtCore.QPoint(255, 116)
    self.postGuiFunc(editor.onChangeItemOrder, editor.MOVE_BOTTOM)
    QTest.qWait(100)
    session.refresh(rep)
    self.assertEqual(rep.Order, 0)

    # Pause to show the result
    if False:
      while True:
        QTest.qWait(100)


if __name__ == "__main__":
  try:
    r = unittest.main()
    sys.exit(r)
  except:
    traceback.print_exc()
    sys.exit(1)