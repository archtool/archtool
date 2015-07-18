__author__ = 'ehwaal'

from rest_framework.test import APIRequestFactory
from django.core.urlresolvers import reverse
from rest_framework import status
from rest_framework.test import APITestCase



class ApiTests(APITestCase):
    def test_list_systems(self):
        url = reverse('/api/systems')
        data = {}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, '[]')

