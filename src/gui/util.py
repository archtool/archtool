'''
Created on Sep 26, 2013

@author: EHWAAL
'''

from PyQt4 import QtCore, QtGui



def bindLambda(func, kwargs):
  ''' Bind a dictionary with additional arguments to a function.
  '''
  def callFunc(*inner_args, **kwds):
    kwds.update(kwargs)
    func(*inner_args, **kwds)
  return callFunc


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
  for action, func, kwargs in definition:
    if action == '---' and is_menu:
      menu.addSeparator()
    else:
      a = QtGui.QAction(action, parent)
      menu.addAction(a)
      if func:
        a.triggered.connect(bindLambda(func, kwargs))
  return menu
