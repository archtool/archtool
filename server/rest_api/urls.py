__author__ = 'ehwaal'

from django.conf.urls import url
from rest_framework.urlpatterns import format_suffix_patterns
from rest_api import views

urlpatterns = [
    url(r'^system/$', views.SystemList.as_view()),
    url(r'^system/(?P<pk>[0-9]+)/$', views.SystemDetail.as_view()),
]

urlpatterns = format_suffix_patterns(urlpatterns)