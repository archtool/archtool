__author__ = 'ehwaal'

from django.forms import widgets
from django.views.decorators.csrf import csrf_exempt
from rest_framework import serializers
from .models import (System, PlaneableItem, PlaneableStatus, Requirement, Action,
                     Connection, Bug, View, Project)

class SystemSerializer(serializers.ModelSerializer):
    class Meta:
        model = System
        fields = ('id', 'name', 'description')


class PlaneableListSerializer(serializers.ModelSerializer):
    parent = serializers.IntegerField(source='parent_id', required=False, allow_null=True,
                                      validators=[])
    system = serializers.IntegerField(source='system_id', validators=[])

    class Meta:
        model = PlaneableItem
        fields = ('id', 'name', 'parent', 'order', 'itemtype', 'system')

def create_planeableserializer(cls):
    class S(serializers.ModelSerializer):
        parent = serializers.IntegerField(source='parent_id', required=False, allow_null=True,
                                          validators=[],
                                          style={'base_template': 'hidden.html'})
        system = serializers.IntegerField(source='system_id', validators=[],
                                          style={'base_template': 'hidden.html'})

        class Meta:
            model = cls
            fields = cls.get_detailfields()
            extra_kwargs = {'itemtype': {'style': {'base_template': 'hidden.html'}},
                            'order':    {'style': {'base_template': 'hidden.html'}}}

    return S


PlaneableDetailSerializers = {cls.abref : create_planeableserializer(cls)
                            for cls in PlaneableItem.classes()}


class PlaneableDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlaneableItem
