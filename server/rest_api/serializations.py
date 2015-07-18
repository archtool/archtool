__author__ = 'ehwaal'

from django.forms import widgets
from django.views.decorators.csrf import csrf_exempt
from rest_framework import serializers
from .models import (System, PlaneableItem, PlaneableStatus, Requirement, Action,
                     Connection, Bug, View, Project)


class PlaneableListSerializer(serializers.ModelSerializer):
    parent = serializers.IntegerField(source='parent_id', required=False, allow_null=True,
                                      validators=[])
    system = serializers.IntegerField(source='system_id', validators=[])

    class Meta:
        model = PlaneableItem
        fields = ('id', 'name', 'parent', 'order', 'itemtype', 'system')


class FieldContext:
    """ A class that helps provide a default value for a field with a context.
        This context is the serializer context.
        The serializer context is set in the GenericAPIView, by the result of
        get_serializer_context. Normally this object is a dictionary with three
        entries:
            'request': the current request object,
            'format': the view's format_kwarg object, and
            'view' the current view object.
    """
    def __init__(self, func):
        self.serializer = None
        self.func = func
    @property
    def context(self):
        return self.serializer.context
    def set_context(self, serializer):
        self.serializer = serializer
    def __call__(self, *args, **kwargs):
        return self.func(self, *args, **kwargs)



def create_planeableserializer(cls):
    class S(serializers.ModelSerializer):
        parent = serializers.IntegerField(source='parent_id', required=False, allow_null=True,
                                          validators=[],
                                          style={'base_template': 'hidden.html'})
        system = serializers.IntegerField(source='system_id', validators=[],
                                          style={'base_template': 'hidden.html'})

        if cls == Bug:
            reportedby = serializers.IntegerField(source='reportedby_id', validators=[],
                          read_only=True,
                          default=FieldContext(lambda slf:slf.context['request'].user.id))

        class Meta:
            model = cls
            fields = cls.get_detailfields()
            style = {'title':cls.editor_title}
            extra_kwargs = {'itemtype': {'style': {'base_template': 'hidden.html'}},
                            'order':    {'style': {'base_template': 'hidden.html'}}}
            read_only_fields = []
    return S


PlaneableDetailSerializers = {cls.abref : create_planeableserializer(cls)
                            for cls in PlaneableItem.classes()}


class P0laneableDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlaneableItem
