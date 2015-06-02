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

DEFAULTS = dict(nr_files_history=10, 
                font_name='Arial', font_size=12,
                export_dir=expanduser('~/architectures'))


CONFIG_URL = 'sqlite:///%s'%(expanduser('~/.archtool.conf').replace('\\', '/'))




###############################################################################
## The tables stored in the configuration database

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


###############################################################################
## Accessing the database

class ConfigManager(object):
  ''' Manages the config database.
  '''
  the_config = None # Config singleton

  def __init__(self):
    self.engine = create_engine(CONFIG_URL)
    self.SessionFactory = sessionmaker(bind=self.engine)
    Base.metadata.create_all(self.engine)

    self.config_table = {}

    # Create the configuration if not present
    # Fill the database with default values if necessary
    with self.transactionScope() as session:
      config = session.query(Config).all()
      self.config_table = {i.Key : i.getValue() for i in config}
      # Check all entries are there
      for k, value in DEFAULTS.iteritems():
        if k not in self.config_table:
          item = Config(key=k, value = value)
          session.add(item)
          self.config_table[k] = value


  @classmethod
  def getTheConfig(cls):
    ''' Access the singleton
    '''
    if not cls.the_config:
      cls.the_config = ConfigManager()
    return cls.the_config

  @contextmanager
  def transactionScope(self):
    """Provide a transactional scope around a series of operations."""
    session = self.SessionFactory()
    try:
      yield session
      session.commit()
    except:
      session.rollback()
      raise


  def getConfig(self, key):
    ''' Returns a configuration item. '''
    return self.config_table[key]

  def getRecentFiles(self):
    ''' Return a list of recent files.
    '''
    max_files = self.getConfig('nr_files_history')
    with self.transactionScope() as session:
      # Delete files that are too many
      recent_files = session.query(FileHistory).\
                          order_by(FileHistory.TimeStamp.desc())
      for f in recent_files[max_files:]:
        session.delete(f)

    with self.transactionScope() as session:
      # Return the remaining files
      files = session.query(FileHistory.Url).order_by(FileHistory.TimeStamp.desc())[:max_files]
      return [f[0] for f in files]


  def addRecentFile(self, url):
    ''' Add a recent file to the list in the configuration database'''
    with self.transactionScope() as session:
      exists = session.query(FileHistory).filter(FileHistory.Url==url).all()
      if len(exists) > 0:
        # This file has been opened before. Update the timestamp.
        exists[0].TimeStamp = datetime.now()
      else:
        # This is a new file: add it to the list
        entry = FileHistory(Url=url)
        session.add(entry)

  def currentFile(self):
    ''' Returns the current (latest) file.
    '''
    with self.transactionScope() as session:
      record = session.query(FileHistory).order_by(FileHistory.TimeStamp.desc()).first()
      if record:
        return record.Url


def getConfig(*args, **kwds):
  return ConfigManager.getTheConfig().getConfig(*args, **kwds)

def getRecentFiles(*args, **kwds):
  return ConfigManager.getTheConfig().getRecentFiles(*args, **kwds)

def currentFile(*args, **kwds):
  return ConfigManager.getTheConfig().currentFile(*args, **kwds)

def addRecentFile(*args, **kwds):
  return ConfigManager.getTheConfig().addRecentFile(*args, **kwds)

def currentFile(*args, **kwds):
  return ConfigManager.getTheConfig().currentFile(*args, **kwds)
