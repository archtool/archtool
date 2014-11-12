'''
Update a database to be opened to the most recent version.
'''

from model import VERSION, sessionmaker, sessionScope

__author__ = 'ehwaal'


class SQLUpdater(object):
  ''' Updater for generic SQL databases.

      Can be subclassed in case specific updates are problematic for spefic RDMSes.

      Mainly raw SQL is used, because the database may not be compatible with the current model.
  '''
  def __init__(self, engine):
    self.engine = engine
    self.handlers = {6:self.update6to7,
                     7:self.update7to8}
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

    # TODO: Delete the old database versions.
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


def updateDatabase(engine):
  '''
  Analyse a database to determine its version; if not the most recent, update the database to the
  newest version.
  :param engine: connection database.
  '''
  updater = SQLUpdater(engine)
  updater.update()

