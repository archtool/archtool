# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from decimal import Decimal
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Model',
            fields=[
                ('id', models.AutoField(auto_created=True, serialize=False, primary_key=True, verbose_name='ID')),
            ],
        ),
        migrations.CreateModel(
            name='Anchor',
            fields=[
                ('model_ptr', models.OneToOneField(auto_created=True, serialize=False, primary_key=True, parent_link=True, to='rest_api.Model')),
                ('style_role', models.CharField(max_length=100)),
                ('order', models.IntegerField(default=0)),
            ],
            bases=('rest_api.model',),
        ),
        migrations.CreateModel(
            name='Attachment',
            fields=[
                ('model_ptr', models.OneToOneField(auto_created=True, serialize=False, primary_key=True, parent_link=True, to='rest_api.Model')),
                ('name', models.CharField(max_length=100)),
                ('data', models.BinaryField()),
            ],
            bases=('rest_api.model',),
        ),
        migrations.CreateModel(
            name='ChangeLog',
            fields=[
                ('model_ptr', models.OneToOneField(auto_created=True, serialize=False, primary_key=True, parent_link=True, to='rest_api.Model')),
                ('recordtype', models.CharField(max_length=20)),
                ('recordid', models.IntegerField()),
                ('changetype', models.IntegerField(choices=[('add', 1), ('delete', 2), ('change', 3)])),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('details', models.TextField()),
            ],
            bases=('rest_api.model',),
        ),
        migrations.CreateModel(
            name='CrossrefType',
            fields=[
                ('model_ptr', models.OneToOneField(auto_created=True, serialize=False, primary_key=True, parent_link=True, to='rest_api.Model')),
                ('forwardname', models.CharField(max_length=40)),
                ('backwardname', models.CharField(max_length=40)),
            ],
            bases=('rest_api.model',),
        ),
        migrations.CreateModel(
            name='DbaseVersion',
            fields=[
                ('model_ptr', models.OneToOneField(auto_created=True, serialize=False, primary_key=True, parent_link=True, to='rest_api.Model')),
                ('version', models.IntegerField(default=16)),
            ],
            bases=('rest_api.model',),
        ),
        migrations.CreateModel(
            name='PlaneableItem',
            fields=[
                ('model_ptr', models.OneToOneField(auto_created=True, serialize=False, primary_key=True, parent_link=True, to='rest_api.Model')),
                ('name', models.CharField(max_length=100)),
                ('description', models.TextField()),
                ('priority', models.IntegerField(choices=[('must', 1), ('should', 2), ('could', 3), ('would', 4)], default=1)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('order', models.IntegerField(default=0)),
                ('itemtype', models.CharField(max_length=6)),
            ],
            bases=('rest_api.model',),
        ),
        migrations.CreateModel(
            name='PlaneableStatus',
            fields=[
                ('model_ptr', models.OneToOneField(auto_created=True, serialize=False, primary_key=True, parent_link=True, to='rest_api.Model')),
                ('description', models.TextField()),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('status', models.IntegerField(choices=[('open', 1), ('in_progress', 2), ('testing', 3), ('question', 4), ('done', 5), ('rejected', 6), ('duplicate', 7)])),
                ('timeremaining', models.FloatField()),
                ('timespent', models.FloatField()),
            ],
            bases=('rest_api.model',),
        ),
        migrations.CreateModel(
            name='PlaneableXRef',
            fields=[
                ('model_ptr', models.OneToOneField(auto_created=True, serialize=False, primary_key=True, parent_link=True, to='rest_api.Model')),
            ],
            bases=('rest_api.model',),
        ),
        migrations.CreateModel(
            name='PlannedEffort',
            fields=[
                ('model_ptr', models.OneToOneField(auto_created=True, serialize=False, primary_key=True, parent_link=True, to='rest_api.Model')),
                ('week', models.DateField()),
                ('hours', models.FloatField()),
                ('isactual', models.BooleanField(default=False)),
            ],
            bases=('rest_api.model',),
        ),
        migrations.CreateModel(
            name='Style',
            fields=[
                ('model_ptr', models.OneToOneField(auto_created=True, serialize=False, primary_key=True, parent_link=True, to='rest_api.Model')),
                ('name', models.CharField(max_length=100)),
                ('details', models.TextField()),
            ],
            bases=('rest_api.model',),
        ),
        migrations.CreateModel(
            name='System',
            fields=[
                ('model_ptr', models.OneToOneField(auto_created=True, serialize=False, primary_key=True, parent_link=True, to='rest_api.Model')),
                ('name', models.CharField(max_length=100)),
                ('description', models.TextField()),
            ],
            bases=('rest_api.model',),
        ),
        migrations.CreateModel(
            name='User',
            fields=[
                ('model_ptr', models.OneToOneField(auto_created=True, serialize=False, primary_key=True, parent_link=True, to='rest_api.Model')),
                ('name', models.CharField(max_length=100)),
                ('email', models.EmailField(max_length=254)),
                ('hourrate', models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0.00'))),
            ],
            bases=('rest_api.model',),
        ),
        migrations.CreateModel(
            name='Action',
            fields=[
                ('planeableitem_ptr', models.OneToOneField(auto_created=True, serialize=False, primary_key=True, parent_link=True, to='rest_api.PlaneableItem')),
                ('isresponse', models.BooleanField(default=False)),
            ],
            bases=('rest_api.planeableitem',),
        ),
        migrations.CreateModel(
            name='ActionRepresentation',
            fields=[
                ('anchor_ptr', models.OneToOneField(auto_created=True, serialize=False, primary_key=True, parent_link=True, to='rest_api.Anchor')),
                ('xoffset', models.FloatField()),
                ('yoffset', models.FloatField()),
            ],
            bases=('rest_api.anchor',),
        ),
        migrations.CreateModel(
            name='Annotation',
            fields=[
                ('anchor_ptr', models.OneToOneField(auto_created=True, serialize=False, primary_key=True, parent_link=True, to='rest_api.Anchor')),
                ('x', models.FloatField()),
                ('y', models.FloatField()),
                ('height', models.FloatField()),
                ('width', models.FloatField()),
                ('description', models.TextField()),
            ],
            bases=('rest_api.anchor',),
        ),
        migrations.CreateModel(
            name='BlockRepresentation',
            fields=[
                ('anchor_ptr', models.OneToOneField(auto_created=True, serialize=False, primary_key=True, parent_link=True, to='rest_api.Anchor')),
                ('x', models.FloatField()),
                ('y', models.FloatField()),
                ('height', models.FloatField()),
                ('width', models.FloatField()),
                ('ismultiple', models.BooleanField()),
            ],
            bases=('rest_api.anchor',),
        ),
        migrations.CreateModel(
            name='Bug',
            fields=[
                ('planeableitem_ptr', models.OneToOneField(auto_created=True, serialize=False, primary_key=True, parent_link=True, to='rest_api.PlaneableItem')),
                ('reportedby', models.ForeignKey(to='rest_api.User')),
            ],
            bases=('rest_api.planeableitem',),
        ),
        migrations.CreateModel(
            name='Connection',
            fields=[
                ('planeableitem_ptr', models.OneToOneField(auto_created=True, serialize=False, primary_key=True, parent_link=True, to='rest_api.PlaneableItem')),
            ],
            bases=('rest_api.planeableitem',),
        ),
        migrations.CreateModel(
            name='ConnectionRepresentation',
            fields=[
                ('anchor_ptr', models.OneToOneField(auto_created=True, serialize=False, primary_key=True, parent_link=True, to='rest_api.Anchor')),
            ],
            bases=('rest_api.anchor',),
        ),
        migrations.CreateModel(
            name='Project',
            fields=[
                ('planeableitem_ptr', models.OneToOneField(auto_created=True, serialize=False, primary_key=True, parent_link=True, to='rest_api.PlaneableItem')),
                ('start', models.DateField()),
                ('finish', models.DateField()),
                ('budget', models.DecimalField(max_digits=12, decimal_places=2)),
            ],
            bases=('rest_api.planeableitem',),
        ),
        migrations.CreateModel(
            name='Requirement',
            fields=[
                ('planeableitem_ptr', models.OneToOneField(auto_created=True, serialize=False, primary_key=True, parent_link=True, to='rest_api.PlaneableItem')),
                ('reqtype', models.IntegerField(choices=[('functional', 1), ('non_functional', 2), ('comment', 3)], default=1)),
            ],
            bases=('rest_api.planeableitem',),
        ),
        migrations.CreateModel(
            name='View',
            fields=[
                ('planeableitem_ptr', models.OneToOneField(auto_created=True, serialize=False, primary_key=True, parent_link=True, to='rest_api.PlaneableItem')),
                ('style', models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, null=True, to='rest_api.Style')),
            ],
            bases=('rest_api.planeableitem',),
        ),
        migrations.AddField(
            model_name='plannedeffort',
            name='worker',
            field=models.ForeignKey(to='rest_api.User'),
        ),
        migrations.AddField(
            model_name='planeablexref',
            name='aitem',
            field=models.ForeignKey(related_name='amember', to='rest_api.PlaneableItem'),
        ),
        migrations.AddField(
            model_name='planeablexref',
            name='bitem',
            field=models.ForeignKey(related_name='bmember', to='rest_api.PlaneableItem'),
        ),
        migrations.AddField(
            model_name='planeablexref',
            name='reftype',
            field=models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, null=True, to='rest_api.CrossrefType'),
        ),
        migrations.AddField(
            model_name='planeablestatus',
            name='assignedto',
            field=models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, null=True, to='rest_api.User'),
        ),
        migrations.AddField(
            model_name='planeablestatus',
            name='planeable',
            field=models.ForeignKey(to='rest_api.PlaneableItem'),
        ),
        migrations.AddField(
            model_name='planeableitem',
            name='aitems',
            field=models.ManyToManyField(related_name='bitems', to='rest_api.PlaneableItem', through='rest_api.PlaneableXRef'),
        ),
        migrations.AddField(
            model_name='planeableitem',
            name='attachments',
            field=models.ManyToManyField(to='rest_api.Attachment'),
        ),
        migrations.AddField(
            model_name='planeableitem',
            name='parent',
            field=models.ForeignKey(related_name='children', to='rest_api.PlaneableItem', null=True, on_delete=django.db.models.deletion.SET_NULL),
        ),
        migrations.AddField(
            model_name='planeableitem',
            name='system',
            field=models.ForeignKey(to='rest_api.System'),
        ),
        migrations.AddField(
            model_name='plannedeffort',
            name='project',
            field=models.ForeignKey(to='rest_api.Project'),
        ),
        migrations.AddField(
            model_name='connectionrepresentation',
            name='connection',
            field=models.ForeignKey(related_name='+', to='rest_api.PlaneableItem'),
        ),
        migrations.AddField(
            model_name='connectionrepresentation',
            name='end',
            field=models.ForeignKey(related_name='+', to='rest_api.PlaneableItem'),
        ),
        migrations.AddField(
            model_name='connectionrepresentation',
            name='start',
            field=models.ForeignKey(related_name='+', to='rest_api.PlaneableItem'),
        ),
        migrations.AddField(
            model_name='connection',
            name='end',
            field=models.ForeignKey(related_name='+', to='rest_api.PlaneableItem'),
        ),
        migrations.AddField(
            model_name='connection',
            name='start',
            field=models.ForeignKey(related_name='+', to='rest_api.PlaneableItem'),
        ),
        migrations.AddField(
            model_name='blockrepresentation',
            name='planeable',
            field=models.ForeignKey(to='rest_api.PlaneableItem'),
        ),
        migrations.AddField(
            model_name='annotation',
            name='anchorpoint',
            field=models.ForeignKey(related_name='+', to='rest_api.Anchor', null=True, on_delete=django.db.models.deletion.SET_NULL),
        ),
        migrations.AddField(
            model_name='annotation',
            name='attachments',
            field=models.ManyToManyField(to='rest_api.Attachment'),
        ),
        migrations.AddField(
            model_name='anchor',
            name='view',
            field=models.ForeignKey(to='rest_api.View'),
        ),
        migrations.AddField(
            model_name='actionrepresentation',
            name='action',
            field=models.ForeignKey(to='rest_api.PlaneableItem'),
        ),
        migrations.AddField(
            model_name='actionrepresentation',
            name='anchorpoint',
            field=models.ForeignKey(related_name='+', to='rest_api.Anchor', null=True, on_delete=django.db.models.deletion.SET_NULL),
        ),
        migrations.AddField(
            model_name='action',
            name='connection',
            field=models.ForeignKey(related_name='+', to='rest_api.PlaneableItem', null=True, on_delete=django.db.models.deletion.SET_NULL),
        ),
    ]
