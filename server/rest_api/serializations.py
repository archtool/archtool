__author__ = 'ehwaal'

from django.forms import widgets
from django.views.decorators.csrf import csrf_exempt
from rest_framework import serializers
from . import models


class PlaneableListSerializer(serializers.ModelSerializer):
    parent = serializers.IntegerField(source='parent_id', required=False, allow_null=True,
                                      validators=[])
    system = serializers.IntegerField(source='system_id', validators=[])

    class Meta:
        model = models.PlaneableItem
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

        if cls == models.Bug:
            reportedby = serializers.IntegerField(source='reportedby_id', validators=[],
                          read_only=True,
                          default=FieldContext(lambda slf:slf.context['request'].user.id))
        if cls == models.Connection:
            start = serializers.IntegerField(source='start_id', required=True, allow_null=False)
            end = serializers.IntegerField(source='end_id', required=True, allow_null=False)

        class Meta:
            model = cls
            fields = cls.get_detailfields()
            style = {'title':cls.editor_title}
            extra_kwargs = {'itemtype': {'style': {'base_template': 'hidden.html'}},
                            'order':    {'style': {'base_template': 'hidden.html'}}}
            read_only_fields = []
    return S

PlaneableDetailSerializers = {cls.abref : create_planeableserializer(cls)
                            for cls in models.PlaneableItem.classes()}



def create_anchorserializer(cls):
    class Serializer(serializers.ModelSerializer):
        view = serializers.IntegerField(source='view_id')
        style_role = serializers.CharField(default='')
        order = serializers.IntegerField(default=0)

        # Anchor type specific fields
        if cls == models.BlockRepresentation:
            planeable = serializers.IntegerField(source='planeable_id')
        if cls == models.Connection:
            connection = serializers.IntegerField(source='connection_id')
            start = serializers.IntegerField(source='start_id')
            end = serializers.IntegerField(source='end_id')
        if cls == models.ActionRepresentation:
            action = serializers.IntegerField(source='action_id')
            anchorpoint = serializers.IntegerField(source='anchorpoint_id')
        if cls == models.Annotation:
            anchorpoint = serializers.IntegerField(source='anchorpoint_id')

        class Meta:
            model = cls
            fields = cls.get_detailfields()
    return Serializer


class PlaneableDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.PlaneableItem


anchor_serializers = {'line'  : create_anchorserializer(models.ConnectionRepresentation),
                      'block' : create_anchorserializer(models.BlockRepresentation),
                      'action': create_anchorserializer(models.ActionRepresentation),
                      'note'  : create_anchorserializer(models.Annotation)}