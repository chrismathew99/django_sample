```python
from __future__ import unicode_literals

import unittest

from django import VERSION as DJANGO_VERSION
from django.core.exceptions import ValidationError
from django.test import TestCase
from tests.models import Band, BandMember, Album, Restaurant, Article, Author, Document, Gallery, Song
from modelcluster.forms import ClusterForm
from django.forms import Textarea, CharField
from django.forms.widgets import TextInput, FileInput
from django.utils.safestring import SafeString

import datetime


class ClusterFormTest(TestCase):
    def test_cluster_form_with_no_formsets(self):
        class BandForm(ClusterForm):
            class Meta:
                model = Band
                fields = ['name']

        self.assertFalse(BandForm.formsets)

        beatles = Band(name='The Beatles')
        form = BandForm(instance=beatles)
        form_html = form.as_p()
        self.assertIsInstance(form_html, SafeString)
        self.assertInHTML('<label for="id_name">Name:</label>', form_html)
        self.assertInHTML('<label for="id_albums-0-name">Name:</label>', form_html, count=0)

    def test_cluster_form(self):
        class BandForm(ClusterForm):
            class Meta:
                model = Band
                fields = ['name']
                formsets = ['members', 'albums']

        self.assertTrue(BandForm.formsets)

        beatles = Band(name='The Beatles', members=[
            BandMember(name='John Lennon'),
            BandMember(name='Paul McCartney'),
        ])

        form = BandForm(instance=beatles)

        self.assertEqual(5, len(form.formsets['members'].forms))
        form_html = form.as_p()
        self.assertIsInstance(form_html, SafeString)
        self.assertInHTML('<label for="id_name">Name:</label>', form_html)
        self.assertInHTML('<label for="id_albums-0-name">Name:</label>', form_html)

    def test_empty_cluster_form(self):
        class BandForm(ClusterForm):
            class Meta:
                model = Band
                fields = ['name']
                formsets = ['members', 'albums']

        form = BandForm()

        self.assertEqual(3, len(form.formsets['members'].forms))

    def test_incoming_form_data(self):
        class BandForm(ClusterForm):
            class Meta:
                model = Band
                fields = ['name']
                formsets = ['members', 'albums']

        beatles = Band(name='The Beatles', members=[
            BandMember(name='George Harrison'),
        ])
        form = BandForm({
            'name': "The Beatles",

            'members-TOTAL_FORMS': 4,
            'members-INITIAL_FORMS': 1,
            'members-MAX_NUM_FORMS': 1000,

            'members-0-name': 'George Harrison',
            'members-0-DELETE': 'members-0-DELETE',
            'members-0-id': '',

            'members-1-name': 'John Lennon',
            'members-1-id': '',

            'members-2-name': 'Paul McCartney',
            'members-2-id': '',

            'members-3-name': '',
            'members-3-id': '',

            'albums-TOTAL_FORMS': 0,
            'albums-INITIAL_FORMS': 0,
            'albums-MAX_NUM_FORMS': 1000,
        }, instance=beatles)

        self.assertTrue(form.is_valid())
        result = form.save(commit=False)
        self.assertEqual(result, beatles)

        self.assertEqual(2, beatles.members.count())
        self.assertEqual('John Lennon', beatles.members.all()[0].name)

        # should not exist in the database yet
        self.assertFalse(BandMember.objects.filter(name='John Lennon').exists())

        beatles.save()
        # this should create database entries
        self.assertTrue(Band.objects.filter(name='The Beatles').exists())
        self.assertTrue(BandMember.objects.filter(name='John Lennon').exists())

    def test_explicit_formset_list(self):
        class BandForm(ClusterForm):
            class Meta:
                model = Band
                formsets = ('members',)
                fields = ['name']

        form = BandForm()
        self.assertTrue(form.formsets.get('members'))
        self.assertFalse(form.formsets.get('albums'))

        self.assertTrue('members' in form.as_p())
        self.assertFalse('albums' in form.as_p())

    def test_excluded_formset_list(self):
        class BandForm(ClusterForm):
            class Meta:
                model = Band
                exclude_formsets = ('albums',)
                fields = ['name']

        form = BandForm()
        self.assertTrue(form.formsets.get('members'))
        self.assertFalse(form.formsets.get('albums'))

        self.assertTrue('members' in form.as_p())
        self.assertFalse('albums' in form.as_p())

    def test_widget_overrides(self):
        class BandForm(ClusterForm):
            class Meta:
                model = Band
                widgets = {
                    'name': Textarea(),
                    'members': {
                        'name': Textarea()
                    }
                }
                fields = ['name']
                formsets = ['members', 'albums']

        form = BandForm()
        self.assertEqual(Textarea, type(form['name'].field.widget))
        self.assertEqual(Textarea, type(form.formsets['members'].forms[0]['name'].field.widget))

    def test_explicit_formset_dict(self):
        class BandForm(ClusterForm):
            class Meta:
                model = Band
                formsets = {
                    'albums': {'fields': ['name'], 'widgets': {'name': Textarea()}}
                }
                fields = ['name']

        form = BandForm()
        self.assertTrue(form.formsets.get('albums'))
        self.assertFalse(form.formsets.get('members'))

        self.assertTrue('albums' in form.as_p())
        self.assertFalse('members' in form.as_p())

        self.assertIn('name', form.formsets['albums'].forms[0].fields)
        self.assertNotIn('release_date', form.formsets['albums'].forms[0].fields)
        self.assertEqual(Textarea, type(form.formsets['albums'].forms[0]['name'].field.widget))

    def test_without_kwarg_inheritance(self):
        # by default, kwargs passed to the ClusterForm do not propagate to child forms
        class BandForm(ClusterForm):
            class Meta:
                model = Band
                formsets = {
                    'members': {'fields': ['name']}
                }
                fields = ['name']

        form = BandForm(label_suffix="!!!:")
        form_html = form.as_p()
        # band name field should have label_suffix applied
        self.assertInHTML('<label for="id_name">Name!!!:</label>', form_html)
        # but this should not propagate to member form fields
        self.assertInHTML('<label for="id_members-0-name">Name!!!:</label>', form_html, count=0)

    def test_with_kwarg_inheritance(self):
        # inherit_kwargs should allow kwargs passed to the ClusterForm to propagate to child forms
        class BandForm(ClusterForm):
            class Meta:
                model = Band
                formsets = {
                    'members': {'fields': ['name'], 'inherit_kwargs': ['label_suffix']}
                }
                fields = ['name']

        form = BandForm(label_suffix="!!!:")
        form_html = form.as_p()
        # band name field should have label_suffix applied
        self.assertInHTML('<label for="id_name">Name!!!:</label>', form_html)
        # and this should propagate to member form fields too
        self.assertInHTML('<label for="id_members-0-name">Name!!!:</label>', form_html)

        # the form should still work without a label_suffix kwarg
        form = BandForm()
        form_html = form.as_p()
        self.assertInHTML('<label for="id_name">Name:</label>', form_html)
        self.assertInHTML('<label for="id_members-0-name">Name:</label>', form_html)

    def test_custom_formset_form(self):
        class AlbumForm(ClusterForm):
            pass

        class BandForm(ClusterForm):
            class Meta:
                model = Band
                formsets = {
                    'albums': {'fields': ['name'], 'form': AlbumForm}
                }
                fields = ['name']

        form = BandForm()
        self.assertTrue(isinstance(form.formsets.get("albums").forms[0], AlbumForm))

    def test_alternative_formset_name(self):
        """Support specifying a formset_name that differs from the relation"""
        class BandForm(ClusterForm):
            class Meta:
                model = Band
                formsets = {
                    'albums': {'fields': ['name'], 'formset_name': 'records'}
                }
                fields = ['name']

        form = BandForm({
            'name': "The Beatles",

            'records-TOTAL_FORMS': 1,
            'records-INITIAL_FORMS': 0,
            'records-MAX_NUM_FORMS': 1000,

            'records-0-name': 'Please Please Me',
            'records-0-id': '',
        })

        self.assertTrue(form.is_valid())
        result = form.save(commit=False)
        self.assertEqual(result.albums.first().name, 'Please Please Me')

    def test_formfield_callback(self):

        def formfield_for_dbfield(db_field, **kwargs):
            # a particularly stupid formfield_callback that just uses Textarea for everything
            return CharField(widget=Textarea, **kwargs)

        class BandFormWithFFC(ClusterForm):
            formfield_callback = formfield_for_dbfield

            class Meta:
                model = Band
                fields = ['name']
                formsets = ['members', 'albums']
                if DJANGO_VERSION >= (4, 2):
                    formfield_callback = formfield_for_dbfield

        form = BandFormWithFFC()
        self.assertEqual(Textarea, type(form['name'].field.widget))
        self.assertEqual(Textarea, type(form.formsets['members'].forms[0]['name'].field.widget))

    def test_saved_items(self):
        class BandForm(ClusterForm):
            class Meta:
                model = Band
                fields = ['name']
                formsets = ['members', 'albums']

        john = BandMember(name='John Lennon')
        paul = BandMember(name='Paul McCartney')
        beatles = Band(name='The Beatles', members=[john, paul])
        beatles.save()
        self.assertTrue(john.id)
        self.assertTrue(paul.id)

        form = BandForm({
            'name': "The New Beatles",

            'members-TOTAL_FORMS': 4,
            'members-INITIAL_FORMS': 2,
            'members-MAX_NUM_FORMS': 1000,

            'members-0-name': john.name,
            'members-0-DELETE': 'members-0-DELETE',
            'members-0-id': john.id,

            'members-1-name': paul.name,
            'members-1-id': paul.id,

            'members-2-name': 'George Harrison',
            'members-2-id': '',

            'members-3-name': '',
            'members-3-id': '',

            'albums-TOTAL_FORMS': 0,
            'albums-INITIAL_FORMS': 0,
            'albums-MAX_NUM_FORMS': 1000,
        }, instance=beatles)
        self.assertTrue(form.is_valid())
        form.save()

        new_beatles = Band.objects.get(id=beatles.id)
        self.assertEqual('The New Beatles', new_beatles.name)
        self.assertTrue(BandMember.objects.filter(name='George Harrison').exists())
        self.assertFalse(BandMember.objects.filter(name='John Lennon').exists())

    def test_cannot_omit_explicit_formset_from_submission(self):
        """
        If an explicit `formsets` parameter has been given, formsets missing from a form submission
        should raise a ValidationError as normal
        """
        class BandForm(ClusterForm):
            class Meta:
                model = Band
                fields = ['name']
                formsets = ['members', 'albums']

        john = BandMember(name='John Lennon')
        paul = BandMember(name='Paul McCartney')
        abbey_road = Album(name='Abbey Road')
        beatles = Band(name='The Beatles', members=[john, paul], albums=[abbey_road])
        beatles.save()

        form = BandForm({
            'name': "The Beatles",

            'members-TOTAL_FORMS': 3,
            'members-INITIAL_FORMS': 2,
            'members-MAX_NUM_FORMS': 1000,

            'members-0-name': john.name,
            'members-0-DELETE': 'members-0-DELETE',
            'members-0-id': john.id,

            'members-1-name': paul.name,
            'members-1-id': paul.id,

            'members-2-name': 'George Harrison',
            'members-2-id': '',
        }, instance=beatles)

        if DJANGO_VERSION >= (3, 2):
            # in Django >=3.2, a missing ManagementForm gives a validation error rather than an exception
            self.assertFalse(form.is_valid())
        else:
            with self.assertRaises(ValidationError):
                form.is_valid()

    def test_saved_items_with_non_db_relation(self):
        class BandForm(ClusterForm):
            class Meta:
                model = Band
                fields = ['name']
                formsets = ['members', 'albums']

        john = BandMember(name='John Lennon')
        paul = BandMember(name='Paul McCartney')
        beatles = Band(name='The Beatles', members=[john, paul])
        beatles.save()

        # pack and unpack the record so that we're working with a non-db-backed queryset
        new_beatles = Band.from_json(beatles.to_json())

        form = BandForm({
            'name': "The New Beatles",

            'members-TOTAL_FORMS': 4,
            'members-INITIAL_FORMS': 2,
            'members-MAX_NUM_FORMS': 1000,

            'members-0-name': john.name,
            'members-0-DELETE': 'members-0-DELETE',
            'members-0-id': john.id,

            'members-1-name': paul.name,
            'members-1-id': paul.id,

            'members-2-name': 'George Harrison',
            'members-2-id': '',

            'members-3-name': '',
            'members-3-id': '',

            'albums-TOTAL_FORMS': 0,
            'albums-INITIAL_FORMS': 0,
            'albums-MAX_NUM_FORMS': 1000,
        }, instance=new_beatles)
        self.assertTrue(form.is_valid())
        form.save()

        new_beatles = Band.objects.get(id=beatles.id)
        self.assertEqual('The New Beatles', new_beatles.name)
        self.assertTrue(BandMember.objects.filter(name='George Harrison').exists())
        self.assertFalse(BandMember.objects.filter(name='John Lennon').exists())

    def test_creation(self):
        class BandForm(ClusterForm):
            class Meta:
                model = Band
                fields = ['name']
                formsets = ['members', 'albums']

        form = BandForm({
            'name': "The Beatles",

            'members-TOTAL_FORMS': 4,
            'members-INITIAL_FORMS': 0,
            'members-MAX_NUM_FORMS': 1000,

            'members-0-name': 'John Lennon',
            'members-0-id': '',

            'members-1-name': 'Paul McCartney',
            'members-1-id': '',

            'members-2-name': 'Pete Best',
            'members-2-DELETE': 'members-0-DELETE',
            'members-2-id': '',

            'members-3-name': '',
            'members-3-id': '',

            'albums-TOTAL_FORMS': 0,
            'albums-INITIAL_FORMS': 0,
            'albums-MAX_NUM_FORMS': 1000,
        })
        self.assertTrue(form.is_valid())
        beatles = form.save()

        self.assertTrue(beatles.id)
        self.assertEqual('The Beatles', beatles.name)
        self.assertEqual('The Beatles', Band.objects.get(id=beatles.id).name)
        self.assertEqual(2, beatles.members.count())
        self.assertTrue(BandMember.objects.filter(name='John Lennon').exists())
        self.assertFalse(BandMember.objects.filter(name='Pete Best').exists())

    def test_sort_order_is_output_on_form(self):
        class BandForm(ClusterForm):
            class Meta:
                model = Band
                fields = ['name']
                formsets = ['members', 'albums']

        form = BandForm()
        form_html = form.as_p()
        self.assertTrue('albums-0-ORDER' in form_html)
        self.assertFalse('members-0-ORDER' in form_html)

    def test_sort_order_is_committed(self):
        class BandForm(ClusterForm):
            class Meta:
                model = Band
                fields = ['name']
                formsets = ['members', 'albums']

        form = BandForm({
            'name': "The Beatles",

            'members-TOTAL_FORMS': 0,
            'members-INITIAL_FORMS': 0,
            'members-MAX_NUM_FORMS': 1000,

            'albums-TOTAL_FORMS': 2,
            'albums-INITIAL_FORMS': 0,
            'albums-MAX_NUM_FORMS': 1000,

            'albums-0-name': 'With The Beatles',
            'albums-0-id': '',
            'albums-0-ORDER': 2,

            'albums-0-songs-TOTAL_FORMS': 0,
            'albums-0-songs-INITIAL_FORMS': 0,
            'albums-0-songs-MAX_NUM_FORMS': 1000,

            'albums-1-name': 'Please Please Me',
            'albums-1-id': '',
            'albums-1-ORDER': 1,

            'albums-1-songs-TOTAL_FORMS': 0,
            'albums-1-songs-INITIAL_FORMS': 0,
            'albums-1-songs-MAX_NUM_FORMS': 1000,
        })
        self.assertTrue(form.is_valid())
        beatles = form.save()

        self.assertEqual('Please Please Me', beatles.albums.all()[0].name)
        self.assertEqual('With The Beatles', beatles.albums.all()[1].name)

    def test_ignore_validation_on_deleted_items(self):
        class BandForm(ClusterForm):
            class Meta:
                model = Band
                fields = ['name']
                formsets = ['members', 'albums']

        please_please_me = Album(name='Please Please Me', release_date=datetime.date(1963, 3, 22))
        beatles = Band(name='The Beatles', albums=[please_please_me])
        beatles.save()

        form = BandForm({
            'name': "The Beatles",

            'members-TOTAL_FORMS': 0,
            'members-INITIAL_FORMS': 0,
            'members-MAX_NUM_FORMS': 1000,

            'albums-TOTAL_FORMS': 1,
            'albums-INITIAL_FORMS': 1,
            'albums-MAX_NUM_FORMS': 1000,

            'albums-0-name': 'With The Beatles',
            'albums-0-release_date': '1963-02-31',  # invalid date
            'albums-0-id': please_please_me.id