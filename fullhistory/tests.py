import unittest

from django.test import TestCase
from django.test.client import Client
from django.core import urlresolvers
from django.contrib.auth.models import User #this app requires auth, so we can do tests against it
from django.contrib.auth.admin import UserAdmin
from django.contrib import admin

from models import *
from fullhistory import register_model

class FullHistoryTest(TestCase):
    
    def setUp(self):
        #overide user admin history_view
        UserAdmin.history_view = FullHistoryAdmin.history_view.im_func
        admin.autodiscover()
        register_model(User)

    def test_details(self):
        # Check for errors
        
        user = User(username='test', email='testemail@test.com', is_staff=True, is_superuser=True)
        user.set_password('test')
        user.save()
        
        user.email = 'foo@test.com'
        user.save()
        
        self.client.login(username='test', password='test')
        
        response = self.client.get('/admin/auth/user/%s/history/' % user.pk)
        self.assertEqual(200, response.status_code)
        self.assertNotEqual(response.content.find('changed from [testemail@test.com] to [foo@test.com]'), -1)

        foo_user = User(username='bar', email='testemail@test.com', id=user.pk)
        foo_user.save()
        
        user.delete()
        self.assertEqual(5, FullHistory.objects.actions_for_object(foo_user).count()) # 5 including the login time
        FullHistory.objects.audit(foo_user)
        
        #lets rollback to the 3rd version
        user = FullHistory.objects.rollback(foo_user, 3)
        self.assertEqual(6, FullHistory.objects.actions_for_object(user).count())
        FullHistory.objects.audit(user)
        self.assertEqual('test', user.username)
        
        FullHistory.objects.restore(User, user.pk)
        
        actions = FullHistory.objects.actions_for_object(user)
        first = actions[0]
        last = actions[len(actions)-1]
        first.next()
        last.previous()
        self.assertRaises(FullHistory.DoesNotExist, first.previous)
        self.assertRaises(FullHistory.DoesNotExist, last.next)
