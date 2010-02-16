import unittest

from django.test import TestCase
from django.test.client import Client, ClientHandler
from django.core import urlresolvers
from django.contrib.auth.models import User #this app requires auth, so we can do tests against it
from django.contrib import admin

from models import *
from admin import *
import fullhistory

import django
django1_1 = (django.VERSION[0] == 1 and django.VERSION[1] >= 1)

class Test1Model(models.Model):
    field1 = models.CharField(max_length=10)

    history = HistoryField()

class Test2Model(models.Model):
    field1 = models.FileField(upload_to="testup")
    
    history = HistoryField()

class Test3Model(models.Model):
    field1 = models.CharField(max_length=10)
    field2 = models.IntegerField(default=0)
    field3 = models.DateTimeField(auto_now=True)
    test2_fk = models.ForeignKey(Test2Model, null=True)
    test1_m2m = models.ManyToManyField(Test1Model)

class Test4Model(Test2Model):
    field2 = models.FloatField(default=0.0)

if django1_1:
    class TestProxyModel(Test1Model):
        class Meta:
            proxy = True


'''
try:
    fullhistory_admin.site.register(Test3Model, FullHistoryAdmin) 
except:
    pass
'''

class FullHistoryTest(TestCase):
    urls = 'fullhistory.test_urls'
    
    def setUp(self):
        if django1_1:
            fullhistory.register_model(TestProxyModel)
        fullhistory.register_model(Test4Model)
        fullhistory.register_model(Test3Model)
        fullhistory.register_model(Test2Model)
        fullhistory.register_model(Test1Model)
        
        user = User(username='test', email='testemail@test.com', is_staff=True, is_superuser=True)
        user.set_password('test')
        user.save()
        self.client.login(username='test', password='test')

    def test_proxy_signal(self):
        if not django1_1:
            return
        from django.db.models import signals
        def save_signal():
            raise Exception()
        signals.post_save.connect(save_signal, sender=TestProxyModel)
        tp = TestProxyModel(field1="test1")
        self.assertRaises(Exception, tp.save)

    def test_proxy(self):
        if not django1_1:
            return
        fullhistory.end_session()
        tp = TestProxyModel(field1="test1")
        tp.save()
        self.assertEquals(1, len(tp.history.all()))

    def test_inheritence(self):
        fullhistory.end_session()
        t4 = Test4Model(field1="test1", field2=-1)
        t4.save()
        for history in fullhistory.get_active_histories():
            if 'field1' in history.data:
                break
        else:
            self.fail("Did not find field1 in history")
        t4.field1 = "test1a"
        t4.save()
        t4 = Test4Model.objects.get(pk=t4.pk)
        t4.field2 = 0
        t4.save()
        t2 = Test2Model.objects.get(pk=t4.pk)
        t2.field1 = "test1b"
        t2.save()
        t4.delete()

    def test_inheritence_historyfield(self):
        fullhistory.end_session()
        t4 = Test4Model(field1="test1", field2=-1)
        t4.save()
        t4.field1 = "test1a"
        t4.save()
        t2 = Test2Model.objects.get(pk=t4.pk)
        self.assertTrue('field1' in t2.history.all().latest().data)
        try:
            self.assertTrue('field2' in t4.history.all().latest().data)
        except AssertionError:
            if django1_1:
                raise
            #known bug for Django 1.0, see ticket #9546

    def test_m2m_adjustments(self):
        fullhistory.end_session()
        t1a = Test1Model(field1="test")
        t1a.save()
        t3 = Test3Model(field1="testa", field2=5)
        t3.save()
        t3.test1_m2m.add(t1a)
        history = fullhistory.adjust_history(t3)
        self.assertNotEqual(None, history)
        self.assertTrue('test1_m2m' in history.data)
        self.assertEqual(1, len(history.data['test1_m2m']))
        self.assertEqual(history.data['test1_m2m'][0], [t1a.pk])
        fullhistory.end_session()
        t1b = Test1Model(field1="testb")
        t1b.save()
        t3.test1_m2m.add(t1b)
        history = fullhistory.adjust_history(t3)
        self.assertEqual(history.data['test1_m2m'][0], [t1a.pk])
        self.assertTrue(t1a.pk in history.data['test1_m2m'][1] and t1b.pk in history.data['test1_m2m'][1])
        self.assertEqual(2, len(FullHistory.objects.actions_for_object(t3)))

    def test_autofield_with_specified_obj(self):
        """
        This fails due to the combination of an auto field and specifying an id that already is in use
        Effectively we have no way of differing a record loaded from the database (which specifies an id)
        or a record that we manually specify.
        Another scenerio is creating specific object with an id and later setting another field before saving
        In general, we should not specify the id of an object without first loading it
        The alternative is to simply take a snapshot on save and not do differences
        this would be easier but its nice to know what people changed
        """
        fullhistory.end_session()
        t3 = Test3Model(field1="test1", field2=5)
        t3.save()
        t3a = Test3Model(field1="test2", field2=600, id=t3.pk)
        t3a.save()
        self.assertRaises(AssertionError, FullHistory.objects.audit, t3)

    def test_details(self):
        # Check for errors
        fullhistory.end_session()
        t3 = Test3Model(field1="test1", field2=5)
        t3.save()
        
        self.assertEqual(1, len(FullHistory.objects.actions_for_object(t3)))
        self.assertEqual('C', FullHistory.objects.actions_for_object(t3)[0].action)
        t3.field2 = 7
        t3.save()
        self.assertEqual('U', FullHistory.objects.actions_for_object(t3)[1].action)
        pk = t3.pk
        FullHistory.objects.audit(t3)
        t3.delete()
        
        self.assertEqual('D', FullHistory.objects.actions_for_object(model=Test3Model, pk=pk).reverse()[0].action)
        FullHistory.objects.audit(model=Test3Model, pk=pk)
        
        previous_revision = -1
        for history in FullHistory.objects.actions_for_object(model=Test3Model, pk=pk):
            self.assertEqual(previous_revision+1, history.revision)
            previous_revision = history.revision
        #lets rollback to the 3rd version
        t3 = FullHistory.objects.rollback(version=3, model=Test3Model, pk=pk)
        t3 = Test3Model.objects.get(pk=pk)
        FullHistory.objects.audit(t3)
        t3.delete()
        
        t3 = FullHistory.objects.rollback(model=Test3Model, pk=pk)
        t3 = Test3Model.objects.get(pk=pk)
        
        actions = FullHistory.objects.actions_for_object(t3)
        first = actions[0]
        last = actions[len(actions)-1]
        first.next()
        last.previous()
        self.assertRaises(FullHistory.DoesNotExist, first.previous)
        self.assertRaises(FullHistory.DoesNotExist, last.next)
        while True:
            try:
                previous = first
                first = first.next()
                self.assertNotEqual(first.pk, previous.pk)
            except FullHistory.DoesNotExist:
                self.assertEquals(first.pk, last.pk)
                break
    
    def test_django_admin(self):
        if not django1_1:
            return
        fullhistory.end_session()
        t3 = Test3Model(field1="foo")
        t3.save()
        t3.field2 = 5
        t3.save()
        
        base = '/admin/%s/%s/' % (Test3Model._meta.app_label, Test3Model._meta.module_name)
        response = self.client.get('%s%s/history/audit/' % (base, t3.pk))
        self.assertEqual(200, response.status_code)
        response = self.client.get('%s%s/history/version/1/' % (base, t3.pk))
        self.assertEqual(200, response.status_code)
        response = self.client.get('%s%s/history/version/256/' % (base, t3.pk))
        self.assertEqual(404, response.status_code)

