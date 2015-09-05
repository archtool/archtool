# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('rest_api', '0002_auto_20150718_1747'),
    ]

    operations = [
        migrations.CreateModel(
            name='StructuralItem',
            fields=[
                ('planeableitem_ptr', models.OneToOneField(primary_key=True, serialize=False, parent_link=True, to='rest_api.PlaneableItem', auto_created=True)),
            ],
            bases=('rest_api.planeableitem',),
        ),
    ]
