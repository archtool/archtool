__author__ = 'ehwaal'

import csv
from server import settings
import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.settings")
import django
django.setup()
# your imports, e.g. Django models

from django.db import transaction
from rest_api.models import Requirement, Priorities

csvfile = '/home/ehwaal/arbeid/privee/private/Various/archtool/archtool.csv'

f = open(csvfile, 'r')
reader = csv.reader(f, delimiter=';', quoting=csv.QUOTE_NONNUMERIC)

_table = next(reader)
columns = next(reader)

print (columns)

reader = csv.DictReader(f, columns, delimiter=';', quoting=csv.QUOTE_NONNUMERIC)

with transaction.atomic():
    for details in reader:
        result = {dest:details[src] for dest, src in [('id', 'Id'),
            ('parent_id', 'Parent'),
            ('name', 'Name'),
            ('created', 'Created'),
            ('description', 'Description')]}
        result['system_id'] = 1
        result['priority'] = getattr(Priorities, details['Priority'].lower())
        result['itemtype'] = 'req'
        obj = Requirement(**result)
        obj.save()


