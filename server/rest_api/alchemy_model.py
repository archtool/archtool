""" Imports the Django model and exposes it as a SQLalchemy model ORM model.

Django's model offers a very compact syntax, ease of migration, integration
with Django settings, validation, generation of forms etc.
However, it lacks the expressive power of SQLalchemy when defining complex queries.
Thus this bridge is useful.

The approach is NOT to use SQLalchemy's introspection but to convert the
Django model into an equivalent SQLalchemy ORM model.

Copyright (C) 2015 Evert van de Waal
This program is released under the conditions of the GNU General Public License.
"""
__author__ = 'ehwaal'


if __name__ == '__main__':
    import os
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.settings")
    import django
    django.setup()


from enum import IntEnum
import sys
from decimal import Decimal

from sqlalchemy.ext.declarative import declarative_base, declared_attr
import sqlalchemy as sa
# Column, Integer, String, Float, Text, Boolean, DateTime, Enum, LargeBinary
from sqlalchemy import ForeignKey, create_engine, Table, UniqueConstraint
from sqlalchemy.orm import relationship, backref, sessionmaker

from django.conf import settings
import django.db.models

from rest_api.models import PlaneableItem

Base = declarative_base()

bridge = {}

type_conversion = {'OneToOneField':sa.Integer,
                   'CharField':sa.String,
                   'TextField':sa.Text,
                   'ForeignKey':None, #sa.ForeignKey,
                   'IntegerField':sa.Integer,
                   'DateTimeField':sa.DateTime,
                   'AutoField':None}

def field_factory(field):
    t = type_conversion[field.__class__.__name__]
    if t:
        kwargs = {'primary_key':field.primary_key}
        if t == sa.String:
            t = t(field.max_length)
        return sa.Column(t, **kwargs)

def table_factory(model):
    attrs = {'__tablename__': model._meta.db_table}

    for field in model._meta.concrete_fields:
        attrs[field.column] = field_factory(field)

    return type(model.__name__, (Base,), attrs)

bridge[PlaneableItem] = table_factory(PlaneableItem)
pass