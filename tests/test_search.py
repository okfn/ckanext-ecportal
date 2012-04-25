# -*- coding: UTF8 -*-
'''
**Notice**: Vim users please check the tests README file before
            editing this file.
'''
from ckan import model
import ckan.lib.search as search

from ckan.tests import TestController, setup_test_search_index
from create_test_data import CreateTestData, ecportal_search_items


class TestSearch(TestController):

    @classmethod
    def setup_class(cls):
        model.Session.remove()
        setup_test_search_index()
        CreateTestData.create_ecportal_search_test_data(
            extra_core_fields=['description', 'status']
        )

    @classmethod
    def teardown_class(cls):
        model.repo.rebuild_db()
        search.clear()

    def _pkg_names(self, result):
        return ' '.join(result['results'])

    def _check_entity_names(self, result, names_in_result):
        names = result['results']
        for name in names_in_result:
            if name not in names:
                return False
        return True

    def _assert_one_package(self, result, name=None):
        assert result['count'] == 1, result
        if name:
            assert self._pkg_names(result) == name

    def test_general(self):
        result = search.query_for(model.Package).run({'q': '*:*'})
        assert result['results'], len(result['results']) == len(ecportal_search_items)
        assert result['count'] == len(ecportal_search_items), result['count']

    def test_non_latin_alphabet(self):
        # Search Greek word
        result = search.query_for(model.Package).run({'q': u'σιτηρό'})
        self._assert_one_package(result, u'test-greek')

    def test_special_characters_folding(self):
        # Search word with letter a with grave accent
        result = search.query_for(model.Package).run({'q': u'metropolità'})
        self._assert_one_package(result, u'test-catalan')

        # Search same word with letter a without accent
        result = search.query_for(model.Package).run({'q': u'metropolita'})
        self._assert_one_package(result, u'test-catalan')

        # Search word with two special characters
        result = search.query_for(model.Package).run({'q': u'pražských'})
        self._assert_one_package(result, u'test-czech')

        # Search same word with just one special character
        result = search.query_for(model.Package).run({'q': u'prazských'})
        self._assert_one_package(result, u'test-czech')

        # Search uppercase word with accents
        result = search.query_for(model.Package).run({'q': u'SVĚTOVÁ'})
        self._assert_one_package(result, u'test-czech')

        # Search same uppercase word without accents
        result = search.query_for(model.Package).run({'q': u'SVETOVA'})
        self._assert_one_package(result, u'test-czech')

        # Search greek word with accent
        result = search.query_for(model.Package).run({'q': u'ηπειρωτικές'})
        self._assert_one_package(result, u'test-greek')

        # Search same greek word without accents: folding does not work
        result = search.query_for(model.Package).run({'q': u'ηπειρωτικες'})
        assert result['count'] == 0, result
