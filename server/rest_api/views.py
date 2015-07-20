from string import Template
from .models import Priorities, System, PlaneableItem, RequirementType, PlaneableStatus
from .serializations import (PlaneableListSerializer, PlaneableDetailSerializers, FieldContext)
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
        # TODO: Allow setting assigned_to
        planeable = serializers.HiddenField(source='planeable_id',
                    default=FieldContext(lambda self: self.context['view'].kwargs['planeable']),
                                            validators=[])
        class Meta:
            model = PlaneableStatus
            fields = ('planeable', 'description', 'timestamp', 'status', 'timeremaining',
                      'timespent')
            extra_kwargs = {'timespent': {'required': False, 'default': None, 'allow_null': True},
                            'timeremaining': {'required': False, 'default': None, 'allow_null': True},
                           }




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
            return SystemSerializer
        return PlaneableListSerializer


class ViewItemsView:
    pass


class WorkItemsView:
    pass


class PlanningView:
    pass
