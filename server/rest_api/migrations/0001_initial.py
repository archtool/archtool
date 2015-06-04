# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.db.models.deletion
from decimal import Decimal


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Model',
            fields=[
                ('id', models.AutoField(serialize=False, primary_key=True, auto_created=True, verbose_name='ID')),
            ],
        ),
        migrations.CreateModel(
            name='Anchor',
            fields=[
                ('model_ptr', models.OneToOneField(primary_key=True, auto_created=True, to='rest_api.Model', serialize=False, parent_link=True)),
                ('style_role', models.CharField(max_length=100)),
                ('order', models.IntegerField(default=0)),
            ],
            bases=('rest_api.model',),
        ),
        migrations.CreateModel(
            name='Attachment',
            fields=[
                ('model_ptr', models.OneToOneField(primary_key=True, auto_created=True, to='rest_api.Model', serialize=False, parent_link=True)),
                ('name', models.CharField(max_length=100)),
                ('data', models.BinaryField()),
            ],
            bases=('rest_api.model',),
        ),
        migrations.CreateModel(
            name='ChangeLog',
            fields=[
                ('model_ptr', models.OneToOneField(primary_key=True, auto_created=True, to='rest_api.Model', serialize=False, parent_link=True)),
                ('recordtype', models.CharField(max_length=20)),
                ('recordid', models.IntegerField()),
                ('changetype', models.IntegerField(choices=[(1, 'add'), (2, 'delete'), (3, 'change')])),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('details', models.TextField()),
            ],
            bases=('rest_api.model',),
        ),
        migrations.CreateModel(
            name='CrossrefType',
            fields=[
                ('model_ptr', models.OneToOneField(primary_key=True, auto_created=True, to='rest_api.Model', serialize=False, parent_link=True)),
                ('forwardname', models.CharField(max_length=40)),
                ('backwardname', models.CharField(max_length=40)),
            ],
            bases=('rest_api.model',),
        ),
        migrations.CreateModel(
            name='DbaseVersion',
            fields=[
                ('model_ptr', models.OneToOneField(primary_key=True, auto_created=True, to='rest_api.Model', serialize=False, parent_link=True)),
                ('version', models.IntegerField(default=16)),
            ],
            bases=('rest_api.model',),
        ),
        migrations.CreateModel(
            name='Icon',
            fields=[
                ('model_ptr', models.OneToOneField(primary_key=True, auto_created=True, to='rest_api.Model', serialize=False, parent_link=True)),
                ('name', models.CharField(max_length=100)),
                ('data', models.ImageField(upload_to='', max_length=100000)),
            ],
            bases=('rest_api.model',),
        ),
        migrations.CreateModel(
            name='PlaneableItem',
            fields=[
                ('model_ptr', models.OneToOneField(primary_key=True, auto_created=True, to='rest_api.Model', serialize=False, parent_link=True)),
                ('name', models.CharField(max_length=100)),
                ('description', models.TextField()),
                ('priority', models.IntegerField(default=1, choices=[(1, 'must'), (2, 'should'), (3, 'could'), (4, 'would')])),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('order', models.IntegerField(default=0)),
                ('itemtype', models.CharField(max_length=6)),
            ],
            bases=('rest_api.model',),
        ),
        migrations.CreateModel(
            name='PlaneableStatus',
            fields=[
                ('model_ptr', models.OneToOneField(primary_key=True, auto_created=True, to='rest_api.Model', serialize=False, parent_link=True)),
                ('description', models.TextField()),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('status', models.IntegerField(choices=[(1, 'open'), (2, 'in_progress'), (3, 'testing'), (4, 'question'), (5, 'done'), (6, 'rejected'), (7, 'duplicate')])),
                ('timeremaining', models.FloatField()),
                ('timespent', models.FloatField()),
            ],
            bases=('rest_api.model',),
        ),
        migrations.CreateModel(
            name='PlaneableXRef',
            fields=[
                ('model_ptr', models.OneToOneField(primary_key=True, auto_created=True, to='rest_api.Model', serialize=False, parent_link=True)),
            ],
            bases=('rest_api.model',),
        ),
        migrations.CreateModel(
            name='PlannedEffort',
            fields=[
                ('model_ptr', models.OneToOneField(primary_key=True, auto_created=True, to='rest_api.Model', serialize=False, parent_link=True)),
                ('week', models.DateField()),
                ('hours', models.FloatField()),
                ('isactual', models.BooleanField(default=False)),
            ],
            bases=('rest_api.model',),
        ),
        migrations.CreateModel(
            name='Style',
            fields=[
                ('model_ptr', models.OneToOneField(primary_key=True, auto_created=True, to='rest_api.Model', serialize=False, parent_link=True)),
                ('name', models.CharField(max_length=100)),
                ('details', models.TextField()),
            ],
            bases=('rest_api.model',),
        ),
        migrations.CreateModel(
            name='System',
            fields=[
                ('model_ptr', models.OneToOneField(primary_key=True, auto_created=True, to='rest_api.Model', serialize=False, parent_link=True)),
                ('name', models.CharField(max_length=100)),
                ('description', models.TextField()),
            ],
            bases=('rest_api.model',),
        ),
        migrations.CreateModel(
            name='User',
            fields=[
                ('model_ptr', models.OneToOneField(primary_key=True, auto_created=True, to='rest_api.Model', serialize=False, parent_link=True)),
                ('name', models.CharField(max_length=100)),
                ('email', models.EmailField(max_length=254)),
                ('hourrate', models.DecimalField(default=Decimal('0.00'), decimal_places=2, max_digits=6)),
            ],
            bases=('rest_api.model',),
        ),
        migrations.CreateModel(
            name='Action',
            fields=[
                ('planeableitem_ptr', models.OneToOneField(primary_key=True, auto_created=True, to='rest_api.PlaneableItem', serialize=False, parent_link=True)),
                ('isresponse', models.BooleanField(default=False)),
            ],
            bases=('rest_api.planeableitem',),
        ),
        migrations.CreateModel(
            name='ActionRepresentation',
            fields=[
                ('anchor_ptr', models.OneToOneField(primary_key=True, auto_created=True, to='rest_api.Anchor', serialize=False, parent_link=True)),
                ('xoffset', models.FloatField()),
                ('yoffset', models.FloatField()),
            ],
            bases=('rest_api.anchor',),
        ),
        migrations.CreateModel(
            name='Annotation',
            fields=[
                ('anchor_ptr', models.OneToOneField(primary_key=True, auto_created=True, to='rest_api.Anchor', serialize=False, parent_link=True)),
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
                ('anchor_ptr', models.OneToOneField(primary_key=True, auto_created=True, to='rest_api.Anchor', serialize=False, parent_link=True)),
                ('x', models.FloatField()),
                ('y', models.FloatField()),
                ('height', models.FloatField()),
                ('width', models.FloatField()),
                ('ismultiple', models.BooleanField()),
                ('icon', models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, null=True, to='rest_api.Icon')),
            ],
            bases=('rest_api.anchor',),
        ),
        migrations.CreateModel(
            name='Bug',
            fields=[
                ('planeableitem_ptr', models.OneToOneField(primary_key=True, auto_created=True, to='rest_api.PlaneableItem', serialize=False, parent_link=True)),
                ('reportedby', models.ForeignKey(to='rest_api.User')),
            ],
            bases=('rest_api.planeableitem',),
        ),
        migrations.CreateModel(
            name='Connection',
            fields=[
                ('planeableitem_ptr', models.OneToOneField(primary_key=True, auto_created=True, to='rest_api.PlaneableItem', serialize=False, parent_link=True)),
            ],
            bases=('rest_api.planeableitem',),
        ),
        migrations.CreateModel(
            name='ConnectionRepresentation',
            fields=[
                ('anchor_ptr', models.OneToOneField(primary_key=True, auto_created=True, to='rest_api.Anchor', serialize=False, parent_link=True)),
            ],
            bases=('rest_api.anchor',),
        ),
        migrations.CreateModel(
            name='Project',
            fields=[
                ('planeableitem_ptr', models.OneToOneField(primary_key=True, auto_created=True, to='rest_api.PlaneableItem', serialize=False, parent_link=True)),
                ('start', models.DateField()),
                ('finish', models.DateField()),
                ('budget', models.DecimalField(decimal_places=2, max_digits=12)),
            ],
            bases=('rest_api.planeableitem',),
        ),
        migrations.CreateModel(
            name='Requirement',
            fields=[
                ('planeableitem_ptr', models.OneToOneField(primary_key=True, auto_created=True, to='rest_api.PlaneableItem', serialize=False, parent_link=True)),
                ('reqtype', models.IntegerField(default=1, choices=[(1, 'functional'), (2, 'non_functional'), (3, 'comment')])),
            ],
            bases=('rest_api.planeableitem',),
        ),
        migrations.CreateModel(
            name='View',
            fields=[
                ('planeableitem_ptr', models.OneToOneField(primary_key=True, auto_created=True, to='rest_api.PlaneableItem', serialize=False, parent_link=True)),
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
            field=models.ForeignKey(to='rest_api.PlaneableItem', related_name='amember'),
        ),
        migrations.AddField(
            model_name='planeablexref',
            name='bitem',
            field=models.ForeignKey(to='rest_api.PlaneableItem', related_name='bmember'),
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
            field=models.ManyToManyField(to='rest_api.PlaneableItem', through='rest_api.PlaneableXRef', related_name='bitems'),
        ),
        migrations.AddField(
            model_name='planeableitem',
            name='attachments',
            field=models.ManyToManyField(to='rest_api.Attachment'),
        ),
        migrations.AddField(
            model_name='planeableitem',
            name='parent',
            field=models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, null=True, to='rest_api.PlaneableItem', related_name='children'),
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
            field=models.ForeignKey(to='rest_api.PlaneableItem', related_name='+'),
        ),
        migrations.AddField(
            model_name='connectionrepresentation',
            name='end',
            field=models.ForeignKey(to='rest_api.PlaneableItem', related_name='+'),
        ),
        migrations.AddField(
            model_name='connectionrepresentation',
            name='start',
            field=models.ForeignKey(to='rest_api.PlaneableItem', related_name='+'),
        ),
        migrations.AddField(
            model_name='connection',
            name='end',
            field=models.ForeignKey(to='rest_api.PlaneableItem', related_name='+'),
        ),
        migrations.AddField(
            model_name='connection',
            name='start',
            field=models.ForeignKey(to='rest_api.PlaneableItem', related_name='+'),
        ),
        migrations.AddField(
            model_name='blockrepresentation',
            name='planeable',
            field=models.ForeignKey(to='rest_api.PlaneableItem'),
        ),
        migrations.AddField(
            model_name='annotation',
            name='anchorpoint',
            field=models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, null=True, to='rest_api.Anchor', related_name='+'),
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
            field=models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, null=True, to='rest_api.Anchor', related_name='+'),
        ),
        migrations.AddField(
            model_name='action',
            name='connection',
            field=models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, null=True, to='rest_api.PlaneableItem', related_name='+'),
        ),
    ]
