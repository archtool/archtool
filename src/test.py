'''
Created on Oct 25, 2013

@author: EHWAAL
'''
import unittest
import model

from sqlalchemy.orm.exc import ObjectDeletedError
from sqlalchemy import event
from sqlalchemy.engine import Engine


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


class Test(unittest.TestCase):

  def setUp(self):
    # Do the tests on a temporary database
    self.org_engine = model.engine
    self.engine = model.create_engine('sqlite:///:memory:', echo=True)
    model.changeEngine(self.engine)

  def tearDown(self):
    # Restore the database
    model.changeEngine(self.org_engine, create=False)
    
  def testModel(self):
    session = model.SessionFactory()
    # Test the database is empty
    assert session.query(model.ArchitectureBlock.Id).count() == 0
    
    # Add some architecture blocks and a View
    with model.sessionScope(session) as s:
      s.add(model.ArchitectureBlock(Name='blok1'))
      s.add(model.ArchitectureBlock(Name='blok2'))
      s.add(model.View(Name='view1'))
    # Add a connection
    with model.sessionScope(session) as s:
      s.add(model.Connection(Start=1, End=2))
    # Add function points
    with model.sessionScope(session) as s:
      s.add(model.FunctionPoint(Connection=1, Name='fp1'))
      s.add(model.FunctionPoint(Block=1, Name='fp2'))
    # Add elements to the view
    with model.sessionScope(session) as s:
      s.add(model.BlockRepresentation(Block=1, View=1))
      s.add(model.BlockRepresentation(Block=1, View=1))
      s.add(model.BlockRepresentation(Block=2, View=1))
      s.add(model.FpToUseCase(UseCase=1, FunctionPoint=1))
      s.add(model.FpToUseCase(UseCase=1, FunctionPoint=2))
        
    assert session.query(model.FpToUseCase.Id).count() == 2
    assert session.query(model.BlockRepresentation.Id).count() == 3
    
    block1 = session.query(model.ArchitectureBlock).get(1)
    assert len(block1.Representations) == 2
    
    # Delete Block two; check everything is deleted correctly
    with model.sessionScope(session) as s:
      s.query(model.ArchitectureBlock).filter(model.ArchitectureBlock.Id==2).delete()
    assert session.query(model.ArchitectureBlock.Id).count() == 1
    self.assertEqual(session.query(model.BlockRepresentation.Id).count(), 2)
    self.assertEqual(session.query(model.Connection.Id).count(), 0)
    self.assertEqual(session.query(model.FpToUseCase.Id).count(), 1)
    
    # Delete the View
    fp2uc = session.query(model.FpToUseCase).get(2)
    with model.sessionScope(session) as s:
      s.query(model.View).filter(model.View.Id==1).delete()
    self.assertEqual(session.query(model.BlockRepresentation.Id).count(), 0)
    self.assertEqual(session.query(model.FpToUseCase.Id).count(), 0)
    
    # Check that accessing ORM objects that have been deleted raises errors.
    try:
      print 'DELETED FP2UC', fp2uc
      self.fail('Should have raised an exception')
    except ObjectDeletedError:
      pass

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testModel']
    unittest.main()