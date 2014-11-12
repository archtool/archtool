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
    self.org_engine = model.the_engine
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
      b1 = model.ArchitectureBlock(Name='blok1')
      b2 = model.ArchitectureBlock(Name='blok2')
      v1 = model.View(Name='view1')
      # Add a connection
      c1 = model.BlockConnection(theStart=b1, theEnd=b2)

      # Add function points
      fp1 = model.FunctionPoint(theConnection=c1, Name='fp1')
      fp2 = model.FunctionPoint(theBlock=b1, Name='fp2')

      # Add elements to the view
      br1 = model.BlockRepresentation(theBlock=b1, theView=v1)
      s.add(model.BlockRepresentation(theBlock=b1, theView=v1))
      br2 = model.BlockRepresentation(theBlock=b2, theView=v1)
      fpr1 = model.FpRepresentation(theView=v1, theFp=fp1, theAnchor=br1)
      fpr2 = model.FpRepresentation(theView=v1, theFp=fp2, theAnchor=br2)
      s.add(fpr1)
      s.add(fpr2)


    assert session.query(model.FpRepresentation.Id).count() == 2
    assert session.query(model.BlockRepresentation.Id).count() == 3
    
    block1 = session.query(model.ArchitectureBlock).get(b1.Id)
    assert len(block1.Representations) == 2
    
    # Delete Block two; check everything is deleted correctly
    with model.sessionScope(session) as s:
      s.query(model.ArchitectureBlock).filter(model.ArchitectureBlock.Id==b2.Id).delete()
    assert session.query(model.ArchitectureBlock.Id).count() == 1
    self.assertEqual(session.query(model.BlockRepresentation.Id).count(), 2)
    self.assertEqual(session.query(model.BlockConnection.Id).count(), 0)
    self.assertEqual(session.query(model.FpRepresentation.Id).count(), 1)
    
    # Delete the View
    fp2uc = session.query(model.FpRepresentation).get(fpr2.Id)
    with model.sessionScope(session) as s:
      s.query(model.View).filter(model.View.Id==1).delete()
    self.assertEqual(session.query(model.BlockRepresentation.Id).count(), 0)
    self.assertEqual(session.query(model.FpRepresentation.Id).count(), 0)
    
    # Check that accessing ORM objects that have been deleted raises errors.
    try:
      print 'DELETED FP2UC', fp2uc
      self.fail('Should have raised an exception')
    except ObjectDeletedError:
      pass

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testModel']
    unittest.main()