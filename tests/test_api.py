import json
from ckan import model
from ckan import plugins
from ckan.tests import WsgiAppCase
from create_test_data import CreateTestData

try:
    import json
except:
    import simplejson as json


class TestAPI(WsgiAppCase):
    @classmethod
    def setup_class(cls):
        CreateTestData.create()
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
            'name' : u'rdfpackage',
            'title': u'RDF Package',
            'rdf'  : json.dumps(rdf)
        })
        response = self.app.post('/api/action/package_create',
                                 params=dataset_json,
                                 extra_environ={'Authorization': 'tester'})
        dataset = json.loads(response.body)['result']
        assert 'dct=' in dataset['rdf']

    def test_package_rdf_create_ns_new(self):
        rdf = ('<rdf:RDF '
               'xmlns:foaf="http://xmlns.com/foaf/0.1/" '
               'xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" '
               'xmlns:dcat="http://www.w3.org/ns/dcat#"> '
               '<dcat:Dataset rdf:about="http://localhost"></dcat:Dataset> '
               '</rdf:RDF>')
        dataset_json = json.dumps({
            'name' : u'rdfpackage',
            'title': u'RDF Package',
            'rdf'  : json.dumps(rdf)
        })
        response = self.app.post('/api/action/package_create',
                                 params=dataset_json,
                                 extra_environ={'Authorization': 'tester'})
        dataset = json.loads(response.body)['result']
        assert 'dct=' in dataset['rdf']


    def test_keywords_create(self):
        tag = u'test-keyword'
        dataset_json = json.dumps({
            'name': u'test_keywords_dataset',
            'title': u'Test Keywords Dataset',
            'description': u'test description',
            'keywords': [{u'name': tag}]
        })
        response = self.app.post('/api/action/package_create',
                                 params=dataset_json,
                                 extra_environ={'Authorization': 'tester'})
        dataset = json.loads(response.body)['result']

        tags = [t['name'] for t in dataset['keywords']]
        assert len(tags) == 1
        assert tag in tags

    def test_keywords_update(self):
        params = json.dumps({'id': u'warandpeace'})
        response = self.app.post('/api/action/package_show', params=params)
        dataset = json.loads(response.body)['result']

        old_tags = dataset.pop('keywords')
        new_tags = old_tags[:]
        new_tag = u'test-keyword'
        new_tags.append({'name': new_tag})
        dataset['keywords'] = new_tags

        params = json.dumps(dataset)
        response = self.app.post('/api/action/package_update', params=params,
                                 extra_environ={'Authorization': 'tester'})
        updated_dataset = json.loads(response.body)['result']

        old_tag_names = [tag['name'] for tag in old_tags]
        new_tag_names = [tag['name'] for tag in updated_dataset['keywords']]

        for tag in old_tag_names:
            assert tag in new_tag_names
        assert new_tag in new_tag_names
