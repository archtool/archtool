__author__ = 'ehwaal'

from rest_framework.test import APIRequestFactory
from django.core.urlresolvers import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_api.models import System, Priorities



class ApiTests(APITestCase):
    base_system_data = dict(id=1, name='ABC', description='is a great project')
    @classmethod
    def setUpClass(cls):
        APITestCase.setUpClass()

        # Create some initial objects
        s = System(**cls.base_system_data)
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



    def test_list_priorities(self):
        response = self.client.get('/api/priorities/', '', format='json')
        self.assertEqual(response.data, Priorities.keys())

    def test_planeable_items(self):
        pass