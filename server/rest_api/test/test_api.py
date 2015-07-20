__author__ = 'ehwaal'

from rest_framework.test import APIRequestFactory
from django.core.urlresolvers import reverse
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

