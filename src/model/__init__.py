'''
Created on Sep 25, 2013

@author: EHWAAL

Copyright (C) 2014 Evert van de Waal
This program is released under the conditions of the GNU General Public License.
'''

from contextlib import contextmanager
from sqlalchemy.ext.declarative import declarative_base, declared_attr
from sqlalchemy import Column, Integer, String, Float, Text, Boolean, DateTime, Enum
from sqlalchemy import ForeignKey, create_engine, Table
from sqlalchemy.orm import relationship, backref, sessionmaker
from sqlalchemy.types import TypeDecorator
from datetime import datetime
from collections import OrderedDict

VERSION = 2


# TODO: Implement an undo method


class MyBase(object):
  ''' Base class for database tables. '''
  Id = Column(Integer, primary_key=True)

  @declared_attr
  def __tablename__(cls):       #pylint:disable=E0213
    ''' Derive the name of the table from the name of the class. '''
    return cls.__name__.lower() #pylint:disable=E1101
  
  @classmethod
  def getFields(cls):
    ''' Get the names of the columns in the table, or the fields in a record '''
    cols = cls.__table__.columns.keys()
    # Check if any base is also a table.
    for b in cls.__bases__:
      if issubclass(b, MyBase) and hasattr(b, '__table__'):
        cols = b.getFields() + cols
    return  cols
  
  @classmethod
  def getColumns(cls):
    ''' Get a list of columns associated with this record. '''
    cols = OrderedDict(cls.__table__.columns)
    # Check if any base is also a table.
    for b in cls.__bases__:
      if issubclass(b, MyBase) and hasattr(b, '__table__'):
        cols.update(b.getColumns())
    return  cols
    
  
  @classmethod
  def create(cls, engine):
    ''' Create a table in a database '''
    cls.__table__.create(engine) #pylint:disable=E1101

  @classmethod
  def getTables(cls):
    ''' return all tables defined with this class as base. '''
    tables = []
    tables = cls.__subclasses__()   # pylint: disable=E1101
    for c in cls.__subclasses__():  # pylint: disable=E1101
      tables += c.getTables()
    return tables
    
  def __repr__(self):
    args = ', '.join(['%s=%s'%(field, repr(getattr(self, field))) for field in self.getFields()])
    return '%s(%s)'%(self.__class__.__name__, args)
  
  def toDict(self):
    return {c.name: getattr(self, c.name) for c in self.__table__.columns}


Base = declarative_base(cls=MyBase)


class ManDay(Float):
  ''' Define a custom data type so that custom editors can be used
      to enter / display it.
  '''
  @staticmethod
  def fromString(s):
    ''' Convert a string into a manday. '''
    if s:
      return float(s)
    else:
      return None

def createConvertingDateTime(time_format):
  ''' Create a custom type that automatically converts between strings and
      DateTimes. The class that is returned by this function can be used as
      a database Column. This column will store SQL DateTime objects.
  '''
  class ConvertedDateTime(TypeDecorator):
    ''' A type that converts strings to DateTime objects using a specific format.
    '''
    impl = DateTime
    
    def process_bind_param(self, value, _dialect):  #pylint:disable=R0201
      ''' Convert a string to the datetime stored in the database.
      '''
      if value:
        return datetime.strptime(value, time_format)
      return None
    def process_result_value(self, value, _dialect):  #pylint:disable=R0201
      ''' Convert a datetime to a string. The datetime is what is stored in the dbase.
      '''
      if value:
        return value.strftime(time_format)
      return value
    
  return ConvertedDateTime
    



OPEN_STATES = ['Open', 'Question']
REQUIREMENTS_STATES = OPEN_STATES + ['Done', 'Rejected', 'Duplicate']
PRIORITIES = ['Must', 'Should', 'Could', 'Would']
REQ_TYPES = ['Functional', 'Non-Functional', 'Comment']
week_format = '%Y%W'


class StrWrapper(str):
  pass

class WorkingWeek(TypeDecorator):
  ''' A type that converts strings to DateTime objects using a specific format.
  
  A specific class is needed because strptime does not handle %W without %w...
  '''
  impl = DateTime
  
  @staticmethod
  def fromString(txt):
    # in strptime, %W only works if the weekday (w) is also specified...
    return datetime.strptime(txt+'0', week_format+'%w')
    
  
  def process_bind_param(self, value, _dialect):  #pylint:disable=R0201
    ''' Convert a string to the datetime stored in the database.
    '''
    if value:
      return WorkingWeek.fromString(value)
    return None
  def process_result_value(self, value, _dialect):  #pylint:disable=R0201
    ''' Convert a datetime to a string. The datetime is what is stored in the dbase.
    '''
    if value:
      result = StrWrapper(value.strftime(week_format))
      result.dt = value
      return result
    return value  




###############################################################################
## The elements stored in the database
class ColorPalette(Base):   #pylint:disable=W0232
  ''' This table stores the various colors used in the model. '''
  Color = Column(String)  # An QT color name.

class DbaseVersion(Base):   #pylint:disable=W0232
  ''' Stores the version number of the database. '''
  Version = Column(Integer, default=VERSION)

class ArchitectureBlock(Base):   #pylint:disable=W0232
  ''' A building block of the architecture.
  
  A hierarchy is supported where a block contains smaller, child, blocks.
  '''
  Name = Column(String)
  Description = Column(Text)
  Parent = Column(Integer, ForeignKey('architectureblock.Id'))
  Children = relationship('ArchitectureBlock', passive_deletes=True)
  FunctionPoints = relationship("FunctionPoint", passive_deletes=True)
  Representations = relationship("BlockRepresentation", backref='block_obj',
                                 passive_deletes=True)

class Connection(Base):   #pylint:disable=W0232
  ''' The Architecture Blocks are inter-connected.
  
  The connections are directional so the direction of FP's can be
  determined uniquely.
  '''
  Start = Column(Integer, ForeignKey('architectureblock.Id', ondelete='CASCADE'))
  End = Column(Integer, ForeignKey('architectureblock.Id', ondelete='CASCADE'))
  Description = Column(Text)
  FunctionPoints = relationship("FunctionPoint", passive_deletes=True)


# Define an n-to-m mapper class between planeable items
planeablexref = Table('planeablexref', Base.metadata,
  Column('A', Integer, ForeignKey('planeableitem.Id', ondelete='CASCADE')),
  Column('B', Integer, ForeignKey('planeableitem.Id', ondelete='CASCADE')))



class PlaneableItem(Base):   #pylint:disable=W0232
  ''' Base table for anything that can be planned, such as requirements, 
      function points and projects.
  '''
  short_type = ''
  Name = Column(String)
  # All plannable items can be broken down into other planeable items
  Parent = Column(Integer, ForeignKey('planeableitem.Id'))
  Description = Column(Text)
  StateChanges = relationship('PlaneableStatus', order_by='PlaneableStatus.TimeStamp.desc()')
  Children    = relationship('PlaneableItem', order_by='PlaneableItem.Name')
  Priority    = Column(Enum(*PRIORITIES), default=PRIORITIES[0])
  ItemType    = Column(String(50))
  AItems      = relationship('PlaneableItem', primaryjoin='planeablexref.c.A==PlaneableItem.Id',
                             secondary=planeablexref, secondaryjoin='planeablexref.c.B==PlaneableItem.Id')
  BItems      = relationship('PlaneableItem', primaryjoin='planeablexref.c.B==PlaneableItem.Id',
                             secondary=planeablexref, secondaryjoin='planeablexref.c.A==PlaneableItem.Id')

  __mapper_args__ = {
      'polymorphic_identity':'planeableitem',
      'polymorphic_on':ItemType
  }
  
  
  @classmethod
  def getTree(cls, session, with_root=True):
    ''' Return a tree of items.
        If with_root is True, returns a dictionary, else a list.
    '''
    elements = session.query(cls).filter(PlaneableItem.Parent==None).\
                                  order_by(PlaneableItem.ItemType).all()
    if with_root:
      roots = {}
      for e in elements:
        l = roots.setdefault(e.ItemType, [])
        l.append(e)
      return roots
    return elements

  @staticmethod  
  def getAllOffspring(details, offspring=None):
    ''' Get all children, grandchildren etc (recursively).
        The offspring is added to the 'offspring' list, if present.
     '''
    if offspring is None:
      offspring = []
    offspring += details.Children
    for child in details.Children:
      PlaneableItem.getAllOffspring(child, offspring)
    return offspring
  
  def getParents(self):
    ''' Get all the parents, recursively. Returns a list where the first item is the root.
    '''
    detail = self
    parents = [detail]
    while detail.Parent:
      detail = detail.Parent
      parents.append(detail)
    parents.reverse()
    return parents
    


class FunctionPoint(PlaneableItem):   #pylint:disable=W0232
  ''' A Function Point represents a bit of communication between parts of the architecture.
  
  These communications can be counted to get a measurement of the amount of work involved in
  creating the system.
  
  Sometimes, a significant of 'internal' processing is required before a message can be sent.
  This work can be represented by function points that are inside a block.
  '''
  short_type = 'fp'

  # Override the Id inherited from Base
  Id = Column(Integer, ForeignKey('planeableitem.Id'), primary_key=True)
  # FPs are linked to a connection.
  Connection = Column(Integer, ForeignKey('connection.Id', ondelete='CASCADE'))
  # Some FPs are linked to a block, not to a connection. These are 'internal' fps.
  Block = Column(Integer, ForeignKey('architectureblock.Id', ondelete='CASCADE'))
  # Complex FP's can be split into smaller ones. The complex ones should not be counted!
  # This flag is true if the message goes against the connection direction
  isResponse = Column(Boolean)
#  Representations = relationship("fptousecase",
#                                 backref=backref("functionpoint", cascade="delete"))
  __mapper_args__ = {
      'polymorphic_identity':'functionpoint',
      #'inherit_condition': (Id == PlaneableItem.Id)
  }

class View(PlaneableItem):   #pylint:disable=W0232
  ''' A 'view' on the architecture, showing certain blocks and interconnection.
  A view combines static elements (blocks) and dynamic elements (function points / actions).
  Due to the dynamic elements, a view can be planned for implementation.
  '''
  short_type = 'view'

  # Override the Id inherited from Base
  Id = Column(Integer, ForeignKey('planeableitem.Id'), primary_key=True)
  Refinement = Column(Integer, ForeignKey('functionpoint.Id', ondelete='CASCADE'), nullable=True)
  #Requirements = relationship('Req2UseCase')
#  Blocks = relationship("blockrepresentation",
#                        backref=backref("view", cascade="delete"))
#  Actions = relationship("fptousecase",
#                         backref=backref("view", cascade="delete"))
  __mapper_args__ = {
      'polymorphic_identity':'view'
  }


class BlockRepresentation(Base):   #pylint:disable=W0232
  ''' A Architecture Block can be seen on many views.
  '''
  Block = Column(Integer, ForeignKey('architectureblock.Id', ondelete='CASCADE'))
  View = Column(Integer, ForeignKey('view.Id', ondelete='CASCADE'))
  x = Column(Float)
  y = Column(Float)  
  height = Column(Float)
  width = Column(Float)
  Order = Column(Integer)
  Color = Column(Integer, ForeignKey('colorpalette.Id'), nullable=True)   # Index into a pallette
  Font  = Column(String)
  IsMultiple = Column(Boolean)
  
  
class FpToView(Base):   #pylint:disable=W0232
  ''' Mapper class that links function points to use cases.
  
  In each use case, the FPs are ordered. Thus these use cases are closely linked
  to test cases describing cause and effect.
  
  The co-ordinates are an offset from where they would normally be plotted.
  '''
  View = Column(Integer, ForeignKey('view.Id', ondelete='CASCADE'))
  FunctionPoint = Column(Integer, ForeignKey('functionpoint.Id', ondelete='CASCADE'))
  Order = Column(Integer)
  Xoffset = Column(Float, default=0.0)
  Yoffset = Column(Float, default=0.0)


class HiddenConnection(Base):   #pylint:disable=W0232
  ''' In some views, not all connections for the blocks in the drawing are wanted.
      Allow connections to be hidden.
  '''
  View = Column(Integer, ForeignKey('view.Id', ondelete='CASCADE'))
  Connection = Column(Integer, ForeignKey('connection.Id', ondelete='CASCADE'))
  

class Requirement(PlaneableItem):   #pylint:disable=W0232
  ''' Requirements management is incorporated.
  Requirements, unlike function points, are not linked to the architecture.
  '''
  short_type = 'req'
  
  # Override the Id inherited from Base
  Id   = Column(Integer, ForeignKey('planeableitem.Id'), primary_key=True)
  Type = Column(Enum(*REQ_TYPES), default=REQ_TYPES[0])
  
  __mapper_args__ = {
      'polymorphic_identity':'requirement'
  }


class PlaneableStatus(Base):
  ''' Status for a planeable item. '''
  Planeable     = Column(Integer, ForeignKey('planeableitem.Id', ondelete='CASCADE'), default=None)
  Description   = Column(Text)
  TimeStamp     = Column(DateTime, default=datetime.now)
  Status        = Column(Enum(*REQUIREMENTS_STATES))
  TimeRemaining = Column(ManDay, default=0.0)
  TimeSpent     = Column(ManDay)
  AssignedTo    = Column(ForeignKey('worker.Id'))

  def __init__(self, **kwds):
    if 'TimeStamp' in kwds and isinstance(kwds['TimeStamp'], basestring):
      kwds['TimeStamp'] = datetime.strptime(kwds['TimeStamp'], '%Y-%m-%d %H:%M:%S.%f')
    Base.__init__(self, **kwds) # pylint:disable=W0233
    
  def isOpen(self):
    ''' Determine if the planeable is 'open' or 'closed'.
    '''
    return self.Status in OPEN_STATES
    
      


###############################################################################
## Project Planning

class Worker(Base):   #pylint:disable=W0232
  ''' Stores details for a worker on this project. '''
  Name = Column(String)

class Project(PlaneableItem):   #pylint:disable=W0232
  ''' A project is something a worker can be assigned to. '''
  short_type = 'prj'
  
  # Override the Id inherited from Base
  Id   = Column(Integer, ForeignKey('planeableitem.Id'), primary_key=True)
  FirstWeek = Column(WorkingWeek)
  LastWeek  = Column(WorkingWeek)
  
  Effort = relationship('PlannedEffort', passive_deletes=True)
  
  __mapper_args__ = {
      'polymorphic_identity':'project'
  }


class PlannedEffort(Base):   #pylint:disable=W0232
  ''' Plan the amount of time a worker can work on a project '''  
  Worker  = Column(Integer, ForeignKey('worker.Id', ondelete='CASCADE'))
  Project = Column(Integer, ForeignKey('project.Id', ondelete='CASCADE'))
  Week    = Column(WorkingWeek)  # If null: default effort for worker on project
  Hours   = Column(Float)



###############################################################################
## Database connections
the_engine = None
SessionFactory = None

def changeEngine(new_engine, create=True):
  ''' Change the database engine used by the Session Factory.
  '''
  global the_engine, SessionFactory  #pylint:disable=W0603
  the_engine = new_engine
  SessionFactory = sessionmaker(bind=new_engine)
  if create:
    Base.metadata.create_all(new_engine)


def connectSession(url):
  ''' Connect to a database and return a session '''
  engine = create_engine(url)
  changeEngine(engine)
  return SessionFactory()

@contextmanager
def sessionScope(session):
  """Provide a transactional scope around a series of operations."""
  try:
    yield session
    session.commit()
  except:
    session.rollback()
    raise

