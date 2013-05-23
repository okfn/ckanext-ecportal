# -*- coding: utf8 -*-

import cgi
try:
    import json
except ImportError:
    import simplejson as json
import urllib
from ckan import model
import ckan.lib as lib
import ckan.lib.search as search
import ckan.tests as tests
import create_test_data as ctd
import test_api
import ckanext.ecportal.searchcloud as searchcloud
from ckan import plugins
from pylons import config
import paste.fixture
from ckan.config.middleware import make_app

def normalize_line_endings(text):
    return text.replace('\r\n', '\n').replace('\r', '\n')

expected_json = json.dumps(
    [
        {"text": "Health", "weight": 3},
        {"text": "Water<>&\"{}'", "weight": 2},
        {"text": u"Tax\u6c49\u5b57\u6f22\u5b57", "weight": 1}
    ]
)

class TestSearchCloud(tests.TestController):

    @classmethod
    def setup_class(cls):
        model.Session.remove()
        tests.setup_test_search_index()
        ctd.CreateTestData.create_ecportal_search_test_data()
        lib.create_test_data.CreateTestData.create('publisher')
        cls.sysadmin_user = model.User.get('testsysadmin')
        model.Session.commit()
        # Plugins
        for plugin in ['ecportal', 'ecportal_form', 'ecportal_publisher_form', 'ecportal_controller']:
            plugins.load(plugin)

    @classmethod
    def teardown_class(cls):
        model.repo.rebuild_db()
        search.clear()
        # Plugins
        plugins.reset()

    def test_00_no_tables(self):
        for table in ['search_query', 'search_popular_latest', 'search_popular_approved']:
            self.assert_equal(searchcloud.table_exists(model.Session, table), False)
        self.assert_equal(searchcloud.index_exists(model.Session, 'search_query', 'search_query_date'), False)

    def test_01_searchcloud_not_displayed_when_tables_are_missing(self):
        home_url = tests.url_for('home')
        res = self.app.get(home_url)
        self.assert_equal("Top Publishers" in res, True)
        self.assert_equal("jqcloud" not in res, True)

    def test_02a_searches_dont_fail_when_tables_are_missing(self):
        # Programatically (will raise an Exception if this doesn't work)
        result = search.query_for(model.Package).run({'q': '*:*'})
        self.assert_equal(result.get('count', 0) > 0, True)

    def test_02b_searches_dont_fail_when_tables_are_missing(self):
        # Via HTTP
        search_url = tests.url_for(controller='package', action='search') +'?q=Test'
        res = self.app.get(search_url)
        self.assert_equal("Test language English" in res, True)

    def test_03_install_searchcloud_tables(self):
        for table in ['search_query', 'search_popular_latest', 'search_popular_approved']:
            self.assert_equal(searchcloud.table_exists(model.Session, table), False)
        output = []
        def out(text):
            output.append(text)
        first_run = """\
Creating the search_query table ...
done.
Creating the search_popular_latest table ...
done.
Creating the search_popular_approved table ...
done.
Creating the search_query_date index ...
done."""
        searchcloud.install_tables(model.Session, out)
        self.assert_equal(output, normalize_line_endings(first_run).split('\n'))
        second_run = """\
The index already exists
The tables already exist"""
        while output:
            output.pop()
        searchcloud.install_tables(model.Session, out)
        self.assert_equal(output, normalize_line_endings(second_run).split('\n'))
        for table in ['search_query', 'search_popular_latest', 'search_popular_approved']:
            self.assert_equal(searchcloud.table_exists(model.Session, table), True)
        self.assert_equal(searchcloud.index_exists(model.Session, 'search_query', 'search_query_date'), True)
        model.Session.commit()

    def test_04_searchcloud_not_displayed_when_approved_table_is_empty(self):
        result = model.Session.execute('select count(*) from search_popular_approved').fetchall()[0][0]
        self.assert_equal(int(result), 0)
        home_url = tests.url_for('home')
        res = self.app.get(home_url)
        self.assert_equal("Top Publishers" in res, True)
        self.assert_equal("jqcloud" not in res, True)

    def test_05_searches_are_logged(self):
        for table in ['search_query', 'search_popular_latest', 'search_popular_approved']:
            self.assert_equal(searchcloud.table_exists(model.Session, table), True)
        self.assert_equal(searchcloud.index_exists(model.Session, 'search_query', 'search_query_date'), True)
        # Tables are in place, let's continue
        result = model.Session.execute('select count(*) from search_query').fetchall()[0][0]
        self.assert_equal(int(result), 0)
        # Perform some searches
        searches = ['Health', 'Health', 'Health', "Water<>&\"{}'", "Water<>&\"{}'", u'Tax\u6c49\u5b57\u6f22\u5b57']
        for term in searches:
            search_url = tests.url_for(controller='package', action='search') +'?q='+urllib.quote(term.encode('utf8'))
            res = self.app.get(search_url)
        # Now the query is logged
        result = model.Session.execute('select count(*) from search_query').fetchall()[0][0]
        self.assert_equal(int(result), 6)

    def test_06_searchcloud_displays_when_approved_data_present(self):
        # Put some data into the cloud
        searchcloud.generate_unapproved_list(model.Session, days=30)
        latest_rows = searchcloud.get_latest(model.Session)
        self.assert_equal(latest_rows, [[u'Health', 3L], [u"Water<>&\"{}'", 2L], [u'Tax\u6c49\u5b57\u6f22\u5b57', 1L]])
        searchcloud.update_approved(model.Session, latest_rows)
        approved_rows = searchcloud.get_approved(model.Session)
        self.assert_equal(latest_rows, approved_rows)
        # We'll use this test data later, so save it.
        model.Session.commit()
        # Test that the JSON text is what we expect.
        self.assert_equal(
            expected_json,
            searchcloud.approved_to_json(approved_rows)
        )
        # Now we should get a cloud
        home_url = tests.url_for('home')
        res = self.app.get(home_url)
        self.assert_equal(
            'var word_array = '+(cgi.escape(expected_json)) in res,
            True,
        )
        self.assert_equal('Popular terms' in res, True)
        self.assert_equal('jqcloud-1.0.4.min.js' in res, True)
        self.assert_equal('jqcloud.css' in res, True)
        self.assert_equal('<div id="searchcloud"' in res, True)

    def test_07_searches_are_made_uniform_correctly(self):
        # How should capitalization be taken into account? In the search itself?
        for search_string, expected in (
            # Simple case
            ['One Two', 'One Two'],
            # Leading and trailing space
            ['  One Two  ', 'One Two'],
            # Multiple spaces in words
            ['One   Two  Three', 'One Two Three'],
            # Over max length (one long word)
            ['One_Two_Three_Four', 'One_Two_Three_Fo'],
            # Over max length (multiple words)
            ['One Two Three Four', 'One Two Three'],
        ):
            self.assert_equal(
                searchcloud.unify_terms(search_string, max_length=16),
                expected
            )

    def test_08_updating_latest_table(self):
        # Check the sysadmin exists
        sysadmin = model.User.by_name(u'testsysadmin')
        self.assert_equal(sysadmin is not None, True)
        # Check that they can access the two versions of the index page
        for url in ['/searchcloud', '/searchcloud/']:
            res = self.app.get(url, status=200, extra_environ={'REMOTE_USER': 'testsysadmin'})
            self.assert_equal('/searchcloud/download' in res, True)
            self.assert_equal('/searchcloud/upload' in res, True)
        # Download a file
        res = self.app.get('/searchcloud/download', status=200, extra_environ={'REMOTE_USER': 'testsysadmin'})
        self.assert_equal(res.header_dict['Content-Disposition'.lower()].startswith('attachment'), True)
        self.assert_equal(res.header_dict['Content-Type'.lower()], 'application/json; charset=utf8')
        expected_results = json.dumps(
            [
                [
                    "Health",
                    3
                ],
                [
                    "Water<>&\"{}'",
                    2
                ],
                [
                    u"Tax\u6c49\u5b57\u6f22\u5b57",
                    1
                ]
            ],
            indent=4
        )
        latest_rows = searchcloud.get_latest(model.Session)
        self.assert_equal(expected_results, res.body)
        self.assert_equal(json.loads(res.body), latest_rows)
        # Check you get an upload form
        res = self.app.get('/searchcloud/upload', status=200, extra_environ={'REMOTE_USER': 'testsysadmin'})
        self.assert_equal('type="file"' in res.body, True)
        self.assert_equal('enctype="multipart/form-data"' in res.body, True)
        # Check you get a preview
        res = self.app.post(
            '/searchcloud/upload',
            status=200,
            extra_environ={'REMOTE_USER': 'testsysadmin'},
            upload_files=[('searchcloud', 'test.json', expected_results.replace('Health', 'Environment'))]
        )
        self.assert_equal(cgi.escape(expected_json.replace('Health', 'Environment')) in res.body, True)
        # Check you get a saved message
        res = self.app.post(
            '/searchcloud/save',
            status=200,
            extra_environ={'REMOTE_USER': 'testsysadmin'},
            params={'searchcloud': expected_results.replace('Health', 'Environment')}
        )
        self.assert_equal('Search Cloud Successfully Updated' in res.body, True)
        model.Session.commit()
        # Check the new data is in the approved table
        self.assert_equal(searchcloud.get_approved(model.Session), [[u'Environment', 3L], [u"Water<>&\"{}'", 2L], [u'Tax\u6c49\u5b57\u6f22\u5b57', 1L]])
        # Finally test that the new data is on the homepage
        home_url = tests.url_for('home')
        res = self.app.get(home_url)
        self.assert_equal(
            'var word_array = '+(cgi.escape(expected_json.replace('Health', 'Environment'))) in res,
            True,
        )

    def test_09_json_parsing_and_errors(self):
        # Post the wrong data and check we get an error
        res = self.app.post(
            '/searchcloud/save',
            status=200,
            extra_environ={'REMOTE_USER': 'testsysadmin'},
            params={'searchcloud': expected_json}
        )
        self.assert_equal('Error Accepting JSON File' in res.body, True)
        # Check it hasn't changed the approved data
        self.assert_equal(searchcloud.get_approved(model.Session), [[u'Environment', 3L], [u"Water<>&\"{}'", 2L], [u'Tax\u6c49\u5b57\u6f22\u5b57', 1L]])
        # Post an empty list to empty the table
        res = self.app.post(
            '/searchcloud/save',
            status=200,
            extra_environ={'REMOTE_USER': 'testsysadmin'},
            params={'searchcloud': '[]'}
        )
        model.Session.commit()
        self.assert_equal('Search Cloud Successfully Updated' in res.body, True)
        # The approved data table should be empty
        self.assert_equal(searchcloud.get_approved(model.Session), [])

    def test_10_access_restrictions(self):
        model.Session.add(model.User(name=u'notadmin'))
        notadmin = model.User.by_name(u'notadmin')
        for url in [
            '/searchcloud',
            '/searchcloud/',
            '/searchcloud/upload',
            '/searchcloud/index',
            '/searchcloud/download',
            '/searchcloud/save',
        ]:
            # Check we get a 401 response from notadmin
            res = self.app.get(url, status=401, extra_environ={'REMOTE_USER': 'notadmin'})
            res = self.app.post(url, status=401, extra_environ={'REMOTE_USER': 'notadmin'})

