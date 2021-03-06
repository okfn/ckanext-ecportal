# -*- coding: UTF8 -*-
'''
**Notice**: Vim users please check the tests README file before
            editing this file.
'''
import json

import ckan.model as model
import ckan.lib.create_test_data
import ckan.lib.search as search
import ckan.tests as tests

import data
import test_api

_create_test_data = ckan.lib.create_test_data.CreateTestData


class TestSearch(tests.TestController):

    @classmethod
    def setup_class(cls):
        model.Session.remove()
        tests.setup_test_search_index()

        _create_test_data.create_arbitrary(data.ecportal_search_items)
        _create_test_data.create('publisher')

        cls.sysadmin_user = model.User.get('testsysadmin')
        cls.sysadmin_env = {'Authorization': str(cls.sysadmin_user.apikey)}

        model.repo.new_revision()

        usr = model.User(name="ectest", apikey="ectest", password=u'ectest')
        model.Session.add(usr)
        model.Session.commit()

        g = model.Group.get('david')
        g.type = 'organization'
        model.Session.add(g)

        mu = model.Member(table_id=usr.id, table_name='user', group=g)
        model.Session.add(mu)
        model.Session.commit()

        # create status vocab
        status = test_api.create_vocab(u'status', cls.sysadmin_user.name)
        test_api.add_tag_to_vocab(u'http://purl.org/adms/status/Completed',
                                  status['id'], cls.sysadmin_user.name)

        # create geographical coverage vocab
        cls.geo_tags = [(u'uk', u'United Kingdom'), (u'ie', u'Ireland')]
        geo = test_api.create_vocab(u'geographical_coverage',
                                    cls.sysadmin_user.name)
        cls.geo_vocab_id = geo['id']

        for tag in cls.geo_tags:
            test_api.add_tag_to_vocab(tag[0], cls.geo_vocab_id,
                                      cls.sysadmin_user.name)
            params = json.dumps({
                'term': tag[0],
                'term_translation': tag[1],
                'lang_code': u'en'
            })
            response = cls.app.post('/api/action/term_translation_update',
                                    params=params,
                                    extra_environ=cls.sysadmin_env)
            assert json.loads(response.body)['success']

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
        assert len(result['results']) == len(data.ecportal_search_items) + 2
        assert result['count'] == len(data.ecportal_search_items) + 2

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

    def test_facets(self):
        params = json.dumps({'id': u'warandpeace'})
        response = self.app.post('/api/action/package_show', params=params)
        dataset = json.loads(response.body)['result']

        dataset['description'] = u'test description'
        dataset['url'] = u'http://datahub.io'
        dataset['status'] = [u'http://purl.org/adms/status/Completed']
        dataset['geographical_coverage'] = [u'uk']

        params = json.dumps(dataset)
        response = self.app.post('/api/action/package_update', params=params,
                                 extra_environ={'Authorization': 'ectest'})

        params = json.dumps({
            'q': u'warandpeace',
            'facet.field': [u'vocab_geographical_coverage']
        })
        response = self.app.post('/api/action/package_search', params=params)
        facets = json.loads(response.body)['result']['search_facets']
        geo_facets = facets[u'vocab_geographical_coverage']['items']

        assert geo_facets[0]['count'] == 1
        assert geo_facets[0]['name'] == 'uk'

    def test_search_by_modified(self):
        # create a new dataset
        dataset = {'name': u'new-test-dataset',
                   'title': u'title',
                   'description': u'description',
                   'url': u'http://datahub.io',
                   'published_by': u'david',
                   'status': u'http://purl.org/adms/status/Completed'}
        self.app.post('/api/action/package_create',
                      params=json.dumps(dataset),
                      extra_environ={'Authorization': 'ectest'})

        # check that new dataset is first result when sorting by
        # modified_date (should default to same value as CKAN's
        # metadata_modified field)
        search_query = {'sort': 'modified_date desc'}
        response = self.app.post('/api/action/package_search',
                                 params=json.dumps(search_query),
                                 extra_environ={'Authorization': 'ectest'})
        result = json.loads(response.body)['result']
        assert result['count'] > 1
        assert result['results'][0]['name'] == dataset['name']

        # set the modified_date field to a time before the rest
        # of the datasets were created
        dataset['modified_date'] = u'2013-01-01'
        self.app.post('/api/action/package_update',
                      params=json.dumps(dataset),
                      extra_environ={'Authorization': 'ectest'})

        # check that dataset is now the first result when sorting
        # by modified_date (ascending)
        search_query = {'sort': 'modified_date asc'}
        response = self.app.post('/api/action/package_search',
                                 params=json.dumps(search_query),
                                 extra_environ={'Authorization': 'ectest'})
        result = json.loads(response.body)['result']
        assert result['count'] > 1
        assert result['results'][0]['name'] == dataset['name']
