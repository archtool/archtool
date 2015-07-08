# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Anchor',
            fields=[
                ('id', models.AutoField(primary_key=True, verbose_name='ID', serialize=False, auto_created=True)),
                ('style_role', models.CharField(max_length=100)),
                ('order', models.IntegerField(default=0)),
            ],
        ),
        migrations.CreateModel(
            name='Attachment',
            fields=[
                ('id', models.AutoField(primary_key=True, verbose_name='ID', serialize=False, auto_created=True)),
                ('name', models.CharField(max_length=100)),
                ('data', models.BinaryField()),
            ],
        ),
        migrations.CreateModel(
            name='ChangeLog',
            fields=[
                ('id', models.AutoField(primary_key=True, verbose_name='ID', serialize=False, auto_created=True)),
                ('recordtype', models.CharField(max_length=20)),
                ('recordid', models.IntegerField()),
                ('changetype', models.IntegerField(choices=[(1, 'add'), (2, 'delete'), (3, 'change')])),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('details', models.TextField()),
            ],
        ),
        migrations.CreateModel(
            name='CrossrefType',
            fields=[
                ('id', models.AutoField(primary_key=True, verbose_name='ID', serialize=False, auto_created=True)),
                ('forwardname', models.CharField(max_length=40)),
                ('backwardname', models.CharField(max_length=40)),
            ],
        ),
        migrations.CreateModel(
            name='DbaseVersion',
            fields=[
                ('id', models.AutoField(primary_key=True, verbose_name='ID', serialize=False, auto_created=True)),
                ('version', models.IntegerField(default=17)),
            ],
        ),
        migrations.CreateModel(
            name='Icon',
            fields=[
                ('id', models.AutoField(primary_key=True, verbose_name='ID', serialize=False, auto_created=True)),
                ('name', models.CharField(max_length=100)),
                ('data', models.ImageField(max_length=100000, upload_to='')),
            ],
        ),
        migrations.CreateModel(
            name='PlaneableItem',
            fields=[
                ('id', models.AutoField(primary_key=True, verbose_name='ID', serialize=False, auto_created=True)),
                ('name', models.CharField(max_length=100)),
                ('description', models.TextField(default='')),
                ('priority', models.IntegerField(choices=[(1, 'must'), (2, 'should'), (3, 'could'), (4, 'would')], default=1)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('order', models.IntegerField(default=0)),
                ('itemtype', models.CharField(max_length=6)),
            ],
        ),
        migrations.CreateModel(
            name='PlaneableStatus',
            fields=[
                ('id', models.AutoField(primary_key=True, verbose_name='ID', serialize=False, auto_created=True)),
                ('description', models.TextField()),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('status', models.IntegerField(choices=[(1, 'open'), (2, 'in_progress'), (3, 'testing'), (4, 'question'), (5, 'done'), (6, 'rejected'), (7, 'duplicate')])),
                ('timeremaining', models.FloatField()),
                ('timespent', models.FloatField()),
                ('assignedto', models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='PlaneableXRef',
            fields=[
                ('id', models.AutoField(primary_key=True, verbose_name='ID', serialize=False, auto_created=True)),
            ],
        ),
        migrations.CreateModel(
            name='PlannedEffort',
            fields=[
                ('id', models.AutoField(primary_key=True, verbose_name='ID', serialize=False, auto_created=True)),
                ('week', models.DateField()),
                ('hours', models.FloatField()),
                ('isactual', models.BooleanField(default=False)),
                ('worker', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Style',
            fields=[
                ('id', models.AutoField(primary_key=True, verbose_name='ID', serialize=False, auto_created=True)),
                ('name', models.CharField(max_length=100)),
                ('details', models.TextField()),
            ],
        ),
        migrations.CreateModel(
            name='System',
            fields=[
                ('id', models.AutoField(primary_key=True, verbose_name='ID', serialize=False, auto_created=True)),
                ('name', models.CharField(max_length=100)),
                ('description', models.TextField()),
            ],
        ),
        migrations.CreateModel(
            name='Action',
            fields=[
                ('planeableitem_ptr', models.OneToOneField(serialize=False, parent_link=True, to='rest_api.PlaneableItem', primary_key=True, auto_created=True)),
                ('isresponse', models.BooleanField(default=False)),
            ],
            bases=('rest_api.planeableitem',),
        ),
        migrations.CreateModel(
            name='ActionRepresentation',
            fields=[
                ('anchor_ptr', models.OneToOneField(serialize=False, parent_link=True, to='rest_api.Anchor', primary_key=True, auto_created=True)),
                ('xoffset', models.FloatField()),
                ('yoffset', models.FloatField()),
            ],
            bases=('rest_api.anchor',),
        ),
        migrations.CreateModel(
            name='Annotation',
            fields=[
                ('anchor_ptr', models.OneToOneField(serialize=False, parent_link=True, to='rest_api.Anchor', primary_key=True, auto_created=True)),
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
                ('anchor_ptr', models.OneToOneField(serialize=False, parent_link=True, to='rest_api.Anchor', primary_key=True, auto_created=True)),
                ('x', models.FloatField()),
                ('y', models.FloatField()),
                ('height', models.FloatField()),
                ('width', models.FloatField()),
                ('ismultiple', models.BooleanField()),
                ('icon', models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, to='rest_api.Icon', null=True)),
            ],
            bases=('rest_api.anchor',),
        ),
        migrations.CreateModel(
            name='Bug',
            fields=[
                ('planeableitem_ptr', models.OneToOneField(serialize=False, parent_link=True, to='rest_api.PlaneableItem', primary_key=True, auto_created=True)),
                ('reportedby', models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL, null=True)),
            ],
            bases=('rest_api.planeableitem',),
        ),
        migrations.CreateModel(
            name='Connection',
            fields=[
                ('planeableitem_ptr', models.OneToOneField(serialize=False, parent_link=True, to='rest_api.PlaneableItem', primary_key=True, auto_created=True)),
            ],
            bases=('rest_api.planeableitem',),
        ),
        migrations.CreateModel(
            name='ConnectionRepresentation',
            fields=[
                ('anchor_ptr', models.OneToOneField(serialize=False, parent_link=True, to='rest_api.Anchor', primary_key=True, auto_created=True)),
            ],
            bases=('rest_api.anchor',),
        ),
        migrations.CreateModel(
            name='Project',
            fields=[
                ('planeableitem_ptr', models.OneToOneField(serialize=False, parent_link=True, to='rest_api.PlaneableItem', primary_key=True, auto_created=True)),
                ('start', models.DateField()),
                ('finish', models.DateField()),
                ('budget', models.DecimalField(max_digits=12, decimal_places=2, default='0.00')),
            ],
            bases=('rest_api.planeableitem',),
        ),
        migrations.CreateModel(
            name='Requirement',
            fields=[
                ('planeableitem_ptr', models.OneToOneField(serialize=False, parent_link=True, to='rest_api.PlaneableItem', primary_key=True, auto_created=True)),
                ('reqtype', models.IntegerField(choices=[(1, 'functional'), (2, 'non_functional'), (3, 'comment')], default=1)),
            ],
            bases=('rest_api.planeableitem',),
        ),
        migrations.CreateModel(
            name='View',
            fields=[
                ('planeableitem_ptr', models.OneToOneField(serialize=False, parent_link=True, to='rest_api.PlaneableItem', primary_key=True, auto_created=True)),
                ('style', models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, to='rest_api.Style', null=True)),
            ],
            bases=('rest_api.planeableitem',),
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
            field=models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, to='rest_api.CrossrefType', null=True),
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
            field=models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, to='rest_api.PlaneableItem', related_name='children', null=True),
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
            field=models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, to='rest_api.Anchor', related_name='+', null=True),
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
            field=models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, to='rest_api.Anchor', related_name='+', null=True),
        ),
        migrations.AddField(
            model_name='action',
            name='connection',
            field=models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, to='rest_api.PlaneableItem', related_name='+', null=True),
        ),
    ]
