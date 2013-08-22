import json
import ckan.model as model
import ckan.plugins as plugins
import ckan.logic as logic
import ckan.lib.helpers as h
import ckan.lib.create_test_data
import ckan.tests as tests

_create_test_data = ckan.lib.create_test_data.CreateTestData


def create_vocab(vocab_name, user_name):
    context = {'model': model, 'session': model.Session,
               'user': user_name}
    vocab = logic.get_action('vocabulary_create')(
        context, {'name': vocab_name}
    )
    return vocab


def add_tag_to_vocab(tag_name, vocab_id, user_name):
    tag_schema = logic.schema.default_create_tag_schema()
    tag_schema['name'] = [unicode]
    context = {'model': model, 'session': model.Session,
               'user': user_name, 'schema': tag_schema}
    tag = {'name': tag_name,
           'vocabulary_id': vocab_id}
    logic.get_action('tag_create')(context, tag)


class TestAPI(tests.WsgiAppCase):
    @classmethod
    def setup_class(cls):
        _create_test_data.create('publisher')
        model.repo.new_revision()

        usr = model.User(name="ectest", apikey="ectest", password=u'ectest')
        model.Session.add(usr)
        model.Session.commit()

        g = model.Group.get('david')
        g.type = 'organization'
        model.Session.add(g)

        p = model.Package.get('warandpeace')
        mu = model.Member(table_id=usr.id, table_name='user', group=g)
        mp = model.Member(table_id=p.id, table_name='package', group=g)
        model.Session.add(mu)
        model.Session.add(mp)
        model.Session.commit()

        cls.sysadmin_user = model.User.get('testsysadmin')

        status = create_vocab(u'status', cls.sysadmin_user.name)
        add_tag_to_vocab(u'http://purl.org/adms/status/Completed',
                         status['id'], cls.sysadmin_user.name)

        plugins.load('ecportal')

    @classmethod
    def teardown_class(cls):
        model.repo.rebuild_db()
        plugins.unload('ecportal')

    def test_package_rdf_create_ns_update(self):
        rdf = ('<rdf:RDF '
               'xmlns:foaf="http://xmlns.com/foaf/0.1/" '
               'xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" '
               'xmlns:dct="http://purl.org/dc/terms/" '
               'xmlns:dcat="http://www.w3.org/ns/dcat#"> '
               '<dcat:Dataset rdf:about="http://localhost"></dcat:Dataset> '
               '</rdf:RDF>')
        dataset_json = json.dumps({
            'name': u'rdfpackage2',
            'title': u'RDF Package2',
            'description': u'RDF package 2 description',
            'url': u'http://datahub.io',
            'published_by': u'david',
            'status': u'http://purl.org/adms/status/Completed',
            'rdf': rdf
        })
        response = self.app.post('/api/action/package_create',
                                 params=dataset_json,
                                 extra_environ={'Authorization': 'ectest'})
        dataset = json.loads(response.body)['result']
        assert 'dcat=' in dataset['rdf']

        # Fetch RDF page
        response = self.app.get(h.url_for(
            controller='package', action='read', id='rdfpackage2'
        ) + ".rdf")
        assert '/dataset/rdfpackage2' in response.body, response.body

    def test_package_rdf_create_ns_new(self):
        rdf = ('<rdf:RDF '
               'xmlns:foaf="http://xmlns.com/foaf/0.1/" '
               'xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" '
               'xmlns:dcat="http://www.w3.org/ns/dcat#"> '
               '<dcat:Dataset rdf:about="http://localhost"></dcat:Dataset> '
               '</rdf:RDF>')
        dataset_json = json.dumps({
            'name': u'rdfpackage1',
            'title': u'RDF Package1',
            'description': u'RDF package 2 description',
            'url': u'http://datahub.io',
            'published_by': u'david',
            'status': u'http://purl.org/adms/status/Completed',
            'rdf': rdf
        })
        response = self.app.post('/api/action/package_create',
                                 params=dataset_json,
                                 extra_environ={'Authorization': 'ectest'})
        dataset = json.loads(response.body)['result']
        assert 'dcat=' in dataset['rdf']

        # Fetch RDF page
        response = self.app.get(h.url_for(
            controller='package', action='read', id='rdfpackage1'
        ) + ".rdf")
        assert '/dataset/rdfpackage1' in response.body, response.body

    def test_keywords_create(self):
        tag = u'test-keyword'
        dataset_json = json.dumps({
            'name': u'test_keywords_dataset',
            'title': u'Test Keywords Dataset',
            'description': u'test description',
            'url': u'http://datahub.io',
            'published_by': u'david',
            'status': u'http://purl.org/adms/status/Completed',
            'keywords': [{u'name': tag}]
        })
        response = self.app.post('/api/action/package_create',
                                 params=dataset_json,
                                 extra_environ={'Authorization': 'ectest'})
        dataset = json.loads(response.body)['result']

        tags = [t['name'] for t in dataset['keywords']]
        assert len(tags) == 1
        assert tag in tags

    def test_keywords_update(self):
        params = json.dumps({'id': u'warandpeace'})
        response = self.app.post('/api/action/package_show', params=params)
        dataset = json.loads(response.body)['result']
        old_tags = dataset.pop('keywords')
        new_tag_names = [u'test-keyword1', u'test-keyword2']
        new_tags = old_tags + [{'name': name} for name in new_tag_names]
        dataset['keywords'] = new_tags
        dataset['description'] = u'test description'
        dataset['url'] = u'http://datahub.io'
        dataset['status'] = u'http://purl.org/adms/status/Completed'

        params = json.dumps(dataset)
        response = self.app.post('/api/action/package_update', params=params,
                                 extra_environ={'Authorization': 'ectest'})
        updated_dataset = json.loads(response.body)['result']

        old_tags = [tag['name'] for tag in old_tags]
        updated_tags = [tag['name'] for tag in updated_dataset['keywords']]

        for tag in old_tags:
            assert tag in updated_tags
        for tag in new_tag_names:
            assert tag in updated_tags

    def test_convert_publisher_to_groups(self):
        params = json.dumps({'id': u'warandpeace'})
        response = self.app.post('/api/action/package_show', params=params)
        dataset = json.loads(response.body)['result']
        assert dataset['published_by'] == u'david'

        dataset['description'] = u'test description'
        dataset['url'] = u'http://datahub.io'
        dataset['status'] = u'http://purl.org/adms/status/Completed'
        dataset['published_by'] = u'roger'
        params = json.dumps(dataset)
        response = self.app.post('/api/action/package_update', params=params,
                                 extra_environ={'Authorization': 'ectest'})
        updated_dataset = json.loads(response.body)['result']
        assert updated_dataset['published_by'] == u'david', updated_dataset

    def test_uppercase_names_allowed(self):
        dataset_json = json.dumps({
            'name': u'TEST-UPPERCASE-NAMES',
            'title': u'Test',
            'description': u'test description',
            'url': u'http://datahub.io',
            'published_by': u'david',
            'status': u'http://purl.org/adms/status/Completed',
        })
        self.app.post('/api/action/package_create',
                      params=dataset_json,
                      extra_environ={'Authorization': 'ectest'})

    def test_contact_name_required(self):
        dataset_json = json.dumps({
            'name': u'TEST-UPPERCASE-NAMES',
            'title': u'Test',
            'description': u'test description',
            'url': u'http://datahub.io',
            'published_by': u'david',
            'status': u'http://purl.org/adms/status/Completed',
            'contact_email': u'contact@email.com',
        })
        self.app.post('/api/action/package_create',
                      params=dataset_json,
                      extra_environ={'Authorization': 'ectest'},
                      status=409)

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

    def test_blank_license_allowed(self):
        dataset_json = json.dumps({
            'name': u'test-blank-license-string',
            'title': u'Test',
            'description': u'test description',
            'url': u'http://datahub.io',
            'published_by': u'david',
            'status': u'http://purl.org/adms/status/Completed',
            'contact_email': u'contact@email.com',
            'license_id': u''
        })
        self.app.post('/api/action/package_create',
                      params=dataset_json,
                      extra_environ={'Authorization': 'ectest'},
                      status=409)

        dataset_json = json.dumps({
            'name': u'test-blank-license-list',
            'title': u'Test',
            'description': u'test description',
            'url': u'http://datahub.io',
            'published_by': u'david',
            'status': u'http://purl.org/adms/status/Completed',
            'contact_email': u'contact@email.com',
            'license_id': []
        })
        self.app.post('/api/action/package_create',
                      params=dataset_json,
                      extra_environ={'Authorization': 'ectest'},
                      status=409)
