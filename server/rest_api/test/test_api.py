__author__ = 'ehwaal'

from rest_framework.test import APIRequestFactory
from django.core.urlresolvers import reverse
from django.test.testcases import TestCase
from rest_framework import status
from rest_framework.test import APITestCase
from rest_api import models


class ApiTests(APITestCase):
    base_system_data = dict(id=1, name='ABC', description='is a great project')
    @classmethod
    def setUpClass(cls):
        APITestCase.setUpClass()

        # Create some initial objects
        s = models.System(**cls.base_system_data)
        s.save()

    def setUp(self):
        self.factory = APIRequestFactory()


    def test_systems(self):
        # Test the List Create API
        response = self.client.get('/api/systems/', self.base_system_data,
                                   format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [self.base_system_data])

        data = {'name': 'DEF', 'description': 'also great'}
        response = self.client.post('/api/systems/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data['id'] = 2
        self.assertEqual(response.data, data)

        response = self.client.get('/api/systems/', data, format='json')
        self.assertEqual(len(response.data), 2)

        # Test the Retrieve
        response = self.client.get('/api/systems/2/', '', format='json')
        self.assertEqual(response.data, data)
        # TODO: Test the Retrieve for a non-existing object
        # Test the Update
        data = {'description': 'but not as great as ABC'}
        response = self.client.patch('/api/systems/2/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data['id'] = 2
        data['name'] = 'DEF'
        self.assertEqual(response.data, data)
        # Test the Delete
        response = self.client.delete('/api/systems/2/', '', format='json')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        # Check the List results again
        response = self.client.get('/api/systems/', '', format='json')
        self.assertEqual(response.data, [self.base_system_data])


    def test_list_priorities_etc(self):
        """ Test the getters for a number of lists of constants
        """
        response = self.client.get('/api/priorities/', '', format='json')
        self.assertEqual(response.data, models.Priorities.keys())
        response = self.client.get('/api/reqtypes/', '', format='json')
        self.assertEqual(response.data, models.RequirementType.keys())
        response = self.client.get('/api/planeabletypes/', '', format='json')
        self.assertEqual(response.data, models.PlaneableItem.get_types())


    def test_planeable_items(self):
        # Create a Requirement
        req1 = dict(name='First Requirement',
                    description='This is the first requirements of a large set',
                    system=1,
                    parent=None,
                    priority=2,
                    itemtype='req',
                    reqtype=3)
        response = self.client.post('/api/planeableitems/?system=1&itemtype=req', req1,
                                    format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        req1['id'] = 1
        req1['order'] = 0
        data = dict(req1)
        del response.data['created']  # Difficult to check the creation datetime.
        self.assertEqual(response.data, data)

        # List all requirements
        response = self.client.get('/api/planeableitems/?system=1&itemtype=req', '',
                                   format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # The list does not contain all fields: skip the unnecessary ones.
        del data['description']
        del data['priority']
        del data['reqtype']
        for p in models.Requirement.objects.all():
            print (p)
        self.assertEqual(response.data, [data])

        # Retrieve a Requirement
        response = self.client.get('/api/planeableitems/1/?itemtype=req', '',
                                   format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        del response.data['created']  # Difficult to check the creation datetime.
        self.assertEqual(response.data, req1)

        # Update a Requirement
        req1['name'] = 'Last Requirement'
        response = self.client.patch('/api/planeableitems/1/?itemtype=req',
                                     {'name':req1['name']},
                                     format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        del response.data['created']  # Difficult to check the creation datetime.
        self.assertEqual(response.data, req1)
        response = self.client.get('/api/planeableitems/1/?itemtype=req', '',
                                   format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        del response.data['created']  # Difficult to check the creation datetime.
        self.assertEqual(response.data, req1)

        # Delete a Requirement
        response = self.client.delete('/api/planeableitems/1/?itemtype=req', '', format='json')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Check it is gone
        response = self.client.get('/api/planeableitems/1/?itemtype=req', '',
                                   format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        response = self.client.get('/api/planeableitems/?itemtype=req&system=1', '',
                                   format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])


        # Create a view
        view1 = dict(name='First Requirement',
                     description='Project Plan',
                     system=1,
                     parent=None,
                     priority=2,
                     itemtype='view')
        response = self.client.post('/api/planeableitems/?system=1&itemtype=view', view1,
                                    format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        view1['id'] = 2
        view1['order'] = 0
        data = dict(view1)
        del response.data['created']  # Difficult to check the creation datetime.
        self.assertEqual(response.data, data)

        # Check the lists for items, projects and requirements
        response = self.client.get('/api/planeableitems/?itemtype=item&system=1', '',
                                   format='json')
        self.assertEqual(len(response.data), 1)
        response = self.client.get('/api/planeableitems/?itemtype=req&system=1', '',
                                   format='json')
        self.assertEqual(len(response.data), 0)
        response = self.client.get('/api/planeableitems/?itemtype=view&system=1', '',
                                   format='json')
        self.assertEqual(len(response.data), 1)

        # Delete the view to bring the database back in its original state
        response = self.client.delete('/api/planeableitems/2/?itemtype=view', '', format='json')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_statuschanges(self):
        """ Test adding status changes to a planeable.
        """
        # Create a planeable
        req1 = dict(name='First Requirement',
                    description='This is the first requirements of a large set',
                    system=1,
                    parent=None,
                    priority=2,
                    itemtype='req',
                    reqtype=3)
        response = self.client.post('/api/planeableitems/?system=1&itemtype=req', req1,
                                    format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        req1.update(response.data)

        # Add a statuschange
        stat1 = dict(planeable=req1['id'],
                     description='testing',
                     status=1)
        response = self.client.post('/api/planeablestatuslist/%s/'%req1['id'], stat1,
                                    format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        stat1['timestamp'] = response.data['timestamp']
        stat1['timespent'] = None
        stat1['timeremaining'] = None
        stat1['id'] = 1
        self.assertEqual(response.data, stat1)
        # Add another statuschange with more details
        # The planeable field is deduced from the URL.
        # TODO: Add a user id
        stat2 = dict(description='made an estimate',
                     status=2,
                     timespent=1.3,
                     timeremaining=3.4)
        response = self.client.post('/api/planeablestatuslist/%s/'%req1['id'], stat2,
                                    format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        stat2['timestamp'] = response.data['timestamp']
        stat2['id'] = 2
        stat2['planeable'] = 1
        self.assertEqual(response.data, stat2)

        # List the status changes
        response = self.client.get('/api/planeablestatuslist/%s/'%req1['id'], '',
                                    format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [stat1, stat2])

        # Get the details for a status change
        response = self.client.get('/api/planeablestatusdetails/2/', '',
                                    format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, stat2)

        # Throw away the planeable
        response = self.client.delete('/api/planeableitems/1/?itemtype=req', '', format='json')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Check the status changes are gone as well
        response = self.client.get('/api/planeablestatuslist/%s/'%req1['id'], '',
                                    format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    def test_editors(self):
        """ Test the editor API. These calls either return JSON or a generated HTML
            form for that data, depending on some switch in the request.
            Two different cases exist: editing a planeable item and editing a system.
        """
        # TODO: Figure out which switch is to be set to generate the HTML form.
        # Get the editor for a new requirement
        response = self.client.get('/api/editors/?itemtype=req')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue('reqtype' in response.data)

        # Get the editor for an existing requirement
        req1 = dict(name='First Requirement',
                    description='This is the first requirements of a large set',
                    system=1,
                    parent=None,
                    priority=2,
                    itemtype='req',
                    reqtype=3)
        response = self.client.post('/api/planeableitems/?system=1&itemtype=req', req1,
                                    format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        req1.update(response.data)
        response = self.client.get('/api/editors/%s/?itemtype=req'%req1['id'])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, req1)

        # Get the editor for a new system
        response = self.client.get('/api/editors/?itemtype=system', '',
                                    format='html')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Get the editor for an existing system
        response = self.client.get('/api/editors/1/?itemtype=system', '',
                                    format='html')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, self.base_system_data)

    def test_view(self):
        # Create a view and other planeables that can serve as blocks, connections and actions.
        view = dict(name='View1', itemtype='view', system=1)
        block1 = dict(name='Camelot', itemtype='struct', system=1)
        block2 = dict(name='Aaargh', itemtype='struct', system=1)
        # The numbers are hard-coded references to block1 and conn
        conn   = dict(itemtype='xref', aitem=2, bitem=3)
        act1   = dict(name='search grail', itemtype='action', connection=2, system=1)
        act2   = dict(name='push pram', itemtype='action', connection=4, system=1)

        for details in [view, block1, block2, conn, act1, act2]:
            url = '/api/planeableitems/?system=1&itemtype=%s'%details['itemtype']
            if details == conn:
                url = '/api/planeablexrefs/?system=1'
            response = self.client.post(url, details,
                                        format='json')
            if response.status_code != status.HTTP_201_CREATED:
                pass
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            details.update(response.data)

        # Create representations for the blocks
        reprs = []
        for b in [block1, block2]:
            rep = dict(anchortype='block',
                       view=view['id'],
                       planeable=b['id'],
                       x=10, y=10, height=100, width=100, ismultiple=False)
            response = self.client.post('/api/viewitemdetails/block/', rep, format='json')
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            self.assertEqual(response.data['name'], b['name'])
            reprs.append(response.data)

        # Create a connection between the blocks and actions
        con = dict(anchortype='line',
                   view=view['id'],
                   start=reprs[0]['id'],
                   end=reprs[1]['id'],
                   connection=conn['id'])
        a1 = dict(anchortype='action',
                  action=act1['id'],
                  view=view['id'],
                  anchorpoint=reprs[0]['id'],
                  xoffset=0, yoffset=0)
        a2 = dict(anchortype='action',
                  action=act2['id'],
                  view=view['id'],
                  anchorpoint=reprs[1]['id']+1,
                  xoffset=0, yoffset=0)

        for details in [con, a1, a2]:
            url = '/api/viewitemdetails/%s/'%details['anchortype']
            print ('Trying to create', details)
            response = self.client.post(url, details, format='json')
            self.assertEqual(response.status_code, status.HTTP_201_CREATED,
                             'Not created %s %s'%(response.reason_phrase, response.data))
            # TODO: Test the name
            details.update(response.data)

        # TODO: add an annotation

        # And now, check if these details are given in the view list
        response = self.client.get('/api/viewitems/%s/'%view['id'], '', format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK,
                         'Error in request: %s %s'%(response.reason_phrase, response.data))

        self.assertEqual(response.data, dict(blocks = reprs,
                     connections = [con],
                     actions = [a1, a2],
                     annotations = []))

        # Check if we can create a second line and reuse the connection.
        con2 = dict(anchortype='line',
                    view=view['id'],
                    start=reprs[0]['id'],
                    end=reprs[1]['id'],
                    connection=None)
        response = self.client.post('/api/viewitemdetails/line/', con2, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED,
                         'Error in request: %s %s'%(response.reason_phrase, response.data))
        self.assertEqual(response.data['connection'], conn['id'])
