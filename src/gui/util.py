'''
Created on Sep 26, 2013

@author: EHWAAL

Copyright (C) 2014 Evert van de Waal
This program is released under the conditions of the GNU General Public License.
'''

from PyQt4 import QtCore, QtGui
from functools import partial


def mkMenu(definition, parent, menu=None):
  ''' Utility to create a menu from a configuration structure.
      The definition is a list op tuples (Text, Action, kwargs).
      The text can be '---' to make a separator.
      kwargs are bound to the action as keyword arguments.
  '''
  is_menu = False
  if menu is None:
    menu = QtGui.QMenu(parent)
    is_menu = True
  for action, func in definition:
    if action == '---' and is_menu:
      menu.addSeparator()
    else:
      a = QtGui.QAction(action, parent)
      menu.addAction(a)
      if func:
        a.triggered.connect(func)
  return menu



# Base class for constant classes
class Const(object):
  '''Base class for const value classes.
     The const value classes are used to group a set of const values. This base class provides
     a constructor, overwrite protection and inversed lookup.'''

  class ConstError(TypeError):
    '''This error is raised when someone tries to rebind a const to a new value.'''
    pass

  def __init__(self):
    '''Const constructor'''
    pass

  def __setattr__(self, name, value):
    '''Override of object.__setattr__.
       This override prevents rebinding a const name to a new value.'''
    if name in self.__dict__:
      raise self.ConstError, 'Cannot rebind const(%s)' % name
    self.__dict__[name] = value

  @classmethod
  def iteritems(cls):
    '''Iterator over the (key, value) items in Const object.'''
    for item in cls.__dict__.iteritems():
      if not str(item[0]).startswith('__'):
        yield item
  @classmethod
  def itervalues(cls):
    '''Iterator over the value items in Const object.'''
    for _key, value in cls.iteritems():
      yield value

  @classmethod
  def name(cls, lookup):
    '''Return the string representation of the given constant value.'''
    for key, value in cls.__dict__.iteritems():
      if lookup is value and not str(key).startswith('__'):
        return key
    raise KeyError(lookup)



def showWidgetDialog(parent, widget, actions=None):
  """ Wrap a widget with a modal dialog.
  """
  diag = QtGui.QDialog(parent)
  widget.setParent(diag)
  layout = QtGui.QVBoxLayout(diag)
  layout.addWidget(widget)
  buttonBox = QtGui.QDialogButtonBox(diag)
  buttonBox.setStandardButtons(QtGui.QDialogButtonBox.Cancel|QtGui.QDialogButtonBox.Ok)
  layout.addWidget(buttonBox)

  buttonBox.accepted.connect(diag.accept)
  buttonBox.rejected.connect(diag.reject)

  if actions:
    diag.addActions(actions)
    diag.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)

  return diag.exec_()


