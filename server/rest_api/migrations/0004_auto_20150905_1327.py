# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('rest_api', '0003_structuralitem'),
    ]

    operations = [
        migrations.AddField(
            model_name='requirement',
            name='stakeholder',
            field=models.CharField(max_length=100, blank=True),
        ),
        migrations.AlterField(
            model_name='actionrepresentation',
            name='action',
            field=models.ForeignKey(null=True, to='rest_api.PlaneableItem', on_delete=django.db.models.deletion.SET_NULL),
        ),
        migrations.AlterField(
            model_name='actionrepresentation',
            name='xoffset',
            field=models.FloatField(default=0),
        ),
        migrations.AlterField(
            model_name='actionrepresentation',
            name='yoffset',
            field=models.FloatField(default=0),
        ),
        migrations.AlterField(
            model_name='annotation',
            name='description',
            field=models.TextField(default=''),
        ),
        migrations.AlterField(
            model_name='annotation',
            name='height',
            field=models.FloatField(default=50),
        ),
        migrations.AlterField(
            model_name='annotation',
            name='width',
            field=models.FloatField(default=100),
        ),
        migrations.AlterField(
            model_name='annotation',
            name='x',
            field=models.FloatField(default=0),
        ),
        migrations.AlterField(
            model_name='annotation',
            name='y',
            field=models.FloatField(default=0),
        ),
        migrations.AlterField(
            model_name='blockrepresentation',
            name='height',
            field=models.FloatField(default=50),
        ),
        migrations.AlterField(
            model_name='blockrepresentation',
            name='ismultiple',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='blockrepresentation',
            name='planeable',
            field=models.ForeignKey(null=True, to='rest_api.PlaneableItem', on_delete=django.db.models.deletion.SET_NULL),
        ),
        migrations.AlterField(
            model_name='blockrepresentation',
            name='width',
            field=models.FloatField(default=100),
        ),
        migrations.AlterField(
            model_name='blockrepresentation',
            name='x',
            field=models.FloatField(default=0),
        ),
        migrations.AlterField(
            model_name='blockrepresentation',
            name='y',
            field=models.FloatField(default=0),
        ),
        migrations.AlterField(
            model_name='connectionrepresentation',
            name='connection',
            field=models.ForeignKey(null=True, to='rest_api.PlaneableItem', related_name='+', on_delete=django.db.models.deletion.SET_NULL),
        ),
        migrations.AlterField(
            model_name='connectionrepresentation',
            name='end',
            field=models.ForeignKey(null=True, to='rest_api.PlaneableItem', related_name='+', on_delete=django.db.models.deletion.SET_NULL),
        ),
        migrations.AlterField(
            model_name='connectionrepresentation',
            name='start',
            field=models.ForeignKey(null=True, to='rest_api.PlaneableItem', related_name='+', on_delete=django.db.models.deletion.SET_NULL),
        ),
        migrations.AlterField(
            model_name='planeableitem',
            name='name',
            field=models.CharField(max_length=100, blank=True),
        ),
    ]
