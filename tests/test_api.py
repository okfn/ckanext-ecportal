import json
from ckan import model
from ckan import plugins
from ckan.tests import WsgiAppCase
from create_test_data import CreateTestData


class TestAPI(WsgiAppCase):
    @classmethod
    def setup_class(cls):
        CreateTestData.create()
        plugins.load('ecportal')

    @classmethod
    def teardown_class(cls):
        model.repo.rebuild_db()
        plugins.unload('ecportal')

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

        # TODO: update this when package_show is updated to go through schema
        # validators/converters, the dataset should have keywords instead
        # of tags here
        tags = [t['name'] for t in dataset['tags']]
        assert len(tags) == 1
        assert tag in tags

    def test_keywords_update(self):
        params = json.dumps({'id': u'warandpeace'})
        response = self.app.post('/api/action/package_show', params=params)
        dataset = json.loads(response.body)['result']

        # TODO: update this when package_show is updated to go through schema
        # validators/converters, the dataset should have keywords instead
        # of tags here
        new_tag = u'test-keyword'
        dataset['keywords'] = dataset['tags']
        old_tags = dataset.pop('tags')
        dataset['keywords'].append({'name': new_tag})

        params = json.dumps(dataset)
        response = self.app.post('/api/action/package_update', params=params,
                                 extra_environ={'Authorization': 'tester'})
        updated_dataset = json.loads(response.body)['result']

        old_tag_names = [tag['name'] for tag in old_tags]
        new_tag_names = [tag['name'] for tag in updated_dataset['tags']]

        for tag in old_tag_names:
            assert tag in new_tag_names
        assert new_tag in new_tag_names
