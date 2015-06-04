from rest_api.models import Priorities, System, PlaneableItem
from rest_api.serializations import (SystemSerializer, PlaneableListSerializers, \
    PlaneableDetailSerializer)
from rest_framework.decorators import api_view
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import APIView
from django.http import Http404, HttpResponseBadRequest


class SystemList(generics.ListCreateAPIView):
    queryset = System.objects.all()
    serializer_class = SystemSerializer


@api_view(['GET'])
def priorities_list(request):
    return Response(Priorities.keys())


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
        queryset.filter(itemtype=itemtype).filter(system_id=system)
        return queryset

    def get_serializer_class(self):
        itemtype = self.request.query_params['itemtype']
        return PlaneableListSerializers[itemtype]


class PlaneableDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = PlaneableItem.objects.all()
    serializer_class = PlaneableDetailSerializer


class ViewItemsView:
    pass


class WorkItemsView:
    pass


class PlanningView:
    pass
