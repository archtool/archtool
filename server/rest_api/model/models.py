"""
Created on Sep 25, 2013

@author: EHWAAL

Copyright (C) 2014 Evert van de Waal
This program is released under the conditions of the GNU General Public License.
"""

from .history import Versioned

VERSION = 16


# Determine which encoding to use when interacting with files
# The database stores unicode, and unicode is used inside the program by Python
ENCODING = 'cp1252' if 'win' in sys.platform else 'utf-8'

NAME_LENGTH = 100

class Model(django.db.models.Model)