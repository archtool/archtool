'''
Created on Oct 27, 2013

@author: EHWAAL

Copyright (C) 2014 Evert van de Waal
This program is released under the conditions of the GNU General Public License.
'''

from sqlalchemy import Table, MetaData, Column, ForeignKey, Integer, String
import model
import csv
from sqlalchemy.ext.declarative import declarative_base
import shutil
import os
import traceback


def loadCsv(fname='dump.csv'):
  ''' Import a CSV file, creating a dictionary of tables.
      Inside the tables, each record is a dictionary. 
      If the records have an 'Id' field, they are stored in a dictionary
      else in a list.
  '''
  f = file(fname, 'r')
  reader = csv.reader(f)
  tables = {}
  table = None
  fields = None
  name = None
  for row in reader:
    if len(row) == 1:
      # Start of a new table.
      name = row[0]
      fields = None
      
    elif len(row) > 1:
      if not name:
        # This table is skipped.
        continue
      if fields is None:
        # The first line of a table contains the names of the columns (fields).
        fields = row
        table = tables[name] = []
      else:
        # Replace empty string data elements with None: '' is not a valid value for an integer
        row = [r.decode(model.ENCODING) if r!='' else None for r in row]
        # Instantiate an ORM object that can be inserted into the database.
        d = dict(zip(fields, row))
        table.append(d)
          
  return tables
  



def export(fname, engine):
  meta = MetaData()
  meta.reflect(bind=engine)
  f = file(fname, 'w')
  writer = csv.writer(f)
  # Ensure the planeableitem table is written FIRST.
  tables = meta.tables.values()
  if 'planeableitem' in meta.tables:
    tables.remove(meta.tables['planeableitem'])
    tables.insert(0, meta.tables['planeableitem'])
  # Ensure the PlannedEfforts are written LAST (after the Projects)
  tables.remove(meta.tables['plannedeffort'])
  tables.append(meta.tables['plannedeffort'])
  
  for table in tables:
    writer.writerow([table.fullname])
    writer.writerow(table.columns.keys())
    fields = ','.join(['"%s"'%f for f in table.columns.keys()])
    data = engine.execute('select %s from %s'%(fields, table.fullname))
    data = [[d.encode(model.ENCODING) if isinstance(d, unicode) else d for d in row] for row in data]
    writer.writerows(data)
    writer.writerow([])



def upgradeToVersion6(data):
  ''' Conversion function that prepares data to be loaded in a version 6+ database.
      
      The big difference is that before 6, there was no Anchor class that representation
      inherited from. Also, there were no ConnectionRepresentation's.
  '''
  # Renumber the Anchor children (and create conversion tables)
  index = 1
  for name in ['blockrepresentation', 'fptoview', 'annotation']:
    if not name in data:
      continue
    table = data[name]
    for record in table:
      id = record['Id']
      record['Id'] = index
      record['AnchorType'] = name if name != 'fptoview' else 'fprepresentation'
      index += 1
  
  # Add ConnectionRepresentation's
  con2repr = {}
  data['connectionrepresentation'] = reprs = []
  # Make some indexes for blocks, blockreprs & views
  blockreprs = {(r['Block'], r['View']):r['Id'] for r in data['blockrepresentation']}
  pairs = blockreprs.keys()
  blocks = set([p[0] for p in pairs])
  blockviews = {b:[v for b1,v in pairs if b1==b] for b in blocks}
  for connection in data['connection']:
    start = connection['Start']
    end = connection['End']
    start_views = blockviews.get(start, [])
    end_views = blockviews.get(end, [])
    for view in set(start_views).intersection(set(end_views)):
      repr = dict(Id=index,
                  Connection=connection['Id'],
                  Start=blockreprs[(start, view)],
                  End=blockreprs[(end, view)],
                  View=view,
                  AnchorType='connectionrepresentation')
      index += 1
      reprs.append(repr)
      con2repr[(connection['Id'], view)] = repr['Id']

  # Let FpToView's point to ConnectionRepresentations or BlockRepresentations
  # Databases do have some advantages...
  block2repr = {(r['Block'], r['View']):r['Id'] for r in data['blockrepresentation']}
  fp2con = {fp['Id']:fp['Connection'] for fp in data['functionpoint']}
  fp2block = {fp['Id']:fp['Block'] for fp in data['functionpoint']}
  to_remove = []
  for fp2view in data['fptoview']:
    fp = fp2view['FunctionPoint']
    con = fp2con[fp]
    block = fp2block[fp]
    if not(con or block):
      print 'Skipping %s because no anchor was found'%fp2view
      to_remove.append(fp2view)
    if con:
      fp2view['AnchorPoint'] = con2repr[(con, fp2view['View'])]
    if block:
      fp2view['AnchorPoint'] = block2repr[(block, fp2view['View'])]
  data['fptoview'] = [r for r in data['fptoview'] if r not in to_remove]




def importData(data, db):
  table_renames = {'fptousecase': 'fprepresentation',
                   'fptoview':'fprepresentation',
                   'connection':'blockconnection'}
  table_ignore = ['colorpalette', 'dbaseversion']
  tables = {tab.__tablename__:tab for tab in model.Base.getTables()}
  # Switch off the foreign keys for now
  model.check_fkeys = False
  engine = model.create_engine(db, echo=True)
  model.changeEngine(engine)
  # Clean the database
  model.cleanDatabase()
  try:
    session = model.SessionFactory()
    with model.sessionScope(session) as session:
      # In PostgreSQL, ensure the foreign keys are only checked at the commit, not before.
      if db.startswith('postgresql'):
        session.execute('SET CONSTRAINTS ALL DEFERRED')

      v = int(data['dbaseversion'][0]['Version'])
      if v < 6:
        upgradeToVersion6(data)
      del data['dbaseversion']    # Remove the old database version number
      # Add the current database version
      session.add(model.DbaseVersion())

      # Treat the planeable and anchor items differently: these are polymorphic tables.
      # The base tables are not added directly but through their child tables, using the ORM
      poly_items = {}  # Store the contents held by the polymorphic tables. These are needed later..
      poly_bases = {}  # Find the base for a specific table.
      for poly_table, poly_column in [('planeableitem', 'ItemType'), ('anchor', 'AnchorType')]:
        poly_items[poly_table] = {r['Id']:r for r in data[poly_table]}
        children = set([r[poly_column] for r in data[poly_table]])
        for c in children:
          poly_bases[c] = poly_table
        # Do not add the table directly, so remove it from the list.
        del data[poly_table]

      for n1, n2 in table_renames.items():
        if n1 in data:
          data[n2] = data[n1]

      for table, name in [(t, t.__tablename__) for t in model.order] + \
                  [(model.Base.metadata.tables['planeablexref'], 'planeablexref')]:
        records = data.get(name, [])
        if not records:
          continue
        # Start of a new table.
        if name in table_ignore:
          # Skip this table.
          continue
        if name not in tables:
          table = [name]
        else:
          table = tables[name]
        base_class = poly_bases.get(name, None)

        # Determine which fields are no longer used
        fields = records[0].keys()
        exclude = [f for f in fields if not hasattr(table, f)]
        for d in records:
          print 'Table:', name, 'data:', d
          # Exclude fields that have been removed from the database.
          if exclude:
            for e in exclude:
              del d[e]
          if base_class:
            # Add in the data stored in the polymorphic base table
            d.update(poly_items[base_class][d['Id']])

          # Add the record to the database
          if name not in tables:
            # This class needs raw SQL to create.
            if d:
              ins = table.insert().values(**d)
              session.execute(ins)
          else:
            el = table(**d)
            session.add(el)

    
  finally:
    model.the_engine = None
    model.SessionFactory = None
    model.check_fkeys = True


def upgradeDatabase(url):
  ''' Upgrade the current database to the newest database structure. '''
  fname = model.fnameFromUrl(url)
  print 'Converting', fname

  # Close the engine
  model.clearEngine()
  # Export the current database
  engine = model.create_engine(url)
  export(engine = engine)
  # Create the new (upgraded) database and import the data
  data = loadCsv()
  importData(data, url+'.new')
  # Move the existing file to a backup location
  shutil.move(fname, fname+'.bak')
  # Get the new database to the existing location
  shutil.move(fname+'.new', fname)






if __name__ == '__main__':
  import os.path
  import shutil
  from glob import glob
  
  fnames = glob('*.db')
  print 'Found files:', fnames
  for fname in fnames:
    print 'Converting', fname
    fbase, ext = os.path.splitext(fname)
    fold = '%s.old'%fbase
    fnew = '%s.new'%fbase
    engine = model.create_engine('sqlite:///archmodel.db')
    export('%s.csv'%fbase, engine)
    importCsv('%s.csv'%fbase, 'sqlite:///%s'%fnew)
    shutil.move(fname, fold)
    shutil.move(fnew, fname)
  
