from string import Template
from rest_api.models import Priorities, System, PlaneableItem, RequirementType
from rest_api.serializations import (SystemSerializer, PlaneableListSerializer, \
    PlaneableDetailSerializers)
from rest_framework.decorators import api_view
from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from django.http import Http404, HttpResponseBadRequest
from django.db.models.fields import TextField


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


FIELD_TEMPLATE = Template('''
<div class="form-group>
  <label for="name">$userfield</label>
  <input type="$fieldtype" class="form-control" id="$field" ng-model="$varname.$field">
</div>
''')

TEXTAREA_TEMPLATE = Template('''
<div class="form-group>
  <label for="name">$userfield</label>
  <textarea class="form-control" id="$field"  ng-model="$varname.$field" rows=4></textarea>
</div>
''')

SELECTION_TEMPLATE = Template('''
<div class="form-group>
  <label for="priority">$userfield</label>
  <select ng-model="$varname.$field" ng-options="name for name in $option_source"></select>
</div>
''')


def createField(varname, fieldname, fieldtype, option_source=None):
    if fieldtype == 'text':
        return TEXTAREA_TEMPLATE.substitute({'userfield':fieldname.title(),
                                      'field':fieldname,
                                      'varname':varname})
    if fieldtype == 'select':
        return SELECTION_TEMPLATE.substitute({'userfield':fieldname.title(),
                                      'field':fieldname,
                                      'varname':varname,
                                      'option_source':option_source})
    return FIELD_TEMPLATE.substitute({'userfield':fieldname.title(),
                                      'field':fieldname,
                                      'varname':varname,
                                      'fieldtype':fieldtype})


class EditorTemplatesGenerator:
    WINDOW_TEMPLATE = Template('''
<div class="modal-header">
<h3 class="modal-title">$title</h3>
</div><form role="form">
$form
<div class="modal-footer">
  <button class="btn btn-primary" ng-click="ok()">OK</button>
  <button class="btn btn-warning" ng-click="cancel()">Cancel</button>
</div></form>
    ''')

    SYSTEM_TEMPLATE = WINDOW_TEMPLATE.substitute({
        'title':'Model Details',
        'form': createField('system', 'name', '') + \
                createField('system', 'description', 'text')
    })

    # TODO: Add attachements, xrefs and statuschanges to this editor.
    PLANEABLE_FIELDS = createField('item', 'name', '') + \
                createField('item', 'description', 'text') +\
                createField('item', 'priority', 'select', '$root.priorities')

    ITEM_TEMPLATE = WINDOW_TEMPLATE.substitute({
        'title':'Planeable Details',
        'form': PLANEABLE_FIELDS
    })
    REQ_TEMPLATE = WINDOW_TEMPLATE.substitute({
        'title':'Requirement Details',
        'form': PLANEABLE_FIELDS + createField('item', 'reqtype', 'select', '$root.reqTypes')
    })
    PROJ_TEMPLATE = WINDOW_TEMPLATE.substitute({
        'title':'Project Details',
        'form': PLANEABLE_FIELDS + \
                createField('item', 'start', 'date') +\
                createField('item', 'finish', 'date') +\
                createField('item', 'budget', 'money')
    })
    BUG_TEMPLATE = WINDOW_TEMPLATE.substitute({
        'title':'Bug Details',
        'form': PLANEABLE_FIELDS + \
                createField('item', 'reportedby', '$scope.users')
    })
    ACTION_TEMPLATE = WINDOW_TEMPLATE.substitute({
        'title':'Action Details',
        'form': PLANEABLE_FIELDS + \
                createField('item', 'isresponse', 'bool')
    })


    TEMPLATES = {'system': SYSTEM_TEMPLATE,
                 'item': ITEM_TEMPLATE,
                 'req': REQ_TEMPLATE,
                 'proj': PROJ_TEMPLATE,
                 'con': ITEM_TEMPLATE,
                 'action': ACTION_TEMPLATE,
                 'bug': BUG_TEMPLATE,
                 'view': ITEM_TEMPLATE}
    RESPONSES = {k: Response(t) for k, t in TEMPLATES.items()}


    @api_view(['GET'])
    def get_template(request, name):
        if name not in EditorTemplatesGenerator.RESPONSES:
            return HttpResponseBadRequest
        return EditorTemplatesGenerator.RESPONSES[name]




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

class ViewItemsView:
    pass


class WorkItemsView:
    pass


class PlanningView:
    pass
