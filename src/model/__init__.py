'''
Created on Sep 25, 2013

@author: EHWAAL

Copyright (C) 2014 Evert van de Waal
This program is released under the conditions of the GNU General Public License.
'''
import re
import sys
import inspect
from urlparse import urlparse
from contextlib import contextmanager
from sqlalchemy.ext.declarative import declarative_base, declared_attr
from sqlalchemy import Column, Integer, String, Float, Text, Boolean, DateTime, Enum
from sqlalchemy import ForeignKey, create_engine, Table, UniqueConstraint
from sqlalchemy.orm import relationship, backref, sessionmaker
from sqlalchemy.types import TypeDecorator
from sqlalchemy.sql.functions import GenericFunction
from sqlalchemy.sql import func
from sqlalchemy.engine import Engine
from sqlalchemy import event
from model.history import Versioned
from datetime import datetime, date, timedelta
from collections import OrderedDict

VERSION = 13


# Determine which encoding to use when interacting with files
# The database stores unicode, and unicode is used inside the program by Python
ENCODING = 'cp1252' if 'win' in sys.platform else 'utf-8'



SQLITE_URL_PREFIX = 'sqlite:///'


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
  READONLY = []
  HIDDEN = []

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
  def create(cls, engine, checkfirst=False):
    ''' Create a table in a database '''
    cls.__table__.create(engine, checkfirst) #pylint:disable=E1101
    
  @classmethod
  def drop(cls, engine, checkfirst=False):
    ''' delete (drop) a table from the database '''
    cls.__table__.drop(engine, checkfirst)

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
    ''' Return the columns that can be edited manually by users.
    
        The standard implementation returns all columns except primary keys
        and the 'ItemType' and 'AnchorType' columns.
    '''
    hidden = set()
    for base in inspect.getmro(cls):
      hidden = hidden.union(base.__dict__.get('HIDDEN', []))
    cols = cls.getColumns().values()
    names = []
    columns = []
    for c in cols:
      if c.primary_key:
        continue
      if c in hidden:
        continue
      names.append(c.name)
      columns.append(c)
    
    return names, columns

  @staticmethod
  def getTable(name):
    for table in Base.getTables():
      if table.__tablename__ == name.lower():
        return table
    raise RuntimeError('Table name %s not found!'%name)



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
  r = re.compile('([0-9.]*)\s*([a-zA-Z]*)')
  # TODO: Make these conversion units configurable
  HRS_PER_DAY = 8
  DAYS_PER_WEEK = 5
  DAYS_PER_MONTH = 21

  @staticmethod
  def fromString(s):
    ''' Convert a string into a manday. '''
    try:
      return float(s)
    except:
      if s:
        parts = ManDay.r.match(s).groups()
        unit = parts[1]
        amount = parts[0]
        u = unit[0].lower()
        if u == 'm':
          # Unit is 'months'
          return ManDay.DAYS_PER_MONTH * float(amount)
        if u in ['h', 'u']:
          # Unit is 'hours'
          return float(amount) / ManDay.HRS_PER_DAY
        if u == 'w':
          # Unit is 'weeks'
          return ManDay.DAYS_PER_WEEK * float(amount)
        if u == 'd':
          # Unit is 'days'
          return float(amount)
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
  INPROGRESS = 'In Progress'
  TESTING    = 'Testing'

# Define a subset of states where the workitem is considered 'open'.
OPEN_STATES = [REQUIREMENTS_STATES.OPEN, REQUIREMENTS_STATES.QUESTION,
               REQUIREMENTS_STATES.INPROGRESS, REQUIREMENTS_STATES.TESTING]


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
    def iso_year_start(iso_year):
      "The gregorian calendar date of the first day of the given ISO year"
      fourth_jan = date(iso_year, 1, 4)
      delta = timedelta(fourth_jan.isoweekday()-1)
      return fourth_jan - delta

    "Gregorian calendar date for the given ISO year, week and day"
    iso_year = int(txt[:4])
    iso_week = int(txt[4:6])
    year_start = iso_year_start(iso_year)
    return year_start + timedelta(weeks=iso_week-1)
    
  
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
      result = '%i%02i'%value.isocalendar()[:2]
      return result
    return value  


###############################################################################
## The elements stored in the database
class DbaseVersion(Base):   #pylint:disable=W0232
  ''' Stores the version number of the database. '''
  Version = Column(Integer, default=VERSION)


###############################################################################
## Structural model
class ArchitectureBlock(Base, Versioned):   #pylint:disable=W0232
  ''' A building block of the architecture.
  
  A hierarchy is supported where a block contains smaller, child, blocks.
  '''
  Name = Column(String)
  Description = Column(Text)
  Parent = Column(Integer, ForeignKey('architectureblock.Id', deferrable=True))
  Children = relationship('ArchitectureBlock', passive_deletes=True)

  HIDDEN = [Parent]


class BlockConnection(Base, Versioned):   #pylint:disable=W0232
  ''' The Architecture Blocks are inter-connected.
  
  The connections are directional so the direction of FP's can be
  determined uniquely.
  '''
  Start          = Column(Integer, ForeignKey('architectureblock.Id', ondelete='CASCADE'))
  End            = Column(Integer, ForeignKey('architectureblock.Id', ondelete='CASCADE'))
  Name           = Column(String)
  Description    = Column(Text)

  theEnd        = relationship(ArchitectureBlock, uselist=False, foreign_keys=[End])
  theStart      = relationship(ArchitectureBlock, uselist=False, foreign_keys=[Start])

  HIDDEN = [Start, End]


# Define an n-to-m mapper class between planeable items
planeablexref = Table('planeablexref', Base.metadata,
  Column('A', Integer, ForeignKey('planeableitem.Id', ondelete='CASCADE')),
  Column('B', Integer, ForeignKey('planeableitem.Id', ondelete='CASCADE')))


###############################################################################
## Behavioural model, based on 'planable items' (requirements, usecases, etc).
class PlaneableItem(Base, Versioned):   #pylint:disable=W0232
  ''' Base table for anything that can be planned, such as requirements, 
      function points and projects.
  '''
  short_type = ''
  Name        = Column(String)
  # All plannable items can be broken down into other planeable items
  Parent      = Column(Integer, ForeignKey('planeableitem.Id', deferrable=True))
  Description = Column(Text)
  Children    = relationship('PlaneableItem', order_by='PlaneableItem.Name')
  ParentItem  = relationship('PlaneableItem', remote_side='PlaneableItem.Id')
  Priority    = Column(Enum(*PRIORITIES.values(), name='PRIORITIES'), default=PRIORITIES.MUST)
  ItemType    = Column(String(50))
  Created     = Column(DateTime, default=datetime.now)
  AItems      = relationship('PlaneableItem', primaryjoin='planeablexref.c.A==PlaneableItem.Id',
                             secondary=planeablexref, secondaryjoin='planeablexref.c.B==PlaneableItem.Id')
  BItems      = relationship('PlaneableItem', primaryjoin='planeablexref.c.B==PlaneableItem.Id',
                             secondary=planeablexref, secondaryjoin='planeablexref.c.A==PlaneableItem.Id')

  __mapper_args__ = {
      'polymorphic_identity':'planeableitem',
      'polymorphic_on':ItemType
  }

  HIDDEN   = [ItemType, Parent]
  READONLY = [Created]

  
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

  def getAllOffspring(self, offspring=None):
    ''' Get all children, grandchildren etc (recursively).
        The offspring is added to the 'offspring' list, if present.
     '''
    if offspring is None:
      offspring = []
    for child in self.Children:
      offspring.append(child)
      if child.Children:
        child.getAllOffspring(offspring)
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
    
class PlaneableStatus(Base, Versioned):
  ''' Status for a planeable item. '''
  Planeable     = Column(Integer, ForeignKey('planeableitem.Id', ondelete='CASCADE'), default=None)
  Description   = Column(Text)
  TimeStamp     = Column(DateTime, default=datetime.now)
  Status        = Column(Enum(*REQUIREMENTS_STATES.values(), name='REQ_STATES'))
  TimeRemaining = Column(ManDay, default=0.0)
  TimeSpent     = Column(ManDay)
  AssignedTo    = Column(ForeignKey('worker.Id'))

  theItem  = relationship('PlaneableItem',
                backref=backref('StateChanges', order_by='PlaneableStatus.TimeStamp.desc()'))
  theWorker = relationship('Worker')

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
    

#######################################
# Specific planeable items.
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
  Connection = Column(Integer, ForeignKey('blockconnection.Id', ondelete='CASCADE'))
  # Some FPs are linked to a block, not to a connection. These are 'internal' fps.
  Block = Column(Integer, ForeignKey('architectureblock.Id', ondelete='CASCADE'))
  # Complex FP's can be split into smaller ones. The complex ones should not be counted!
  # This flag is true if the message goes against the connection direction
  isResponse = Column(Boolean)
#  Representations = relationship("fptousecase",
#                                 backref=backref("functionpoint", cascade="delete"))

  theConnection = relationship('BlockConnection', uselist=False, backref='FunctionPoints')
  theBlock      = relationship('ArchitectureBlock', backref='FunctionPoints',
                               uselist=False)

  __mapper_args__ = {
      'polymorphic_identity':'functionpoint',
      #'inherit_condition': (Id == PlaneableItem.Id)
  }

  HIDDEN = [Connection, Block]

class Requirement(PlaneableItem):   #pylint:disable=W0232
  ''' Requirements management is incorporated.
  Requirements, unlike function points, are not linked to the architecture.
  '''
  short_type = 'req'
  
  # Override the Id inherited from Base
  Id   = Column(Integer, ForeignKey('planeableitem.Id'), primary_key=True)
  Type = Column(Enum(*REQ_TYPES.values(), name='REQ_TYPES'), default=REQ_TYPES.FUNCTIONAL)
  
  __mapper_args__ = {
      'polymorphic_identity':'requirement'
  }


class Style(Base):
  ''' Stores styling details in a semicolon-separated string.
      Style items include:
        background: the standard QT style details.
        pen:        the standard QT style details.
        start_arrow: the polygon drawn at the start of a line.
        end_arrow:   the polygon drawn at the end of a line.
        font:        standard QT font details.
  '''
  Name    = Column(String)
  Details = Column(Text)


class View(PlaneableItem):   #pylint:disable=W0232
  ''' A 'view' on the architecture, showing certain blocks and interconnection.
  A view combines static elements (blocks) and dynamic elements (function points / actions).
  Due to the functional elements, a view can be planned for implementation.
  '''
  short_type = 'view'

  # Override the Id inherited from Base
  Id = Column(Integer, ForeignKey('planeableitem.Id'), primary_key=True)
  Refinement = Column(Integer, ForeignKey('functionpoint.Id', ondelete='CASCADE'), nullable=True)
  style      = Column(Integer, ForeignKey('style.Id'), nullable=True)

  __mapper_args__ = {
      'polymorphic_identity':'view'
  }

  HIDDEN = [Refinement]


###############################################################################
## Graphical Representation
class Representation(object):
  ''' A mix-in to indicate that this is a representation of an underlying item
  '''
  pass

class Anchor(Base, Versioned):   #pylint:disable=W0232
  ''' Base table for anything that can be planned, such as requirements, 
      function points and projects.
  '''
  View       = Column(Integer, ForeignKey('view.Id', ondelete='CASCADE'))
  style_role = Column(String)
  Order      = Column(Integer)    # Zero means the item is at the top.
  AnchorType = Column(String(50))

  theView = relationship('View', uselist=False)

  __mapper_args__ = {
      'polymorphic_identity':'anchor',
      'polymorphic_on':AnchorType
  }

  HIDDEN = [AnchorType]


class BlockRepresentation(Anchor, Representation):   #pylint:disable=W0232
  ''' A Architecture Block can be seen on many views.
  '''
  # Override the Id inherited from Base
  Id = Column(Integer, ForeignKey(Anchor.Id, ondelete='CASCADE'), primary_key=True)
  Block  = Column(Integer, ForeignKey('architectureblock.Id', ondelete='CASCADE'))
  x      = Column(Float)
  y      = Column(Float)  
  height = Column(Float)
  width  = Column(Float)
  IsMultiple = Column(Boolean)

  theDetails      = relationship('ArchitectureBlock', backref='Representations',
                               uselist=False)

  # theBlock defined as back reference
  
  __mapper_args__ = {
      'polymorphic_identity':'blockrepresentation',
  }



class UsecaseRepresentation(Anchor, Representation):
  ''' A use case can be defined inside another use case, and shown in the view.
      Thus 'Use Case Diagrams' can be created.
  '''
  # Override the Id inherited from Base
  Id = Column(Integer, ForeignKey(Anchor.Id, ondelete='CASCADE'), primary_key=True)
  # We can not use the column 'View' here, as that is already part of the Anchor table.
  Parent = Column(Integer, ForeignKey('view.Id', ondelete='CASCADE'))
  x      = Column(Float)
  y      = Column(Float)
  height = Column(Float)
  width  = Column(Float)

  theDetails = relationship('View', backref='Representations', foreign_keys=[Parent],
                               uselist=False)

  __mapper_args__ = {
      'polymorphic_identity':'usecaserepresentation',
  }


class ConnectionRepresentation(Anchor, Representation):
  ''' A connection has many view details that can be set '''
  # Override the Id inherited from Base
  Id = Column(Integer, ForeignKey(Anchor.Id, ondelete='CASCADE'), primary_key=True)
  Connection = Column(Integer, ForeignKey('blockconnection.Id', ondelete='CASCADE'), nullable=False)
  Start      = Column(Integer, ForeignKey(Anchor.Id, ondelete='CASCADE'), nullable=False)
  End        = Column(Integer, ForeignKey(Anchor.Id, ondelete='CASCADE'), nullable=False)

  theDetails = relationship(BlockConnection, uselist=False)
  theEnd        = relationship(Anchor, uselist=False, foreign_keys=[End])
  theStart      = relationship(Anchor, uselist=False, foreign_keys=[Start])

  __mapper_args__ = {
      'polymorphic_identity':'connectionrepresentation',
      'inherit_condition': (Id == Anchor.Id)
  }

  
class FpRepresentation(Anchor, Representation):   #pylint:disable=W0232
  ''' Mapper class that links function points to use cases.
  
  In each use case, the FPs are ordered. Thus these use cases are closely linked
  to test cases describing cause and effect.
  
  The co-ordinates are an offset from where they would normally be plotted.
  '''
  # Override the Id inherited from Base
  Id = Column(Integer, ForeignKey(Anchor.Id, ondelete='CASCADE'), primary_key=True)
  FunctionPoint = Column(Integer, ForeignKey(FunctionPoint.Id, ondelete='CASCADE'))
  AnchorPoint   = Column(Integer, ForeignKey(Anchor.Id, ondelete='CASCADE'), nullable=False)
  Xoffset = Column(Float, default=0.0)
  Yoffset = Column(Float, default=0.0)
  SequenceNr = Column(Integer)

  theDetails = relationship('FunctionPoint', uselist=False)
  theAnchor  = relationship(Anchor, uselist = False, foreign_keys=[AnchorPoint])
  
  __mapper_args__ = {
      'polymorphic_identity':'fprepresentation',
      'inherit_condition': (Id == Anchor.Id)
  }


class Annotation(Anchor):
  ''' An annotation is a comment or description that can be added to a View. '''
  # Override the Id inherited from Base
  Id = Column(Integer, ForeignKey(Anchor.Id, ondelete='CASCADE'), primary_key=True)
  AnchorPoint = Column(Integer,  ForeignKey(Anchor.Id, ondelete='CASCADE'),
                       nullable=True)
  x           = Column(Float) # Relative to anchor, if any
  y           = Column(Float) # Relative to anchor, if any  
  height      = Column(Float)
  width       = Column(Float)
  Description = Column(Text)

  theAnchor = relationship(Anchor, uselist = False, foreign_keys=[AnchorPoint])

  __mapper_args__ = {
      'polymorphic_identity':'annotation',
      'inherit_condition': (Id == Anchor.Id)
  }


  @classmethod
  def editableColumnDetails(cls):
    return ['Description'], [cls.Description]
  

###############################################################################
## Project Planning

class Worker(Base, Versioned):   #pylint:disable=W0232
  ''' Stores details for a worker on this project. '''
  Name = Column(String)
  Rate = Column(Float)

class Project(PlaneableItem, Versioned):   #pylint:disable=W0232
  ''' A project is something a worker can be assigned to. '''
  short_type = 'prj'
  
  # Override the Id inherited from Base
  Id   = Column(Integer, ForeignKey('planeableitem.Id'), primary_key=True)
  FirstWeek = Column(WorkingWeek)
  LastWeek  = Column(WorkingWeek)
  Budget    = Column(Float)
  
  __mapper_args__ = {
      'polymorphic_identity':'project'
  }


class PlannedEffort(Base, Versioned):   #pylint:disable=W0232
  ''' Plan the amount of time a worker can work on a project '''  
  Worker  = Column(Integer, ForeignKey('worker.Id', ondelete='CASCADE'))
  Project = Column(Integer, ForeignKey('project.Id', ondelete='CASCADE'))
  Week    = Column(WorkingWeek)  # If null: default effort for worker on project
  Hours   = Column(Float)
  IsActual= Column(Boolean)

  theProject = relationship('Project', backref='Effort')

  __table_args__ = (UniqueConstraint(Worker, Project, Week, IsActual,
                                     name='_planned_effort_constraint'),
                     )

class Bug(PlaneableItem):
  ''' A Bug is reported by a non-programmer, and then examined by a programmer.

  '''
  short_type = 'bug'

  # Override the Id inherited from Base
  Id   = Column(Integer, ForeignKey('planeableitem.Id'), primary_key=True)
  ReportedBy = Column(ForeignKey('worker.Id'))

  __mapper_args__ = {
      'polymorphic_identity':'bug'
  }

  READONLY = []




###############################################################################
## Versioning
class ChangeLog(Base):
  ''' Keep track of all changes in the model '''
  RecordType = Column(String)
  RecordId   = Column(String)
  ChangeType = Column(Enum(*CHANGE_TYPE.values(), name='CHANGE_TYPES'))
  TimeStamp  = Column(DateTime, default=datetime.now)
  Details    = Column(Text)



###############################################################################
## Record Order

order = [ArchitectureBlock, BlockConnection, Style, Worker] + PlaneableItem.__subclasses__() + \
        [PlaneableStatus, PlannedEffort, ChangeLog] + Anchor.__subclasses__()

###############################################################################
## Database connections
the_engine = None
SessionFactory = None
check_fkeys = True
the_url = None


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
  if the_url and the_url.startswith('sqlite'):
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
    raise RuntimeError('Only SQLITE database supported for upgrade')
  return parts.path[1:]
  

def changeEngine(new_engine, create=True):
  ''' Change the database engine used by the Session Factory.
  '''
  global the_engine, SessionFactory  #pylint:disable=W0603
  the_engine = new_engine
  SessionFactory = sessionmaker(bind=new_engine)
  if create:
    Base.metadata.create_all(new_engine)
    session = SessionFactory()
    ver = session.query(DbaseVersion).all()
    if not ver:
      # The database is empty. Initiallise it.
      session.add(DbaseVersion())
      session.commit()
  
def clearEngine():
  global the_engine, SessionFactory
  if the_engine:
    the_engine = None
    SessionFactory = None
    
def open(url, create=False):
  global the_url
  the_url = url
  engine = create_engine(url, echo=True)
  changeEngine(engine, create)
    
def cleanDatabase():
  ''' First drops all tables, then re-creates them. '''
  Base.metadata.drop_all(the_engine)
  Base.metadata.create_all(the_engine)


def createDatabase(url):
  ''' Create a new database from the URL
  '''
  global the_url
  old_url = the_url
  parts = urlparse(url)
  if parts[0].startswith('postgresql'):
    url_admin = '%s://%s/postgres'%(parts.scheme, parts.netloc)
    engine = create_engine(url_admin)
  else:
    raise RuntimeError('Scheme %s not supported'%parts.scheme)

  the_url = url
  conn = engine.connect()
  # Close the current transaction
  conn.execute("commit")
  # Create the new database
  db = parts.path.strip('/')
  conn.execute("create database %s"%db)
  conn.close()
  print 'Created database %s'%db
  the_url = old_url

def dropDatabase(url):
  parts = urlparse(url)
  if parts[0].startswith('postgresql'):
    url_admin = '%s://%s/postgres'%(parts.scheme, parts.netloc)
    engine = create_engine(url_admin)
  else:
    raise RuntimeError('Scheme %s not supported'%parts.scheme)

  conn = engine.connect()
  # Close the current transaction
  conn.execute("commit")
  # Create the new database
  db = parts.path.strip('/')
  conn.execute("drop database %s"%db)
  conn.close()
  print 'Dropped database %s'%db


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

def currentScheme():
  if the_url:
    return urlparse(the_url).scheme
  return ''