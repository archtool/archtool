''' impera.gui.designer: Interface to GUI designs made with QT Designer.

This module automatically compiles QT Designs to python code, and imports them.
'''
import subprocess
import os
import os.path
import sys
from PyQt4.uic import loadUiType

d = os.path.dirname(__file__)


# Load all GUI elements designed with Qt Designer
MainWindowForm       = loadUiType('%s/main_window.ui'%d)
ProjectViewForm      = loadUiType('%s/project_view.ui'%d)
ArchitectureViewForm = loadUiType('%s/architecture_view.ui'%d)
StatusEditorForm     = loadUiType('%s/statuseditor.ui'%d)
StatusViewForm       = loadUiType('%s/statusview.ui'%d)
PlannedItemForm      = loadUiType('%s/planneditem_selector.ui'%d)
XRefEditorForm       = loadUiType('%s/xref_editor.ui'%d)
