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


def create_planeableserializer(cls):
    class Serializer(serializers.ModelSerializer):
        parent = serializers.IntegerField(source='parent_id', required=False, allow_null=True,
                                          validators=[])
        class Meta:
            model = cls
            fields = ('id', 'name', 'parent', 'order')
        def is_valid(self, raise_exception=False):
            valid = serializers.ModelSerializer.is_valid(self, raise_exception)
            if not valid:
                return valid
            if self.context['request'].method == 'POST':
                if 'system_id' not in self.context['request'].POST:
                    self.validated_data['system_id'] = self.context['request'].GET['system']
                if 'itemtype' not in self.context['request'].POST:
                    self.validated_data['itemtype'] = self.context['request'].GET['itemtype']
            return valid
    return Serializer

PlaneableListSerializers = {cls.abref : create_planeableserializer(cls)
                            for cls in PlaneableItem.classes()}


class PlaneableDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlaneableItem
