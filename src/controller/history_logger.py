__author__ = 'ehwaal'


from model.history import versioned_objects
from model import CHANGE_TYPE
from sqlalchemy.orm import attributes, object_mapper
from sqlalchemy.orm.exc import UnmappedColumnError
from sqlalchemy import event
from sqlalchemy.orm.properties import RelationshipProperty



class HistoryLogger(object):
  def __init__(self, session, table):
    self.session = session
    self.table = table
    event.listen(session, 'before_flush', self.before_flush)
    event.listen(session, 'after_flush', self.after_flush)

  def create_version(self, obj, session, deleted=False, new=False):
    ct = CHANGE_TYPE.CHANGE
    if deleted:
      ct = CHANGE_TYPE.DELETE
    elif new:
      ct = CHANGE_TYPE.ADD

    change = self.table(RecordType = obj.__tablename__,
                        RecordId   = obj.Id,
                        ChangeType = ct,
                        Details    = str(obj))

    self.session.add(change)


  def before_flush(self, session, _flush_context, _instances):
    for obj in versioned_objects(session.dirty):
      if session.is_modified(obj):
        self.create_version(obj, session)
    for obj in versioned_objects(session.deleted):
      self.create_version(obj, session, deleted=True)

  def after_flush(self, session, _flush_context):
    ''' The log for new objects is created AFTER flush,
        so that e.g. primary keys are known.
    '''
    for obj in versioned_objects(session.new):
      self.create_version(obj, session, new=True)