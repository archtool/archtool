from rest_api.models import System
from rest_api.serializations import SystemSerializer
from rest_framework import generics


class SystemList(generics.ListCreateAPIView):
    queryset = System.objects.all()
    serializer_class = SystemSerializer


class SystemDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = System.objects.all()
    serializer_class = SystemSerializer
