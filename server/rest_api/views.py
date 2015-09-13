from string import Template
from .models import (Priorities, System, PlaneableItem, RequirementType, PlaneableStatus,
                     BlockRepresentation, ConnectionRepresentation, ActionRepresentation,
                     Annotation, Anchor)
from .serializations import (PlaneableListSerializer, PlaneableDetailSerializers, FieldContext,
                             create_anchorserializer)
from . import models
from rest_api import alchemy_model
from rest_framework.decorators import api_view
from rest_framework import generics, permissions
from rest_framework.renderers import HTMLFormRenderer, JSONRenderer
from rest_framework.utils.field_mapping import ClassLookupDict
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import mixins
from rest_framework import exceptions, serializers, status, VERSION
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.http import HttpResponse
from django.views.generic import View

from os import path
import json

homedir = path.dirname(__file__)


class MyFormRenderer(HTMLFormRenderer):
    template_pack = 'archtool'
    base_template = 'form.html'

    default_style = ClassLookupDict(dict(HTMLFormRenderer.default_style.mapping))
    default_style[serializers.DateField] = {
            'base_template': 'input.html',
            'input_type': 'text'
        }



@login_required
def FrontPage(request):
    print ('User:', request.user.username, request.user.id)
    return render(request, 'archtool/frontpage.html', {})


class SystemList(generics.ListCreateAPIView):
    queryset = System.objects.all()
    class serializer_class(serializers.ModelSerializer):
        class Meta:
            model = System
            fields = ('id', 'name', 'description')
    # TODO: Add authorization
    permission_classes = (permissions.AllowAny,)


@api_view(['GET'])
def priorities_list(request):
    return Response(Priorities.keys())


@api_view(['GET'])
def reqtypes_list(request):
    return Response(RequirementType.keys())


class SystemDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = System.objects.all()
    serializer_class = SystemList.serializer_class


class PlaneableTypesView(APIView):
    def get(self, request):
        return Response(PlaneableItem.get_types())


class PlaneableItemsList(generics.ListCreateAPIView):
    def get_queryset(self):
        """ The queryset is dependent on the argument 'itemtype' and 'model' supplied in the
            request.
        :return: The queryset
        """
        itemtype = self.request.query_params['itemtype']
        cls = PlaneableItem.get_cls(itemtype)
        queryset = cls.objects.all()
        system = self.request.query_params['system']
        system = int(system)
        queryset = queryset.filter(system_id=system)
        queryset = queryset.order_by('parent').order_by('order')
        return queryset


    def get_serializer_class(self):
        itemtype = self.request.query_params['itemtype']
        if self.request.method == 'POST':
            return PlaneableDetailSerializers[itemtype]
        return PlaneableListSerializer


class PlaneableStatusList(generics.ListCreateAPIView):
    def get_queryset(self):
        queryset = PlaneableStatus.objects.all()
        planeable = self.kwargs['planeable']
        return queryset.filter(planeable_id=planeable).order_by('timestamp')
    class serializer_class(serializers.ModelSerializer):
        # TODO: support for assigned_to
        planeable = serializers.IntegerField(source='planeable_id',
                    default=FieldContext(lambda self: self.context['view'].kwargs['planeable']),
                                            validators=[])
        class Meta:
            model = PlaneableStatus
            fields = ('id', 'planeable', 'description', 'timestamp', 'status', 'timeremaining',
                      'timespent')
            extra_kwargs = {'timespent': {'required': False, 'default': None, 'allow_null': True},
                            'timeremaining': {'required': False, 'default': None, 'allow_null': True},
                           }

class PlaneableStatusDetails(generics.RetrieveUpdateDestroyAPIView):
    queryset = PlaneableStatus.objects.all()
    serializer_class = PlaneableStatusList.serializer_class


class PlaneableDetailView(generics.RetrieveUpdateDestroyAPIView):
    # TODO: Add authorization
    permission_classes = (permissions.AllowAny,)

    def get_queryset(self):
        """ The queryset is dependent on the argument 'itemtype' and 'model' supplied in the
            request.
        :return: The queryset
        """
        itemtype = self.request.query_params['itemtype']
        cls = PlaneableItem.get_cls(itemtype)
        return cls.objects.all()

    def get_serializer_class(self):
        itemtype = self.request.query_params['itemtype']
        if itemtype in PlaneableDetailSerializers:
            return PlaneableDetailSerializers[itemtype]
        else:
            return PlaneableDetailSerializers['item']


class DetailEditorView(generics.RetrieveUpdateDestroyAPIView,
                       mixins.CreateModelMixin):
    renderer_classes = [MyFormRenderer]

    def get_queryset(self):
        itemtype = self.request.query_params['itemtype']
        if itemtype == 'system':
            return System.objects.all()
        else:
            for cls in PlaneableItem.__subclasses__():
                if cls.abref == itemtype:
                    return cls.objects.all()

    def get_object(self):
        itemtype = self.request.query_params['itemtype']
        if 'pk' not in self.kwargs:
            # Return a default instance
            if itemtype == 'system':
                return System()
            else:
                return PlaneableItem.get_default(itemtype)
        return generics.RetrieveUpdateDestroyAPIView.get_object(self)

    def get_serializer_class(self):
        itemtype = self.request.query_params['itemtype']
        if itemtype in PlaneableDetailSerializers:
            return PlaneableDetailSerializers[itemtype]
        elif itemtype == 'system':
            return SystemList.serializer_class
        return PlaneableListSerializer


# Create base serializers
view_serializers = {'line'  : create_anchorserializer(models.ConnectionRepresentation),
                    'block' : create_anchorserializer(models.BlockRepresentation),
                    'action': create_anchorserializer(models.ActionRepresentation),
                    'note'  : create_anchorserializer(models.Annotation)}

@api_view(['GET'])
def view_details(request, view):
    # Get all anchors and lines for the view, and return them in a single object
    all_items = {}
    for key, cls in [['blocks', BlockRepresentation],
                     ['connections', ConnectionRepresentation],
                     ['actions', ActionRepresentation],
                     ['annotations', Annotation]]:
        queryset = cls.objects.filter(view=view).all()
        if key == 'block':
            queryset.select_related('planeable')
        elif key == 'line':
            queryset.select_related('connection')
        elif key == 'action':
            queryset.select_related('action')
        serializer = view_serializers[cls._abref](queryset, many=True)
        all_items[key] = serializer.data
    return Response(all_items)



class ViewItemDetailsView(generics.RetrieveUpdateDestroyAPIView,
                          mixins.CreateModelMixin):
    def post(self, request, *args, **kwargs):
        # Allow lines to be created with a connection object.
        # If so, find or create the appropriate connection.
        if request.data['anchortype'] == 'line' and
           request.data.get('connection', None) is None:
           # Check if there is a connection
           start = models.BlockRepresentation.objects.filter(id=request.data['start'])
           end = models.BlockRepresentation.objects.filter(id=request.data['end'])
           con = models.Connection.objects.filter(start_id=start.planeable, end_id=end.planeable)
           results = list(con)
           if len(results) > 0:
                request.data['connection'] = results[0].id
           else:
                # Create a new connection and use it.
                con = models.Connection(start_id=start.planeable,
                                        end_id = end.planeable,
                                        system_id=start.planeable.system,
                                        name = '')
                con.save()
                request.data['connection'] = con.id
        return self.create(request, *args, **kwargs)

    querysets = {'block':  BlockRepresentation.objects.all(),
                 'line':   ConnectionRepresentation.objects.all(),
                 'action': ActionRepresentation.objects.all(),
                 'note'  : Annotation.objects.all()}

    def get_queryset(self):
        anchortype = self.request.data['anchortype']
        return self.querysets[anchortype]

    def get_object(self):
        """ Overrides the APIView implementation of get_object to supply an empty
            instance when creating a new object.
        :return: either an empty object or an object retrieved via the normal
                 get_object method.
        """
        anchortype = self.request.data['anchortype']
        if 'pk' not in self.kwargs:
            # Return a default instance
            return Anchor.get_default(anchortype)
        return generics.RetrieveUpdateDestroyAPIView.get_object(self)

    serializers = {'line'  : create_anchorserializer(models.ConnectionRepresentation),
                   'block' : create_anchorserializer(models.BlockRepresentation),
                   'action': create_anchorserializer(models.ActionRepresentation),
                   'note'  : create_anchorserializer(models.Annotation)}

    def get_serializer_class(self):
        """
        :return: The proper serializer for the required anchor type.
        """
        return self.serializers[self.request.data['anchortype']]



class WorkItemsView:
    pass


class PlanningView:
    pass
