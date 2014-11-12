'''
Created on Oct 6, 2013

@author: EHWAAL

Copyright (C) 2014 Evert van de Waal
This program is released under the conditions of the GNU General Public License.
'''

# TODO: Add change handlers for the style checkbox, combo boxes & line edits.

from PyQt4 import QtCore, QtGui
from sqlalchemy import Integer, Boolean, String, Text, DateTime, event
from datetime import datetime, timedelta
from statechange import StateChangeEditor, StateChangeView
from gui.design import (PlannedItemForm, XRefEditorForm, StyleEditForm, CsvImportForm)
import model
from styles import (Style, StyleTypes, getBool, getItemType,
                    getFont, createDefaultStyle)
from util import Const



CODEC = QtCore.QTextCodec.codecForName(model.ENCODING)

def toUnicode(qstr):
  ''' Convert a QT string to unicode
  :rtype : unicode
  '''
  return unicode(CODEC.fromUnicode(qstr), model.ENCODING)



class CsvImportEditor(CsvImportForm[1]):
  def __init__(self, parent):
    CsvImportForm[1].__init__(self, parent)
    self.ui = CsvImportForm[0]()
    self.ui.setupUi(self)

    # Default we work with SQLite files, hide the proper Database fields.
    for w in [self.ui.edtDb, self.ui.lblDb]:
      w.hide()

    # Link the file open buttons.
    self.ui.btnDbFile.clicked.connect(self.onOpenSqliteFile)
    self.ui.btnCsvFile.clicked.connect(self.onOpenCsvFile)

  def burp(self):
    if self.ui.rbtnSqlite.isChecked():
      return model.SQLITE_URL_PREFIX+str(self.ui.edtDbFile.text())
    return str(self.ui.edtDb.text())

  @property
  def csv_file(self):
    return str(self.ui.edtCsvFile.text())

  def onOpenSqliteFile(self):
    fname = str(QtGui.QFileDialog.getSaveFileName(self, "Open an architecture model",
                                                  '.', "*.db"))
    if fname:
      self.ui.edtDbFile.setText(fname)

  def onOpenCsvFile(self):
    fname = str(QtGui.QFileDialog.getOpenFileName(self, "Select CSV File to import",
                                                  '.', "*.csv"))
    if fname:
      self.ui.edtCsvFile.setText(fname)

class StyleEditor(StyleEditForm[1]):
  class Level(Const):
    Global = 1
    Stereotype = 2
    Role = 3
    
  def __init__(self):
    self.allow_role_updates = False
    self.stylable = None
    self.stylesheet = None
    self.editor = None
    self.session = None   # To be set by the owner

    StyleEditForm[1].__init__(self)
    self.ui = StyleEditForm[0]()
    self.ui.setupUi(self)

    self.ui.btnFactoryDefaults.clicked.connect(self.onResetToDefaults)
    self.ui.edtStyles.textChanged.connect(self.onTextChanged)
    self.ui.edtStyles.focusOutEvent = self.onEditFocusLost
    self.ui.actionSave.triggered.connect(self.onEditFocusLost)
    self.ui.cmbRole.currentIndexChanged.connect(self.onRoleChanged)
    self.ui.cmbDetails.currentIndexChanged.connect(self.onStyleItemChanged)
    for btn in [self.ui.btnGlobal, self.ui.btnStereotype, self.ui.btnRole]:
      btn.clicked.connect(self.onStyleItemChanged)
    
    self.stylesheet_changed = False
    Style.current_style.subscribe(self.onStylesheetChanged)
    Style.current_object.subscribe(self.onStylableChanged)
    self.allow_role_updates = True
  def onStylesheetChanged(self, styles):
    self.allow_role_updates = False
    self.stylesheet = styles
    self.stylesheet.subscribe(self.onStyleItemChanged)
    try:
      self.ui.edtStyles.setPlainText(styles.details.Details)
      self.ui.cmbRole.clear()
    finally:
      self.allow_role_updates = True
  def onStylableChanged(self, stylable):
    self.stylable = None
    self.allow_role_updates = False
    try:
      self.ui.cmbRole.clear()
      self.ui.lblStereotype.setText('')
      if not stylable:
        return
      item = stylable[0]
      self.stylable = item
      # Search for a role, either in this item or its parents.
      stereotype = item.stereotype
      if not stereotype:
        return  # No ROLE defined, no more parents.
      self.ui.lblStereotype.setText(stereotype)
      roles = Style.current_style.get().findApplicableRoles(stereotype)
      roles.insert(0, '<default>')
      roles = sorted(roles)
      self.ui.cmbRole.addItems(roles)
      current_role = item.role
      if current_role and current_role in roles:
        self.ui.cmbRole.setCurrentIndex(roles.index(current_role))
      else:
        self.ui.cmbRole.setCurrentIndex(0)
        
      self.ui.cmbDetails.clear()
      self.ui.cmbDetails.addItems(self.stylesheet.requestedItems(stereotype))
        
      self.onStyleItemChanged(None)
    finally:
      self.allow_role_updates = True
      
  def onTextChanged(self):
    self.stylesheet_changed = True
    
  def onEditFocusLost(self, event):
    ''' Called when the user has stopped editing the stylesheet.
        Overloads edtStyles.focusOutEvent. 
    '''
    if self.stylesheet_changed:
      stylesheet = self.stylesheet
      if stylesheet:
        stylesheet.details.Details = str(self.ui.edtStyles.toPlainText())
        stylesheet.reloadDetails()
    self.stylesheet_changed = False
  def onRoleChanged(self, _):
    if not self.allow_role_updates:
      return
    objs = Style.current_object.get()
    if objs:
      txt = str(self.ui.cmbRole.currentText())
      for obj in objs:
        obj.setRole(txt)
    self.onStyleItemChanged(None)
        
  def getLevel(self):
    if self.ui.btnGlobal.isChecked():
      return self.Level.Global
    if self.ui.btnStereotype.isChecked():
      return self.Level.Stereotype
    if self.ui.btnRole.isChecked():
      return self.Level.Role
        
  def onStyleItemChanged(self, _):
    if not self.allow_role_updates:
      return
    if not self.stylable:
      return
    
    self.ui.edtStyles.setPlainText(self.stylesheet.details.Details)
    
    if self.editor:
      self.ui.editorLayout.removeWidget(self.editor)
      self.editor.close()
      self.editor = None
    
    while self.ui.editorLayout.count() > 0:
      it = self.ui.editorLayout.takeAt(0)
      it.widget.close()
    
    self.editor = self.widgetFactory()
    if self.editor:
      self.ui.editorLayout.addWidget(self.editor)
    
  def getCurrent(self):
    item = str(self.ui.cmbDetails.currentText())
    t = getItemType(item)
    full_role = self.stylable.full_role if self.stylable.role else self.stylable.stereotype
    role = {self.Level.Global:'',
            self.Level.Stereotype:self.stylable.stereotype,
            self.Level.Role:full_role}[self.getLevel()]
    current = self.stylesheet.findItem(role, item)
    return item, role, current, t

    
  def editColor(self):
    item, role, current, _ = self.getCurrent()
    color = QtGui.QColorDialog.getColor(QtGui.QColor(current), self)
    if not color.isValid():
      return
    r, g, b, _ = color.getRgb()
    self.stylesheet.setItem(role, item, '#%02x%02x%02x'%(r, g, b))
    
  def editFont(self):
    item, role, current, _ = self.getCurrent()
    font = getFont(current)
    new_font, ok = QtGui.QFontDialog.getFont(font, self)
    if not ok:
      return
    font_str = '%s %spt'%(new_font.family(), new_font.pointSize())
    if new_font.italic():
      font_str += ' italic'
    if new_font.bold():
      font_str += ' bold'
    if new_font.underline():
      font_str += ' underline'
    if new_font.strikeOut():
      font_str += ' strikeout'
    
    self.stylesheet.setItem(role, item, font_str)
    
    
  def acceptComboUpdate(self, _):
    item, role, _, _ = self.getCurrent()
    new_value = str(self.editor.currentText())
    self.stylesheet.setItem(role, item, new_value)
    
  
  def acceptLineEditUpdate(self):
    item, role, _, _ = self.getCurrent()
    new_value = str(self.editor.text())
    self.stylesheet.setItem(role, item, new_value)
    
  def acceptCheckboxUpdate(self, _):
    item, role, _, _ = self.getCurrent()
    new_value = 'yes' if self.editor.isChecked() else 'no'
    self.stylesheet.setItem(role, item, new_value)
    
  def widgetFactory(self):
    item, _, current, t = self.getCurrent()
    t = getItemType(item)
    if t == StyleTypes.COLOR:
      w = QtGui.QToolButton(self)
      w.setStyleSheet('background-color:%s'%current)
      w.clicked.connect(self.editColor)
      return w
    
    elif t == StyleTypes.BOOL:
      w = QtGui.QCheckBox(self)
      w.setChecked(getBool(current))
      w.stateChanged.connect(self.acceptCheckboxUpdate)
      return w
    
    elif t == StyleTypes.FONT:
      w = QtGui.QPushButton(current, self)
      w.clicked.connect(self.editFont)
      return w
    
    elif t in [StyleTypes.LINESTYLE, StyleTypes.HALIGN, StyleTypes.VALIGN]:
      w = QtGui.QComboBox(self)
      opts = {StyleTypes.LINESTYLE:Style.linestyles.keys(), 
              StyleTypes.HALIGN:Style.halignopts.keys(), 
              StyleTypes.VALIGN:Style.valignopts.keys()}[t]
      w.addItems(opts)
      if current:
        w.setCurrentIndex(opts.index(current))
      w.currentIndexChanged.connect(self.acceptComboUpdate)
      return w
    
    elif t in [StyleTypes.FLOAT, StyleTypes.ARROW, StyleTypes.XYCOOD]:
      default = {StyleTypes.FLOAT:'0.0', StyleTypes.ARROW:'[[0,0]]',
                 StyleTypes.XYCOOD:'[0.0, 0.0]'}[t]
      current = current if current else default
      w = QtGui.QLineEdit(current, self)
      w.returnPressed.connect(self.acceptLineEditUpdate)
      return w


  def onResetToDefaults(self, triggered=False):
    ''' Called when the user clicks on the button 'Reset to Factory Defaults'
    '''
    # Check if the user did not press the button by accident
    q = QtGui.QMessageBox.question(self, 'Reset Styles', 'You are about to reset your styles to '
                'the factory defaults. Are you sure?',
                buttons=QtGui.QMessageBox.Ok | QtGui.QMessageBox.Cancel,
                defaultButton=QtGui.QMessageBox.Cancel)
    if q != QtGui.QMessageBox.Ok:
      return
    createDefaultStyle(self.session)


class XRefEditor(XRefEditorForm[1]):
  def __init__(self, details, session, parent, open_view):
    XRefEditorForm[1].__init__(self, parent)
    
    self.details = details
    self.session = session
    self.open_view = open_view
    
    self.ui = XRefEditorForm[0]()
    self.ui.setupUi(self)
    
    self.ui.btnAdd.clicked.connect(self.onAddXref)
    self.ui.lstAItems.itemDoubleClicked.connect(self.onItemDoubleClick)

    for w, refs in [(self.ui.lstAItems, details.AItems),
                       (self.ui.lstBItems, details.BItems)]:
      if len(refs) == 0:
        w.hide()
      else:
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

  def __init__(self, parent, details, session, read_only):
    QtGui.QWidget.__init__(self, parent)
    self.vertical_layout = QtGui.QVBoxLayout(self)
    self.vertical_layout.setObjectName('vertical_layout')
    self.parent = parent
    self.details = details
    self.session = session
    
    names, columns = details.editableColumnDetails()
    self.names = names
    self.columns = columns
    edits = []
    formLayout = QtGui.QFormLayout()
    formLayout.setObjectName('formLayout')
    for i, n, t in zip(range(len(names)), names, columns):
      l = QtGui.QLabel(self)
      l.setText(n)
      formLayout.setWidget(i, QtGui.QFormLayout.LabelRole, l)
      e = self.__inputFactory(t, getattr(details, n), read_only)
      formLayout.setWidget(i, QtGui.QFormLayout.FieldRole, e)
      edits.append(e)
      
    self.vertical_layout.addLayout(formLayout)
    
    # If the details is a 'PlanneableItem', add some special items
    if isinstance(details, model.PlaneableItem):
      if not read_only:
        # Add a list of cross-references
        # Show only references where this Item is in the A role.
        self.xref_list = XRefEditor(details, session, self, self.open_view)
        self.vertical_layout.addWidget(self.xref_list)
      
      # Add a list of 'State Changes', and allow state changes to be added.
      for state in details.StateChanges:
        w = StateChangeView(self, state)
        self.vertical_layout.addWidget(w)
      if not read_only:
        b = QtGui.QPushButton('Add State Change', self)
        b.clicked.connect(lambda : StateChangeEditor.add(self, details, session))
        self.vertical_layout.addWidget(b)
      
      # Add database hooks to properly update when status updates are added.
      event.listen(model.PlaneableStatus, 'after_insert', self.onStateChangeInsert)
    
    self.edits = edits
    
  def __inputFactory(self, column, value, read_only):
    ''' returns a specific QWidget depending on the constant '''
    type_ = column.type
    if read_only:
      widget = QtGui.QLabel(self)
      if value:
        widget.setText(value)
      widget.setWordWrap(True)
      widget.getValue = lambda : value
    
    elif hasattr(type_, 'enums'):
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
      widget.getValue = lambda : toUnicode(widget.toPlainText())
      self.bindCallback(widget.textChanged, widget, column.name)
      if value:
        widget.setPlainText(value)
    elif isinstance(type_, String) or isinstance(type_, model.WorkingWeek):
      # A working week does its own converting: just feed it a string.
      widget = QtGui.QLineEdit(self)
      widget.getValue = lambda : toUnicode(widget.text())
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
    w = StateChangeView(self, target, self.session)
    self.vertical_layout.insertWidget(2, w)

  def setFocusOnName(self):
    ''' Set the focus on the editor for the 'Name' field. '''
    try:
      index = self.names.index('Name')
    except ValueError:
      # This editor has no field 'Name'...
      return
    editor = self.edits[index]
    editor.setFocus()
    editor.selectAll()


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
