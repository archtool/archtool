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


def export(fname='dump.csv', engine=None):
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
    data = [[d.encode('cp1252') if isinstance(d, unicode) else d for d in row] for row in data]
    writer.writerows(data)
    writer.writerow([])

def importCsv(fname='dump.csv', db=None):
  table_renames = {'fptousecase': 'fptoview'}
  tables = {tab.__tablename__:tab for tab in model.Base.getTables()}
  # Switch off the foreign keys for now
  model.check_fkeys = False
  engine = model.create_engine(db)
  model.changeEngine(engine)
  # Clean the database
  model.cleanDatabase()
  try:
    session = model.SessionFactory()
    f = file(fname, 'r')
    reader = csv.reader(f)
    table = None
    fields = None
    planeable_items = {}
    planeable_types = []
    is_planeable = False
    for row in reader:
      if len(row) == 1:
        # If the previous table was the planeableitems, do some processing
        if table == model.PlaneableItem:
          for r in planeable_items.values():  
            if not r['ItemType'] in planeable_types:
              planeable_types.append(r['ItemType'])
        # Start of a new table.
        name = table_renames.get(row[0], row[0])
        if name not in tables:
          table = model.Base.metadata.tables[name]
        else:
          table = tables[name]
        fields = None
        is_planeable = name in planeable_types
        # Commit the records for the previous table.
        session.commit()
        
      elif len(row) > 1:
        if fields is None:
          # The first line of a table contains the names of the columns (fields).
          fields = row
          exclude = [f for f in fields if not hasattr(table, f)]
        else:
          # Replace empty string data elements with None: '' is not a valid value for an integer
          row = [r.decode('cp1252') if r!='' else None for r in row]
          # Instantiate an ORM object that can be inserted into the database.
          d = dict(zip(fields, row))
          # Exclude fields that have been removed from the database.
          if exclude:
            for e in exclude:
              del d[e]
          if is_planeable:
            d.update(planeable_items[d['Id']])
          if table is model.PlaneableItem:
            planeable_items[d['Id']] = d
          elif name not in tables:
            # This class needs raw SQL to create.
            ins = table.insert().values(**d)
            print ins
            session.execute(ins)
          else:
            el = table(**d)
            print el
            session.add(el)
    session.commit()
    
    # Delete all Dbase Versions and add the current one.
    session.query(model.DbaseVersion).delete()
    session.commit()
    session.add(model.DbaseVersion())
    session.commit()
  finally:
    model.the_engine = None
    model.SessionFactory = None
    model.check_fkeys = True



def upgradeDatabase(url):
  ''' Upgrade the current database to the newest database structure. '''
  fname = model.fnameFromUrl(url)
  if not fname:
    raise RuntimeError('Only SQLITE database supported for upgrade')
  # Close the engine
  model.clearEngine()
  # Export the current database
  export(engine = model.create_engine(url))
  # Create the new (upgraded) database and import the data
  importCsv(db=url+'.new')
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
  
