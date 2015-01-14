'''
This file contains a set of commands for modifying the 'model'. The commands
are given to the controller for execution.
'''

__author__ = 'ehwaal'


import model
import sqlalchemy as sql
import os.path


BLOCK_WIDTH  = 100
BLOCK_HEIGHT = 30



class AddNewAction(object):
  def __init__(self, details, text):
    self.details = details
    self.text = text
  def do(self, ctrl):
    # Determine if adding an action to a block or to a connection.
    if isinstance(self.details, model.ConnectionRepresentation):
      if ctrl.fp_as_call:
        fp = model.FunctionPoint(Name=self.text, Block=self.details.theEnd.Block, Parent=None)
      else:
        fp = model.FunctionPoint(Name=self.text, Connection=self.details.Connection, Parent=None)
    else:
      fp = model.FunctionPoint(Name=self.text, Block=self.details.Block, Parent=None)
    ctrl.session.add(fp)
    ctrl.session.commit()
    return fp


class AddExistingAction(object):
  def __init__(self, view_details, fp_id, anchor_id):
    self.details = view_details
    self.fp_id = fp_id
    self.anchor_id = anchor_id
  def do(self, ctrl):
    '''
    :param ctrl:
    :return: A tuple with the new fprepresentation, and the linked functionpoint.
    '''
    # Create a query to obtain 1). The original FunctionPoint, 2). The number of anchors in the
    # current View, and 3). The number of function points in the current view.
    q = ctrl.session.query
    sq1 = q(model.Anchor.View, sql.func.count('*').label('z_order')).\
           filter_by(View=self.details.Id).\
           group_by(model.Anchor.View).subquery()
    sq2 = q(model.Anchor.View, sql.func.count('*').label('seq_nr')).\
           filter_by(View=self.details.Id).\
           filter_by(AnchorType=model.FpRepresentation.__tablename__).\
           group_by(model.Anchor.View).subquery()
    result = ctrl.session.query(model.FunctionPoint, sq1.c.z_order, sq2.c.seq_nr).\
                          filter(sq1.c.View==self.details.Id).\
                          filter(sq2.c.View==self.details.Id).\
                          filter(model.FunctionPoint.Id==self.fp_id)

    # Execute the query and get 1 result.
    result = result.first()
    # TODO: Check this!
    if result is None:
      result = [ctrl.session.query(model.FunctionPoint).filter(model.FunctionPoint.Id==self.fp_id).one(),
                1, 1]
    # Create the new action in the view, and commit it.
    fp2uc = model.FpRepresentation(FunctionPoint=self.fp_id, View=self.details.Id, Order=result[1],
                                   AnchorPoint=self.anchor_id, SequenceNr=result[2])
    ctrl.session.add(fp2uc)
    ctrl.session.commit()
    return fp2uc, result[0]

class AddBlockRepresentation(object):
  def __init__(self, block_details, view_id, coods, order):
    self.details = block_details
    self.coods = coods
    self.order = order
    self.view_id = view_id
  def do(self, ctrl):
    new_details = None
    with model.sessionScope(ctrl.session):
      if isinstance(self.details, model.ArchitectureBlock):
        new_details = model.BlockRepresentation(Block=self.details.Id,
                                                View = self.view_id,
                                                x = self.coods.x(),
                                                y = self.coods.y(),
                                                height = BLOCK_HEIGHT,
                                                width = BLOCK_WIDTH,
                                                Order = self.order)
        ctrl.session.add(new_details)
      elif isinstance(self.details, model.View):
        new_details = model.UsecaseRepresentation(Parent=self.details.Id,
                                                View = self.view_id,
                                                x = self.coods.x(),
                                                y = self.coods.y(),
                                                height = BLOCK_HEIGHT,
                                                width = BLOCK_WIDTH,
                                                Order = self.order)
        ctrl.session.add(new_details)
    return new_details


class AddNewBlock(object):
  def __init__(self, name, parent, is_usecase):
    self.name = name
    self.parent = parent.Id if parent else None
    self.is_usecase = is_usecase
  def do(self, ctrl):
    if self.is_usecase:
      block_details = model.View(Name=self.name, Parent=self.parent)
    else:
      block_details = model.ArchitectureBlock(Name=self.name, Parent=self.parent)
    ctrl.session.add(block_details)
    ctrl.session.commit()
    return block_details



class AddConnectionRepresentation(object):
  def __init__(self, start, end, view):
    self.start = start
    self.end = end
    self.view = view
  def do(self, ctrl):
    source = self.start
    target = self.end
    # Find the connection object, or create it if it does not yet exist.
    # This connection is between Architecture Blocks, not their representations.
    with model.sessionScope(ctrl.session) as session:
      bc = model.BlockConnection
      conns = session.query(bc).\
                           filter(bc.Start.in_([source.Block, target.Block])).\
                           filter(bc.End.in_([source.Block, target.Block])).all()
      if conns:
        connection = conns[0]
      else:
        connection = model.BlockConnection(Start=source.Block, End=target.Block)
        session.add(connection)
        # We need a valid primary key, so flush the session but do not commit.
        session.flush()
      # Add the representation of the connection, between two representations of blocks.
      details = model.ConnectionRepresentation(Connection=connection.Id,
                                               theStart=source,
                                               theEnd=target,
                                               View=self.view)

      session.add(details)
      # Flush the database so that all references are updated.
      session.flush()
    return details


class AddAnnotation(object):
  def __init__(self, view_id, pos, anchor_id, order):
    self.view_id = view_id
    self.pos = pos
    self.anchor_id = anchor_id
    self.order = order
  def do(self, ctrl):
    x, y = self.pos.x(), self.pos.y()

    with model.sessionScope(ctrl.session) as session:
      details = model.Annotation(View=self.view_id,
                                  x=x, y=y,
                                  AnchorPoint=self.anchor_id,
                                  Order = self.order,
                                  width=BLOCK_WIDTH, height=BLOCK_HEIGHT)
      session.add(details)
    return details


class AddIcon(object):
  def __init__(self, fname):
    self.fname = fname

  def do(self, ctrl):
    with file(self.fname, 'rb') as f:
      data = f.read()
    with model.sessionScope(ctrl.session) as session:
      icon_name = os.path.split(self.fname)[-1]
      details = model.Icon(Name = icon_name, Data = data, Length = len(data))
      session.add(details)
    return details
