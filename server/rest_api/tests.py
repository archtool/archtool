# -*- coding: utf-8
from django.test import TestCase
from rest_api import models
from django.utils import timezone
from decimal import Decimal


TXT = ''' Het is vereist
        dat dit zonder problemen laadt.
        check vreemde karakters: à propos, één, aperçut,  '''

# Create your tests here.
class ModelTestCases(TestCase):
    def setUp(self):
        # Create some generic objects to be used in other tests
        models.System.objects.create(name='test')
        models.User.objects.create(name='Evert', email='pietje.puk@axians.com',
                                   hourrate=Decimal('123.45'))

    def test_planeables(self):
        now = timezone.now()
        system = models.System.objects.get(name='test')

        # Create a planeable with default values
        models.Requirement.objects.create(
            name='Dit is een test',
            description=TXT,
            system=system
        )
        req = models.Requirement.objects.get(name='Dit is een test')
        self.assertEqual(req.system, system)
        self.assertEqual(req.priority, models.Priorities.must)
        self.assertEqual(req.reqtype, models.RequirementType.functional)
        self.assertEqual(req.description, TXT)
        self.assertGreaterEqual(req.created, now)

        # Try to create a child
        req2 = models.Requirement.objects.create(name='test2', system=system)
        req.children.add(req2)
        children = models.Requirement.objects.filter(parent=req)
        self.assertEqual(len(children), 1)

        # Try to create a cross-reference
        action = models.Action.objects.create(name='action', system=system)
        xtype = models.CrossrefType.objects.create(forwardname='defines', backwardname='implements')
        models.PlaneableXRef.objects.create(reftype=xtype, aitem=req, bitem=action)
        aitems = models.PlaneableItem.objects.filter(aitems=action)
        bitems = models.PlaneableItem.objects.filter(bitems=req)
        print()
        self.assertEqual(len(list(aitems)), 1)
        self.assertEqual(len(list(bitems)), 1)


