""" Imports the Django model and exposes it as a SQLalchemy model ORM model.

Django's model offers a very compact syntax, ease of migration, integration
with Django settings, validation, generation of forms etc.
However, it lacks the expressive power of SQLalchemy when defining complex queries.
Thus this bridge is useful.

The approach is NOT to use SQLalchemy's introspection but to convert the
Django model into an equivalent SQLalchemy ORM model. That way all backrelations
and other nifty details in the model are preserved and can be used in SQLAlchemy
just as in the Django model.

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
from inspect import isclass

from sqlalchemy.ext.declarative import declarative_base, declared_attr
import sqlalchemy as sa
# Column, Integer, String, Float, Text, Boolean, DateTime, Enum, LargeBinary
from sqlalchemy import ForeignKey, create_engine, Table, UniqueConstraint
from sqlalchemy.orm import relationship, backref, sessionmaker

from django.conf import settings
import django.db.models

import rest_api.models as models

Base = declarative_base()

def toDict(self):
    return {c.name: getattr(self, c.name) for c in self.__table__.columns}
Base.toDict = toDict

bridge = {}

def find_tables(m):
    """
    Find database tables defined in the global namespace of a module.
    :param m: The module to analyse
    :return: A list of tables, parents first.
    """
    results = []
    bases = [django.db.models.Model]
    cont = True
    classes = [c for c in m.__dict__.values() if isclass(c)]
    while cont:
        cont = False
        baseset = set(bases + results)
        for cls in classes:
            if cls in results:
                continue
            if baseset.isdisjoint(cls.__bases__):
                continue
            # This seems to be a database table
            results.append(cls)
            cont = True

    return results


class TableFactory:
    def __init__(self):
        self.tables = {}

        self.type_conversion = {'OneToOneField':sa.Integer,
                               'CharField':sa.String,
                               'EmailField':sa.String,
                               'TextField':sa.Text,
                               'ForeignKey':sa.Integer,
                               'BooleanField':sa.Boolean,
                               'IntegerField':sa.Integer,
                               'DateTimeField':sa.DateTime,
                               'DateField':sa.Date,
                               'FloatField':sa.Float,
                               'DecimalField':sa.Float,
                               'BinaryField':sa.LargeBinary,
                               'ImageField':sa.LargeBinary}

    @staticmethod
    def convert_model(model):
        factory = TableFactory()
        tables = [django.contrib.auth.models.User] + find_tables(model)
        for table in tables:
            factory.table_factory(table)
        return factory.tables


    def table_factory(self, table):
        attrs = {'__tablename__': table._meta.db_table}

        for field in table._meta.local_concrete_fields:
            self.create_field(field, attrs)

        # Determine the base classes
        bases = []
        for b in table.__bases__:
            if b in self.tables:
                t = self.tables[b]
                bases.append(t)
        if bases:
            bases = tuple(bases)
        else:
            bases = (Base,)
        if hasattr(table, 'polymorphic_on') and bases != (Base,):
            # The join should be made on the foreign key <basetable>_ptr_id
            b = table.__bases__[0]
            fk_name = '%s_ptr_id'%b.__name__.lower()
            col = attrs[fk_name]
            remote_details = list(col.foreign_keys)[0]._column_tokens  # (Database, table, column)
            remote_table = globals()[b.__name__]
            remote_col = getattr(remote_table, remote_details[2]) # (col.foreign_keys)[0]._colspec
            attrs['__mapper_args__'] = {
                'polymorphic_identity': table.polymorphic_identity(),
                'inherit_condition': col == remote_col}


        # Handle a polymorphic base class
        if 'polymorphic_on' in table.__dict__:
            n = table.polymorphic_on
            attrs['__mapper_args__'] = {'polymorphic_on':attrs[n],
                'polymorphic_identity': table.polymorphic_identity()}

        # Create the table class
        print ('CREATING CLASS', table.__name__, bases, attrs)
        nt = type(table.__name__, bases, attrs)
        self.tables[table] = nt
        globals()[table.__name__] = nt

    def create_field(self, field, attrs):
        if field.__class__.__name__ == 'AutoField':
            t = self.handle_autofield(field)
        else:
            t = self.type_conversion[field.__class__.__name__]
        if t:
            kwargs = {'primary_key':field.primary_key}
            if t == sa.String:
                t = t(field.max_length)
            args = [t]
            if isinstance(field, django.db.models.fields.related.ForeignKey):
                for fk in field.foreign_related_fields:
                    fk = sa.ForeignKey('%s.%s'%(fk.model._meta.db_table, fk.column))
                    args.append(fk)
            col = sa.Column(*args, **kwargs)
            attrs[field.column] = col
            if False and isinstance(field, django.db.models.fields.related.ForeignKey):
                attrs[field.name] = relationship(field.rel.model.__name__, foreign_keys=[col])

    def handle_autofield(self, field):
        if field.primary_key:
            return sa.Integer



#t = table_factory(models.Requirement)
bridge = TableFactory.convert_model(models)
pass


if __name__ == '__main__':
    engine = sa.create_engine('sqlite://///home/ehwaal/arbeid/privee/private/Various/archtool_web/server/archtool.sqlite3',
                              echo="debug")
    Session = sa.orm.sessionmaker(bind=engine)
    session = Session()

    # List all the Requirement records
    all = session.query(Requirement).all()
    for r in all:
        print (r.name, r.description, r.reqtype)

