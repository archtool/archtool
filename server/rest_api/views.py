from string import Template
import json
from rest_api.models import Priorities, System, PlaneableItem
from rest_api.serializations import (SystemSerializer, PlaneableListSerializer, \
    PlaneableDetailSerializer)
from rest_framework.decorators import api_view
from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from django.http import Http404, HttpResponseBadRequest


class SystemList(generics.ListCreateAPIView):
    queryset = System.objects.all()
    serializer_class = SystemSerializer
    # TODO: Add authorization
    permission_classes = (permissions.AllowAny,)


@api_view(['GET'])
def priorities_list(request):
    return Response(Priorities.keys())



class EditorTemplatesGenerator:
    SYSTEM_TEMPLATE = '''
<div class="modal-header">
<h3 class="modal-title">Model Details</h3>
</div><form role="form"><div class="form-group>
  <label for="name">Name</label>
  <input type="text" class="form-control" id="name" ng-model="system.name">
</div><div class="form-group>
  <label for="description">Description</label>
  <input type="textarea" class="form-control" id="description"  ng-model="system.description">
</div><div class="modal-footer">
  <button class="btn btn-primary" ng-click="ok()">OK</button>
  <button class="btn btn-warning" ng-click="cancel()">Cancel</button>
</div></form>
'''
    ITEM_TEMPLATE = '''
<div class="modal-header">
<h3 class="modal-title">Planeable Details</h3>
</div><form role="form"><div class="form-group>
  <label for="name">Name</label>
  <input type="text" class="form-control" id="name" ng-model="item.name">
</div><div class="form-group>
  <label for="description">Description</label>
  <input type="textarea" class="form-control" id="description"  ng-model="item.description">
</div><div class="form-group>
  <label for="priority">Priority</label>
  <select ng-model="item.priority" ng-options="name for name in $root.priorities"></select>
</div><div class="modal-footer">
  <button class="btn btn-primary" ng-click="ok()">OK</button>
  <button class="btn btn-warning" ng-click="cancel()">Cancel</button>
</div></form>
'''
    @api_view(['GET'])
    def get_template(request, name):
        if name == 'system':
            return Response(EditorTemplatesGenerator.SYSTEM_TEMPLATE)
        return Response(EditorTemplatesGenerator.ITEM_TEMPLATE)




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

    serializer_class = PlaneableListSerializer


class PlaneableDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = PlaneableItem.objects.all()
    serializer_class = PlaneableDetailSerializer
    # TODO: Add authorization
    permission_classes = (permissions.AllowAny,)


class ViewItemsView:
    pass


class WorkItemsView:
    pass


class PlanningView:
    pass
