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
from django.contrib import admin
import django.db.models


VERSION_NR = 16


# Determine which encoding to use when interacting with files
# The database stores unicode, and unicode is used inside the program by Python
ENCODING = 'cp1252' if 'win' in sys.platform else 'utf-8'

NAME_LENGTH = 100

class Options(IntEnum):
    @classmethod
    def items(cls):
        return [(name, int(value)) for name, value in cls.__members__.items()]


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


class Model(django.db.models.Model):
    pass


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


class User(Model):
    name = models.CharField(max_length=NAME_LENGTH)
    email = models.EmailField()
    hourrate = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0.00'))


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
    changetype = models.IntegerField(choices=ChangeType.items())
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
    abref = ''

    name = models.CharField(max_length=NAME_LENGTH)
    description = models.TextField()

    system = RequiredFK(System)
    parent = OptionalFK("self", related_name='children')
    priority = models.IntegerField(choices=Priorities.items(), default=int(Priorities.must))
    created = models.DateTimeField(auto_now_add=True)
    order = models.IntegerField(default=0)
    itemtype = models.CharField(max_length=6)
    # aitems: the list of items for which this item is the A item.
    # bitems: the list of items for which this item is the B item
    aitems = models.ManyToManyField("self", through=PlaneableXRef,
                                    symmetrical=False, related_name="bitems")
    attachments = models.ManyToManyField(Attachment)


class PlaneableStatus(Model):
    planeable = RequiredFK(PlaneableItem)
    description = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    status = models.IntegerField(choices=PlaneableStates.items())
    timeremaining = models.FloatField()
    timespent = models.FloatField()
    assignedto = OptionalFK(User)


class Action(PlaneableItem):
    abref = 'action'

    connection = OptionalFK(PlaneableItem, related_name='+')
    isresponse = models.BooleanField(default=False)


class Requirement(PlaneableItem):
    abref = 'req'

    reqtype = models.IntegerField(choices=RequirementType.items(),
                                  default=int(RequirementType.functional))


class Connection(PlaneableItem):
    abref = 'con'

    start = RequiredFK(PlaneableItem, related_name='+')
    end   = RequiredFK(PlaneableItem, related_name='+')


class Bug(PlaneableItem):
    abref = 'bug'

    reportedby = models.ForeignKey(User)


class View(PlaneableItem):
    abref = 'view'

    style = OptionalFK(Style)


class Project(PlaneableItem):
    abref = 'proj'
    start = models.DateField()
    finish = models.DateField()
    budget = models.DecimalField(max_digits=12, decimal_places=2)


###############################################################################
# Graphical Representation
class Anchor(Model):
    view = RequiredFK(View)
    style_role = models.CharField(max_length=NAME_LENGTH)
    order = models.IntegerField(default=0)


class BlockRepresentation(Anchor):
    planeable = RequiredFK(PlaneableItem)
    x = models.FloatField()
    y = models.FloatField()
    height = models.FloatField()
    width = models.FloatField()
    ismultiple = models.BooleanField()
    icon  = OptionalFK(Icon)


class ConnectionRepresentation(Anchor):
    connection = RequiredFK(PlaneableItem, related_name='+')
    start = RequiredFK(PlaneableItem, related_name='+')
    end = RequiredFK(PlaneableItem, related_name='+')


class ActionRepresentation(Anchor):
    action = RequiredFK(PlaneableItem)
    anchorpoint = OptionalFK(Anchor, related_name='+')
    xoffset = models.FloatField()
    yoffset = models.FloatField()


class Annotation(Anchor):
    anchorpoint = OptionalFK(Anchor, related_name='+')
    x = models.FloatField()
    y = models.FloatField()
    height = models.FloatField()
    width = models.FloatField()
    description = models.TextField()
    attachments = models.ManyToManyField(Attachment)


###############################################################################
# Keeping track of time spent on a project
class PlannedEffort(Model):
    worker = RequiredFK(User)
    project = RequiredFK(Project)
    week    = models.DateField()
    hours   = models.FloatField()
    isactual = models.BooleanField(default=False)
