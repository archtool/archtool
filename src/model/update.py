'''
Update a database to be opened to the most recent version.
'''

from model import VERSION, sessionmaker, sessionScope
import re

__author__ = 'ehwaal'


class SQLUpdater(object):
  ''' Updater for generic SQL databases.

      Can be subclassed in case specific updates are problematic for specific RDMSes.

      Mainly raw SQL is used, because the database may not be compatible with the current model.

      Conversion functions must have the name update<version>to<version>; these are
      automatically detected.
  '''
  def __init__(self, engine):
    self.engine = engine
    pttrn = re.compile('update([0-9])+to([0-9]+)')
    self.handlers = {}

    dicts = dict(self.__dict__)
    for b in self.__class__.__mro__:
      dicts.update(b.__dict__)

    for name, func in dicts.items():
      m = pttrn.match(name)
      if m:
        # Store the member function. We need to make it a bound function first.
        self.handlers[int(m.groups()[0])] = func.__get__(self)

  def update(self):
    ''' Update the database.
    '''
    # Determine the current version.
    q = 'SELECT MAX(Version) FROM "dbaseversion";'
    version = self.engine.execute(q).first()[0]
    # Call the appropriate update functions, in the right order.
    while version < VERSION:
      updater = self.handlers.get(version, None)
      if updater is None:
        raise RuntimeError('Can not update database')
      new_version, queries = updater()
      queries.append('UPDATE dbaseversion SET Version=%i WHERE Version=%i;'%(new_version, version))
      self.executeQueries(queries)
      version = new_version

    # Delete the old database versions.
    q = 'DELETE FROM "dbaseversion" WHERE "Version" != %s;'%VERSION
    self.engine.execute(q)


  def executeQueries(self, queries):
    ''' Execute a set of queries, using a transaction.
    '''
    session = sessionmaker(bind=self.engine)()
    with sessionScope(session) as s:
      for q in queries:
        s.execute(q)


  def update6to7(self):
    ''' Changes: connection renamed to blockconnection, also in foreign key relations.
    '''
    return 7, ['ALTER TABLE connection RENAME TO blockconnection;']

  def update7to8(self):
    return 8, ['ALTER TABLE fprepresentation ADD COLUMN SequenceNr INTEGER;']

  def update8to9(self):
    # No update needed for SQLite.
    return 9, []

  def update9to10(self):
    return 10, ['ALTER TABLE bug ADD COLUMN ReportedOn DATETIME']



class PostgresqlUpdated(SQLUpdater):
  def update8to9(self):
    # Assume that the version is 9.1 or higher...
    return 9, ["ALTER TYPE REQ_STATUS ADD VALUE 'In Progress' AFTER 'Duplicate'",
               "ALTER TYPE REQ_STATUS ADD VALUE 'Testing' AFTER 'In Progress'"]



def updateDatabase(engine, url):
  '''
  Analyse a database to determine its version; if not the most recent, update the database to the
  newest version.
  :param engine: connection database.
  '''
  if url.startswith('postgresql:'):
    updater = PostgresqlUpdated(engine)
  else:
    updater = SQLUpdater(engine)
  updater.update()

