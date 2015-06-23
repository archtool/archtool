from string import Template
from .models import Priorities, System, PlaneableItem, RequirementType
from .serializations import (SystemSerializer, PlaneableListSerializer, \
    PlaneableDetailSerializers)
from rest_framework.decorators import api_view
from rest_framework import generics, permissions
from rest_framework.renderers import HTMLFormRenderer, JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import mixins
from django.http import Http404, HttpResponseBadRequest
from django.db.models.fields import TextField
from os import path

homedir = path.dirname(__file__)

class SystemList(generics.ListCreateAPIView):
    queryset = System.objects.all()
    serializer_class = SystemSerializer
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
    serializer_class = SystemSerializer


class PlaneableTypesView(APIView):
    def get(self, request):
        return Response(PlaneableItem.get_types())


class PlaneableItemsList(generics.ListCreateAPIView):
    def get_queryset(self):
        """ The queryset is dependent on the argument 'itemtype' and 'model' supplied in the
            request.
        :return: The queryset
        """
        queryset = PlaneableItem.objects.all()
        itemtype = self.request.query_params['itemtype']
        system = self.request.query_params['system']
        if not system:
            return []
        system = int(system)
        if not itemtype:
            itemtype = PlaneableItem.get_types()[0]
        queryset = queryset.filter(itemtype=itemtype).filter(system_id=system)
        queryset = queryset.order_by('parent').order_by('order')
        return queryset


    def get_serializer_class(self):
        itemtype = self.request.query_params['itemtype']
        if self.request.method == 'POST':
            return PlaneableDetailSerializers[itemtype]
        return PlaneableListSerializer


class PlaneableDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = PlaneableItem.objects.all()
    # TODO: Add authorization
    permission_classes = (permissions.AllowAny,)

    def get_serializer_class(self):
        return PlaneableDetailSerializers[itemtype]


class MyFormRenderer(HTMLFormRenderer):
    template_pack = 'archtool'
    base_template = 'form.html'


class DetailEditorView(generics.RetrieveUpdateDestroyAPIView,
                       mixins.CreateModelMixin):
    renderer_classes = [MyFormRenderer]
    queryset = System.objects.all()

    def get_object(self):
        itemtype = self.request.query_params['itemtype']
        if not self.lookup_url_kwarg or 'pk' not in self.lookup_url_kwarg:
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
