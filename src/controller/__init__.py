__author__ = 'ehwaal'


import model
from controller.history_logger import HistoryLogger



class Controller(object):
  theController = None

  def __init__(self):
    self.fp_as_call = False   # Used as global variable.
    self.session = None
    self.history_logger = None

  def setFpAsCall(self, b):
    self.fp_as_call = b

  def getExistingActions(self, anchor_details):
    if isinstance(anchor_details, model.ConnectionRepresentation):
      if self.fp_as_call:
        # If the anchor is a connection, get the actions for its end.
        return anchor_details.theEnd.theDetails.FunctionPoints
      return anchor_details.theDetails.FunctionPoints

    if isinstance(anchor_details, model.BlockRepresentation):
      return anchor_details.theDetails.FunctionPoints
    return []

  def getViewElements(self, view_details):
    q = self.session.query(model.BlockRepresentation).order_by(model.BlockRepresentation.Order)
    blocks = q.filter(model.BlockRepresentation.View == view_details.Id).all()

    q = self.session.query(model.Annotation).order_by(model.Annotation.Order)
    annotations = q.filter(model.Annotation.View == view_details.Id).all()

    q = self.session.query(model.ConnectionRepresentation).\
      filter(model.ConnectionRepresentation.View==view_details.Id)
    connections = q.all()

    # self.fp_details is sorted by 'order'.
    actions = self.session.query(model.FpRepresentation, model.FunctionPoint).\
                     filter(model.FpRepresentation.View==view_details.Id).\
                     filter(model.FunctionPoint.Id == model.FpRepresentation.FunctionPoint).\
                     order_by(model.FpRepresentation.Order.asc()).all()

    usecases = self.session.query(model.UsecaseRepresentation).\
                     filter(model.UsecaseRepresentation.View == view_details.Id).all()

    return blocks, annotations, connections, actions, usecases


  def getIconNames(self):
    Icon = model.Icon
    return [r[0] for r in self.session.query(Icon.Name).order_by(Icon.Name)]


  def execute(self, cmnd):
    return cmnd.do(self)


  @staticmethod
  def get():
    if Controller.theController is None:
      Controller.theController = Controller()
    return Controller.theController

  @staticmethod
  def setSession(session):
    ctrl = Controller.get()
    ctrl.session = session
    ctrl.history_logger = HistoryLogger(session, model.ChangeLog)