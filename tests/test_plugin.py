import json
import ckanext.ecportal.plugin as plugin


class TestECPortalHomePlugin():

    config = {'ckan.home.content': 'data/home.json'}

    def test_read_json(self):
        p = plugin.ECPortalHomepagePlugin()
        p.configure(self.config)
        assert p.home_content

    def test_read_json_bad_json(self):
        p = plugin.ECPortalHomepagePlugin()
        p.configure({'ckan.home.content': __file__})
        assert not p.home_content

    def test_read_json_bad_file_path(self):
        p = plugin.ECPortalHomepagePlugin()
        p.configure({'ckan.home.content': 'badfilepath.json'})
        assert not p.home_content

    def test_homepage_content(self):
        with open(self.config['ckan.home.content'], 'r') as f:
            data = json.loads(f.read())
            p = plugin.ECPortalHomepagePlugin()
            p.configure(self.config)
            print data
            assert p.homepage_content('en')['title'] == data['title']['en']
            assert p.homepage_content('en')['body'] == data['body']['en']

    def test_homepage_content_bad_file_path(self):
        p = plugin.ECPortalHomepagePlugin()
        p.configure({'ckan.home.content': 'badfilepath.json'})
        assert not p.homepage_content('en')
