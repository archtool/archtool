__author__ = 'ehwaal'

from django.forms import widgets
from rest_framework import serializers
from .models import System, NAME_LENGTH

class SystemSerializer(serializers.ModelSerializer):
    class Meta:
        model = System
        fields = ('id', 'name', 'description')



