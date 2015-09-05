"""
Created on Sep 25, 2013

@author: EHWAAL

Copyright (C) 2014 Evert van de Waal
This program is released under the conditions of the GNU General Public License.
"""

from enum import IntEnum
import sys
from decimal import Decimal

from django.db import models
from django.conf import settings
from django.db.models import Model


VERSION_NR = 17


# Determine which encoding to use when interacting with files
# The database stores unicode, and unicode is used inside the program by Python
ENCODING = 'cp1252' if 'win' in sys.platform else 'utf-8'

NAME_LENGTH = 100


class Options(IntEnum):
    @classmethod
    def items(cls):
        return [(name, int(value)) for name, value in cls.__members__.items()]
    @classmethod
    def choices(cls):
        return [(int(value), name) for name, value in cls.__members__.items()]
    @classmethod
    def keys(cls):
        return cls.__members__.keys()


class Priorities(Options):
    must   = 1
    should = 2
    could  = 3
    would  = 4


class PlaneableStates(Options):
    open = 1
    in_progress = 2
    testing = 3
    question = 4
    done = 5
    rejected = 6
    duplicate = 7

    @staticmethod
    def is_open(state):
        return state < PlaneableStates.done


class RequirementType(Options):
    functional = 1
    non_functional = 2
    comment = 3


class ChangeType(Options):
    add = 1
    delete = 2
    change = 3


def RequiredFK(*args, **kwds):
    return models.ForeignKey(*args, null=False, on_delete=models.CASCADE, **kwds)


def OptionalFK(*args, **kwds):
    return models.ForeignKey(*args, null=True, on_delete=models.SET_NULL, **kwds)


###############################################################################
# General database tables
class DbaseVersion(Model):
    version = models.IntegerField(default=VERSION_NR)

class CrossrefType(Model):
    forwardname = models.CharField(max_length=40)
    backwardname = models.CharField(max_length=40)

    DEFAULT_TYPES = [
        ('Refinement', 'Overview'),
        ('Uses', 'Used by'),
        ('Implemented by', 'Specified by'),
        ('Depends', 'Used by'),
        ('Contains', 'Realised during')]

class System(Model):
    name = models.CharField(max_length=NAME_LENGTH)
    description = models.TextField()


class Style(Model):
    name = models.CharField(max_length=NAME_LENGTH)
    details = models.TextField()


class Attachment(Model):
    name = models.CharField(max_length=NAME_LENGTH)
    data = models.BinaryField()


class Icon(Model):
    name = models.CharField(max_length=NAME_LENGTH)
    data = models.ImageField(max_length=100000)


class ChangeLog(Model):
    recordtype = models.CharField(max_length=20)
    recordid   = models.IntegerField()
    changetype = models.IntegerField(choices=ChangeType.choices())
    timestamp  = models.DateTimeField(auto_now_add=True)
    details    = models.TextField()


###############################################################################
# Planeable items
class PlaneableXRef(Model):
    """ For defining cross-references between planeable items that are outside the
        normal parent-child hierarchy.
    """
    aitem = RequiredFK('PlaneableItem', related_name='amember')
    bitem = RequiredFK('PlaneableItem', related_name='bmember')
    reftype = OptionalFK(CrossrefType)


class PlaneableItem(Model):
    abref = 'item'
    editor_title = 'Planeable Item'
    CLS_DICT = None

    name = models.CharField(max_length=NAME_LENGTH, blank=True)
    description = models.TextField(default='')

    system = RequiredFK(System)
    parent = OptionalFK("self", related_name='children')
    priority = models.IntegerField(choices=Priorities.choices(), default=int(Priorities.must))
    created = models.DateTimeField(auto_now_add=True)
    order = models.IntegerField(default=0)
    itemtype = models.CharField(max_length=6)
    # aitems: the list of items for which this item is the A item.
    # bitems: the list of items for which this item is the B item
    aitems = models.ManyToManyField("self", through=PlaneableXRef,
                                    symmetrical=False, related_name="bitems")
    attachments = models.ManyToManyField(Attachment)

    polymorphic_on = 'itemtype'

    @classmethod
    def polymorphic_identity(cls):
        return cls.abref

    @staticmethod
    def get_types():
        return [PlaneableItem.abref]+[cls.abref for cls in PlaneableItem.__subclasses__()]

    @staticmethod
    def get_cls(abref):
        if PlaneableItem.CLS_DICT is None:
            PlaneableItem.CLS_DICT = {cls.abref : cls
            for cls in PlaneableItem.__subclasses__() + [PlaneableItem]}
        if abref not in PlaneableItem.CLS_DICT:
            return None
        return PlaneableItem.CLS_DICT[abref]

    @staticmethod
    def classes():
        return [PlaneableItem] + PlaneableItem.__subclasses__()

    @classmethod
    def get_detailfields(cls):
        """
        :return: a list of the details that are editable in detail views, and the id.
        """
        fields = ['id', 'itemtype', 'system', 'parent', 'order', 'name', 'description', 'priority',
                  'created']

        return fields

    @staticmethod
    def get_default(itemtype):
        classes = {cls.abref:cls for cls in PlaneableItem.__subclasses__()}
        return classes[itemtype]()


class PlaneableStatus(Model):
    editor_title = 'State Update'

    planeable = RequiredFK(PlaneableItem)
    description = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    status = models.IntegerField(choices=PlaneableStates.choices())
    timeremaining = models.FloatField(null=True, default=None)
    timespent = models.FloatField(null=True, default=None)
    assignedto = OptionalFK(settings.AUTH_USER_MODEL)


class Action(PlaneableItem):
    abref = 'action'
    editor_title = 'Interaction'

    # The connection is optional so that actions can be created before they
    # are placed in a structure.
    connection = OptionalFK(PlaneableItem, related_name='+')
    isresponse = models.BooleanField(default=False)


class Requirement(PlaneableItem):
    abref = 'req'
    editor_title = 'Requirement'

    reqtype = models.IntegerField(choices=RequirementType.choices(),
                                  default=int(RequirementType.functional))
    stakeholder = models.CharField(max_length=NAME_LENGTH, blank=True)

    @classmethod
    def get_detailfields(cls):
        """
        :return: a list of the details that are editable in detail views, and the id.
        """
        return PlaneableItem.get_detailfields() + ['reqtype']


class StructuralItem(PlaneableItem):
    abref = 'struct'
    editor_title = 'Structural Item'


class Connection(PlaneableItem):
    abref = 'con'
    editor_title = 'Connection'

    start = RequiredFK(PlaneableItem, related_name='+')
    end   = RequiredFK(PlaneableItem, related_name='+')

    @classmethod
    def get_detailfields(cls):
        return PlaneableItem.get_detailfields() + ['start', 'end']


class Bug(PlaneableItem):
    abref = 'bug'
    editor_title = 'Bug'

    reportedby = OptionalFK(settings.AUTH_USER_MODEL)

    @classmethod
    def get_detailfields(cls):
        """
        :return: a list of the details that are editable in detail views, and the id.
        """
        return PlaneableItem.get_detailfields() + ['reportedby']


class View(PlaneableItem):
    abref = 'view'
    editor_title = 'View'

    style = OptionalFK(Style)


class Project(PlaneableItem):
    abref = 'proj'
    editor_title = 'Project'

    start = models.DateField()
    finish = models.DateField()
    budget = models.DecimalField(max_digits=12, decimal_places=2, default='0.00')

    @classmethod
    def get_detailfields(cls):
        """
        :return: a list of the details that are editable in detail views, and the id.
        """
        return PlaneableItem.get_detailfields() + ['start', 'finish', 'budget']


###############################################################################
# Graphical Representation
class Anchor(Model):
    _abref = 'anchor'
    view = RequiredFK(View)
    style_role = models.CharField(max_length=NAME_LENGTH)
    order = models.IntegerField(default=0)
    anchortype = models.CharField(max_length=6, default='anchor')

    polymorphic_on = 'anchortype'

    @classmethod
    def polymorphic_identity(cls):
        return cls._abref

    @staticmethod
    def get_types():
        return [cls.polymorphic_identity() for cls in Anchor.__subclasses__()]

    @staticmethod
    def get_cls(abref):
        if Anchor.CLS_DICT is None:
            Anchor.CLS_DICT = {cls.polymorphic_identity() : cls
            for cls in Anchor.__subclasses__()}
        if abref not in Anchor.CLS_DICT:
            return None
        return Anchor.CLS_DICT[abref]

    @staticmethod
    def classes():
        return Anchor.__subclasses__()


    @staticmethod
    def get_default(itemtype):
        return Anchor.classes[itemtype]()

    @classmethod
    def get_detailfields(cls):
        """
        :return: a list of the details that are editable in detail views, and the id.
        """
        return ['id', 'view', 'style_role', 'order', 'anchortype']


class BlockRepresentation(Anchor):
    _abref = 'block'
    planeable = OptionalFK(PlaneableItem)
    x = models.FloatField(default=0)
    y = models.FloatField(default=0)
    height = models.FloatField(default=50)
    width = models.FloatField(default=100)
    ismultiple = models.BooleanField(default=False)
    icon  = OptionalFK(Icon)

    @classmethod
    def get_detailfields(cls):
        """
        :return: a list of the details that are editable in detail views, and the id.
        """
        return Anchor.get_detailfields() + ['planeable', 'x', 'y', 'height', 'width',
                                            'ismultiple', 'icon']

    def get_name(self):
        return self.planeable.name


class ConnectionRepresentation(Anchor):
    _abref = 'line'
    connection = OptionalFK(PlaneableItem, related_name='+')
    start = OptionalFK(PlaneableItem, related_name='+')
    end = OptionalFK(PlaneableItem, related_name='+')

    @classmethod
    def get_detailfields(cls):
        """
        :return: a list of the details that are editable in detail views, and the id.
        """
        return Anchor.get_detailfields() + ['connection', 'start', 'end']

    def get_name(self):
        return self.connection.name


class ActionRepresentation(Anchor):
    _abref = 'action'
    action = OptionalFK(PlaneableItem)  # Optional to allow empty objects to be created
    anchorpoint = OptionalFK(Anchor, related_name='+')
    xoffset = models.FloatField(default=0)
    yoffset = models.FloatField(default=0)

    @classmethod
    def get_detailfields(cls):
        """
        :return: a list of the details that are editable in detail views, and the id.
        """
        return Anchor.get_detailfields() + ['action', 'anchorpoint', 'xoffset', 'yoffset']

    def get_name(self):
        return self.action.name


class Annotation(Anchor):
    _abref = 'note'
    anchorpoint = OptionalFK(Anchor, related_name='+')
    x = models.FloatField(default=0)
    y = models.FloatField(default=0)
    height = models.FloatField(default=50)
    width = models.FloatField(default=100)
    description = models.TextField(default='')
    attachments = models.ManyToManyField(Attachment)

    @classmethod
    def get_detailfields(cls):
        """
        :return: a list of the details that are editable in detail views, and the id.
        """
        # TODO: Implement support for attachements
        return Anchor.get_detailfields() + ['anchorpoint', 'x', 'y', 'height', 'width',
                                            'description']


###############################################################################
# Keeping track of time spent on a project
class PlannedEffort(Model):
    worker = RequiredFK(settings.AUTH_USER_MODEL)
    project = RequiredFK(Project)
    week    = models.DateField()
    hours   = models.FloatField()
    isactual = models.BooleanField(default=False)
