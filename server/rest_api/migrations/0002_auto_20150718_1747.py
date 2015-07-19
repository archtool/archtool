# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('rest_api', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='anchor',
            name='anchortype',
            field=models.CharField(max_length=6, default='anchor'),
        ),
        migrations.AlterField(
            model_name='planeablestatus',
            name='timeremaining',
            field=models.FloatField(default=None, null=True),
        ),
        migrations.AlterField(
            model_name='planeablestatus',
            name='timespent',
            field=models.FloatField(default=None, null=True),
        ),
    ]
