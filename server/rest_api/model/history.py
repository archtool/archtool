"""Versioned mixin class and other utilities.
"""

from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import mapper
from sqlalchemy import Table, Column, ForeignKeyConstraint, Integer, DateTime, MetaData
import datetime


class Versioned(object):
    __is_versioned__ = True


def versioned_objects(iter):
    for obj in iter:
        if hasattr(obj, '__is_versioned__'):
            yield obj
