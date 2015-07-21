__author__ = 'ehwaal'

from django.conf.urls import url, include
from rest_framework.urlpatterns import format_suffix_patterns
from rest_api import views

urlpatterns = [
    url(r'^$', views.FrontPage),
    url(r'^accounts/', include('django.contrib.auth.urls')),
    url(r'^api/systems/$', views.SystemList.as_view()),
    url(r'^api/systems/(?P<pk>[0-9]+)/$', views.SystemDetail.as_view()),
    url(r'^api/priorities/$', views.priorities_list),
    url(r'^api/reqtypes/$', views.reqtypes_list),
    url(r'^api/planeabletypes/$', views.PlaneableTypesView.as_view()),
    url(r'^api/planeableitems/$', views.PlaneableItemsList.as_view()),
    url(r'^api/planeableitems/(?P<pk>[0-9]+)/$', views.PlaneableDetailView.as_view()),
    url(r'^api/editors/$', views.DetailEditorView.as_view()),
    url(r'^api/editors/(?P<pk>[0-9]+)/$', views.DetailEditorView.as_view()),
    url(r'^api/planeablestatuslist/(?P<planeable>[0-9]+)/$', views.PlaneableStatusList.as_view()),
    url(r'^api/planeablestatusdetails/(?P<pk>[0-9]+)/$', views.PlaneableStatusDetails.as_view()),
]

urlpatterns = format_suffix_patterns(urlpatterns)