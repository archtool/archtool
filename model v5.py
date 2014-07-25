'''
Created on Sep 25, 2013

@author: EHWAAL

Copyright (C) 2014 Evert van de Waal
This program is released under the conditions of the GNU General Public License.
'''
import re
from urlparse import urlparse
from contextlib import contextmanager
from sqlalchemy.ext.declarative import declarative_base, declared_attr
from sqlalchemy import Column, Integer, String, Float, Text, Boolean, DateTime, Enum
from sqlalchemy import ForeignKey, create_engine, Table
from sqlalchemy.orm import relationship, backref, sessionmaker
from sqlalchemy.types import TypeDecorator
from sqlalchemy.sql.functions import GenericFunction
from sqlalchemy.sql import func
from sqlalchemy.engine import Engine
from sqlalchemy import event
from datetime import datetime
from collections import OrderedDict
import export

VERSION = 5


# TODO: Implement an undo method




class Const(object):
  '''Base class for const value classes.
     The const value classes are used to group a set of const values. This base class provides
     a constructor, overwrite protection and inversed lookup.

    You can not extend a set of constants by subclassing: constants from a parent class
    are not included in the child.
  '''

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
    '''Iterator over the (key, value) items in Const object / class.
    
       Functions from the Const class are not included, as these are not stored
       in cls.__dict__ but in cls.__bases__[0].__dict__.
    '''
    for item in cls.__dict__.iteritems():
      if not str(item[0]).startswith('__'):
        yield item
  @classmethod
  def itervalues(cls):
    '''Iterator over the value items in Const object.'''
    for _key, value in cls.iteritems():
      yield value
      
  @classmethod
  def keys(cls):
    ''' iterator over the key names in a Const object '''
    for key, _value in cls.iteritems():
      yield key
      
  @classmethod
  def values(cls):
    ''' Returns a list of values '''
    return [v for _, v in cls.iteritems()]

  @classmethod
  def name(cls, lookup):
    '''Return the string representation of the given constant value.'''
    for key, value in cls.__dict__.iteritems():
      if lookup == value and not str(key).startswith('__'):
        return key
    raise KeyError(lookup)



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
  
  @classmethod
  def editableColumnDetails(cls):
    cols = cls.getColumns().values()
    names = []
    columns = []
    for c in cols:
      if c.primary_key:
        continue
      if len(c.foreign_keys) > 0:
        continue
      if c.name == 'ItemType':
        continue
      names.append(c.name)
      columns.append(c)
    
    return names, columns



Base = declarative_base(cls=MyBase)



# Prepare some stored procedures to be able to sort requirements having various numbering schemes.
class reqnr(GenericFunction):
  ''' The database has a stored function called 'requirement_number' '''
  type = Integer

  INT_DOT_INT_RULE = re.compile('(?:[0-9]*?\.)*([0-9]*)[^\.]')
  CHAR_DOT_LETTER_RULE = re.compile('(?:[0-9a-zA-Z]*?\.)*([a-zA-Z]*)[^\.]')
  
  @staticmethod
  def doIt(value):
    ''' Function to determine the requirement_number for sqlite3 database. '''
    # First try a scheme like 10.23.454 (numbers separated by points)
    # Find the last number: only the last number is used for sorting
    m = reqnr.INT_DOT_INT_RULE.match(value)
    if m and m.groups()[0] != '':
      return int(m.groups()[0])
    # A rule where a character is used as counter. This is converted into a number.
    m = reqnr.CHAR_DOT_LETTER_RULE.match(value)
    if m and m.groups()[0] != '':
      # Treat single characters quickly
      value = m.groups()[0]
      if len(value) == 1:
        return ord(value.lower()) - ord('a')
      # Also handle multiple characters.
      values = [ord(v)-ord('a') for v in value.lower()]
      values = [v*26**i for i, v in enumerate(reversed(values))]
      return sum(values)
    # No ordering scheme recognised
    return 0
  



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
    

class REQUIREMENTS_STATES(Const):
  ''' Defines the possible states for a work item.
  '''
  OPEN = 'Open'
  QUESTION = 'Question'
  DONE = 'Done'
  REJECTED = 'Rejected'
  DUPLICATE = 'Duplicate'

# Define a subset of states where the workitem is considered 'open'.
OPEN_STATES = [REQUIREMENTS_STATES.OPEN, REQUIREMENTS_STATES.QUESTION]


class PRIORITIES(Const):
  ''' Defines the possible priorities for a work item.
  '''
  MUST   = 'Must'
  SHOULD = 'Should'
  COULD  = 'Could'
  WOULD  = 'Would'
  
class REQ_TYPES(Const):
  ''' Defines possible types of entries in a list of requirements.
      The 'Comment' type is used for any requirement that is not an actual
      requirement. These include section and chapter headers.
  '''
  FUNCTIONAL   = 'Functional'
  NON_FUNCTION = 'Non-Functional'
  COMMENT      = 'Comment'
  
class CHANGE_TYPE(Const):
  ''' Defines the possible changes stored in the change log '''
  ADD    = 'Add'
  DELETE = 'Delete'
  CHANGE = 'Change'
  

week_format = '%Y%W'
sql_format  = '%Y-%m-%d %H:%M:%S.%f'


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
    if len(txt) == 6:
      return datetime.strptime(txt+'0', week_format+'%w')
    if txt.count('-')==2 and txt.count(':')==2:
      return datetime.strptime(txt[:26], sql_format)
    
  
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
  Start          = Column(Integer, ForeignKey('architectureblock.Id', ondelete='CASCADE'))
  End            = Column(Integer, ForeignKey('architectureblock.Id', ondelete='CASCADE'))
  Name           = Column(String)
  Description    = Column(Text)
  Role           = Column(String, default='')
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
  Name        = Column(String)
  # All plannable items can be broken down into other planeable items
  Parent      = Column(Integer, ForeignKey('planeableitem.Id'))
  Description = Column(Text)
  StateChanges = relationship('PlaneableStatus', order_by='PlaneableStatus.TimeStamp.desc()')
  Children    = relationship('PlaneableItem', order_by='PlaneableItem.Name') 
  ParentItem  = relationship('PlaneableItem', remote_side='PlaneableItem.Id')
  Priority    = Column(Enum(*PRIORITIES.values()), default=PRIORITIES.MUST)
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
  
  @staticmethod
  def getItemTypeNames():
    ''' Returns the names for all different item types.
        These names are taken from the 'polymorphic identity' string.
    '''
    result = []
    for cls in PlaneableItem.__subclasses__():
      if hasattr(cls, '__mapper_args__'):
        name = cls.__mapper_args__.get('polymorphic_identity', None)
        if not name is None:
          result.append(name)
    return result
  
  def getParents(self):
    ''' Get all the parents, recursively. Returns a list where the first item is the root.
    '''
    detail = self
    parents = [detail]
    while detail.Parent:
      detail = detail.ParentItem
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

class Style(Base):
  ''' Stores styling details in a semicolon-separated string.
      Style items include:
        background: the standard QT style details.
        pen:        the standard QT style details.
        start_arraw: the polygon drawn at the start of a line.
        end_arrow:   the polygon drawn at the end of a line.
        font:        standard QT font details.
  '''
  Name    = Column(String)
  Details = Column(Text)


class View(PlaneableItem):   #pylint:disable=W0232
  ''' A 'view' on the architecture, showing certain blocks and interconnection.
  A view combines static elements (blocks) and dynamic elements (function points / actions).
  Due to the dynamic elements, a view can be planned for implementation.
  '''
  short_type = 'view'

  # Override the Id inherited from Base
  Id = Column(Integer, ForeignKey('planeableitem.Id'), primary_key=True)
  Refinement = Column(Integer, ForeignKey('functionpoint.Id', ondelete='CASCADE'), nullable=True)
  style      = Column(Integer, ForeignKey('style.Id'), nullable=True)
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
  Font  = Column(String)
  IsMultiple = Column(Boolean)
  style_role = Column(String)


class ConnectionRepresentation(Base):
  ''' A connection has many view details that can be set '''
  Connection = Column(Integer, ForeignKey('connection.Id', ondelete='CASCADE'), nullable=False)
  style_role = Column(String)
  
  
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
  style_role = Column(String)


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
  Type = Column(Enum(*REQ_TYPES.values()), default=REQ_TYPES.FUNCTIONAL)
  
  __mapper_args__ = {
      'polymorphic_identity':'requirement'
  }


class PlaneableStatus(Base):
  ''' Status for a planeable item. '''
  Planeable     = Column(Integer, ForeignKey('planeableitem.Id', ondelete='CASCADE'), default=None)
  Description   = Column(Text)
  TimeStamp     = Column(DateTime, default=datetime.now)
  Status        = Column(Enum(*REQUIREMENTS_STATES.values()))
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
  
  @staticmethod
  def getLatestQuery(session):
    ''' Return the set of latest states.
        Returns tuples of (Id, TimeStamp). '''
    return session.query(PlaneableStatus, func.max(PlaneableStatus.TimeStamp)).\
                   group_by(PlaneableStatus.Planeable)
    
      


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
## Annotations
class Annotation(Base):
  ''' An annotation is a comment or description that can be added to a View. '''
  View        = Column(Integer, ForeignKey('view.Id', ondelete='CASCADE'))
  AnchorId    = Column(Integer, nullable=True)
  AnchorType  = Column(String, nullable=True)
  x           = Column(Float) # Relative to anchor, if any
  y           = Column(Float) # Relative to anchor, if any  
  height      = Column(Float)
  width       = Column(Float)
  Order       = Column(Integer)
  style_role  = Column(String)
  Description = Column(Text)
  
  @classmethod
  def editableColumnDetails(cls):
    return ['Description'], [cls.Description]


###############################################################################
## Versioning
class ChangeLog(Base):
  ''' Keep track of all changes in the model '''
  RecordType = Column(String)
  RecordId   = Column(String)
  ChangeType = Column(Enum(*CHANGE_TYPE.values()))
  TimeStamp  = Column(DateTime, default=datetime.now)
  Details    = Column(Text)



###############################################################################
## Database connections
the_engine = None
SessionFactory = None
check_fkeys = True


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
  cursor = dbapi_connection.cursor()
  if check_fkeys:
    cursor.execute("PRAGMA foreign_keys=ON")
  else:
    cursor.execute("PRAGMA foreign_keys=OFF")
  cursor.close()
  
  connection_record.connection.create_function('reqnr', 1, reqnr.doIt)


def fnameFromUrl(url):
  parts = urlparse(url)
  if parts.scheme != 'sqlite':
    # This only works for sqlite, file-based databases.
    return None
  return parts.path[1:]
  

def changeEngine(new_engine, create=True):
  ''' Change the database engine used by the Session Factory.
  '''
  global the_engine, SessionFactory  #pylint:disable=W0603
  the_engine = new_engine
  SessionFactory = sessionmaker(bind=new_engine)
  if create:
    Base.metadata.create_all(new_engine)
  
def clearEngine():
  global the_engine, SessionFactory
  if the_engine:
    the_engine = None
    SessionFactory = None
    
def open(url):
  engine = create_engine(url)
  changeEngine(engine, False)
    
def cleanDatabase():
  ''' First drops all tables, then re-creates them. '''
  Base.metadata.drop_all(the_engine)
  Base.metadata.create_all(the_engine)

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

