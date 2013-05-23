# -*- coding: utf8 -*-

try:
    import json
except ImportError:
    import simplejson as json
import urllib
from ckan import model
import ckan.tests as tests
from ckan import plugins
from ckan.lib.create_test_data import CreateTestData

test_data = [
    {
        'name':u'boolean1',
        'title':u'Boolean 1',
        'notes':u'one two three',
    },
    {
        'name':u'boolean2',
        'title':u'Boolean 2',
        'notes':u'four three two',
    },
    {
        'name':u'boolean3',
        'title':u'Boolean 3',
        'notes':u'two three four five',
    },
]

class TestSearchBoolean(tests.TestController):

    @classmethod
    def setup_class(cls):
        model.repo.new_revision()
        tests.setup_test_search_index()
        CreateTestData.create_arbitrary(test_data)
        CreateTestData.create_groups(
            [
                {
                    'name': 'publisher1',
                    'packages': ['boolean1', 'boolean2', 'boolean3'],
                }
            ],
        )
        model.Session.commit()
        # Plugins
        for plugin in [
            'ecportal',
            'ecportal_form',
            'ecportal_publisher_form',
            'ecportal_controller',
        ]:
            plugins.load(plugin)

    @classmethod
    def teardown_class(cls):
        # Plugins
        plugins.reset()

    def assert_radio_buttons(self, checked='all'):
        others = ['all', 'any', 'exact']
        others.pop(others.index(checked))
        for url in [
            tests.url_for(controller='group', action='read', id='publisher1'),
            tests.url_for('home'),
            tests.url_for(controller='package', action='search'),
        ]:
            res = self.app.get(url)
            self.assert_equal("Show results with" in res, True)
            self.assert_equal(
                'value="%s" checked="checked" />'%(
                    checked,
                ) in res,
                True
            )
            for other in others:
                self.assert_equal('value="%s" />'%(other) in res, True)

    def assert_dataset_search_results(self, ext_boolean, q, results):
        others = ['Boolean 1', 'Boolean 2', 'Boolean 3']
        for result in results:
            others.pop(others.index(result))
        for url in [
            tests.url_for(controller='package', action='search'),
        ]:
            search_url=url+('?q='+urllib.quote(q)+'&ext_boolean='+urllib.quote_plus(ext_boolean))
            res = self.app.get(search_url)
            for result in results:
                self.assert_equal(result in res, True)
            for other in others:
                self.assert_equal(other not in res, True)

    def assert_publisher_search_results(self, ext_boolean, q, results):
        others = ['Boolean 1', 'Boolean 2', 'Boolean 3']
        for result in results:
            others.pop(others.index(result))
        for url in [
            tests.url_for(controller='group', action='read', id='publisher1'),
        ]:
            search_url=url+('?q='+urllib.quote(q)+'&ext_boolean='+urllib.quote_plus(ext_boolean))
            res = self.app.get(search_url)
            for result in results:
                self.assert_equal(result in res, True)
            for other in others:
                self.assert_equal(other not in res, True)

    def test_01_defaults_to_all_with_no_session(self):
        self.assert_radio_buttons(checked='all')

    def test_02_set_a_value_check_it_is_sticky(self):
        for ext_boolean in ['all', 'any', 'exact']:
            search_url = tests.url_for(
                controller='package',
                action='search',
            ) +'?q='+urllib.quote('Test')+'&ext_boolean='+urllib.quote(ext_boolean)
            # Do a search to set the session
            res = self.app.get(search_url)
            # Iterate the other URLs to check the are set to the new value
            self.assert_radio_buttons(checked=ext_boolean)

    def test_03_dataset_all(self):
        self.assert_dataset_search_results('all', 'one three', ['Boolean 1'])
        self.assert_dataset_search_results('all', 'four two', ['Boolean 2', 'Boolean 3'])

    def test_04_dataset_any(self):
        self.assert_dataset_search_results('any', 'one two three', ['Boolean 1', 'Boolean 2', 'Boolean 3'])
        self.assert_dataset_search_results('any', 'one five', ['Boolean 1', 'Boolean 3'])

    def test_05_dataset_exact(self):
        self.assert_dataset_search_results('exact', 'two three', ['Boolean 1', 'Boolean 3'])

    def test_06_publisher_list(self):
        search_url = tests.url_for(controller='group', action='read', id='publisher1')
        res = self.app.get(search_url)
        self.assert_equal('3 datasets' in res, True)
        for result in ['Boolean 1', 'Boolean 2', 'Boolean 3']:
            self.assert_equal(result in res, True)

    def test_07_publisher_all(self):
        self.assert_publisher_search_results('all', 'one three', ['Boolean 1'])
        self.assert_publisher_search_results('all', 'four two', ['Boolean 2', 'Boolean 3'])

    def test_08_publisher_any(self):
        self.assert_publisher_search_results('any', 'one two three', ['Boolean 1', 'Boolean 2', 'Boolean 3'])
        self.assert_publisher_search_results('any', 'one five', ['Boolean 1', 'Boolean 3'])

    def test_09_publisher_exact(self):
        self.assert_publisher_search_results('exact', 'two three', ['Boolean 1', 'Boolean 3'])

