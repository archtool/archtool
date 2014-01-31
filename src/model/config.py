'''
Created on Nov 17, 2013

@author: EHWAAL

Copyright (C) 2014 Evert van de Waal
This program is released under the conditions of the GNU General Public License.
'''

from contextlib import contextmanager
from sqlalchemy.ext.declarative import declarative_base, declared_attr
from sqlalchemy import ForeignKey, create_engine
from sqlalchemy.orm import relationship, backref, sessionmaker
from sqlalchemy import Column, Integer, String, Float, Text, Boolean, DateTime, Enum
from model import MyBase
from os.path import expanduser
import json
from datetime import datetime

Base = declarative_base(cls=MyBase)

DEFAULTS = dict(nr_files_history=10, font_name='Arial',
                font_size=12)
CONFIG_TABLE = None  # Becomes as dictionary of key : Config item
CONFIG_URL = 'sqlite:///%s'%(expanduser('~/.archtool.conf').replace('\\', '/'))


class Config(Base):
  ''' Stores key : value pairs. 
  The values are encoded as JSON strings.
  '''
  Key = Column(String)
  Value = Column(Text)
  
  def __init__(self, key, value):
    self.Key = key
    self.Value = json.dumps(value)
  def getValue(self):
    return json.loads(self.Value)


class FileHistory(Base):
  Url       = Column(Text)
  TimeStamp = Column(DateTime, default=datetime.now)


@contextmanager
def transactionScope():
  """Provide a transactional scope around a series of operations."""
  session = SessionFactory()
  try:
    yield session
    session.commit()
  except:
    session.rollback()
    raise


def getConfig(key):
  ''' Returns a configuration item. '''
  # Create the configuration if not present
  global CONFIG_TABLE
  with transactionScope() as session:
    if not CONFIG_TABLE:
      config = session.query(Config).all()
      CONFIG_TABLE = {i.Key : i.getValue() for i in config}
    # Check all entries are there
    for k, value in DEFAULTS.iteritems():
      if k not in CONFIG_TABLE:
        item = Config(key=k, value = value)
        session.add(item)
        CONFIG_TABLE[key] = item
  return CONFIG_TABLE[key]
      
def getRecentFiles():
  ''' Return a list of recent files.
  '''
  max_files = getConfig('nr_files_history')
  with transactionScope() as session:
    # Delete files that are too many
    recent_files = list(session.query(FileHistory.Url).order_by(FileHistory.TimeStamp.desc()))
    for f in recent_files[max_files:]:
      session.delete(f)

  with transactionScope() as session:
    # Return the remaining files
    files = session.query(FileHistory.Url).order_by(FileHistory.TimeStamp.desc())[:max_files]
    return [f[0] for f in files]


def addRecentFile(url):
  ''' Add a recent file to the list in the configuration database'''
  with transactionScope() as session:
    exists = session.query(FileHistory).filter(FileHistory.Url==url).all()
    if len(exists) > 0:
      # This file has been opened before. Update the timestamp.
      exists[0].TimeStamp = datetime.now()
    else:
      # This is a new file: add it to the list
      entry = FileHistory(Url=url)
      session.add(entry)


engine = create_engine(CONFIG_URL)
SessionFactory = sessionmaker(bind=engine)
Base.metadata.create_all(engine)
