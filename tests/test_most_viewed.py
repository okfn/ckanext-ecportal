# -*- coding: utf8 -*-

"""\
"""

import paste.fixture
import paste.deploy.loadwsgi
import ckan.lib.base
import datetime
import os
import cgi
try:
    import json
except ImportError:
    import simplejson as json
import urllib
import ckan.lib as lib
import ckan.lib.search as search
import ckan.tests as tests
import paste.fixture
import create_test_data as ctd
import test_api
import ckanext.ecportal.searchcloud as searchcloud
import ckanext.ecportal.mostviewed as mostviewed
from pylons import config
from ckan import plugins
from ckan import model
from ckan.config.middleware import make_app
from nose.plugins.skip import SkipTest

class TestMostViewed(tests.TestController):

    @classmethod
    def setup_class(cls):
        model.repo.new_revision()
        g = model.Group(name='most_popular_tests', type='organization')
        model.Session.add(g)
        # Packages must have a group, or we get a template error
        model.Session.add(model.Package(name='mostviewed1', title='Most Viewed 1', group=g))
        model.Session.add(model.Package(name='mostviewed2', title='Most Viewed 2', group=g))
        model.Session.add(model.Package(name='mostviewed3', title='Most Viewed 3', group=g))
        model.Session.add(model.Package(name='mostviewed4', title='Most Viewed 4', group=g))
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
        #model.repo.rebuild_db()
        search.clear()
        # Plugins
        plugins.reset()

    def test_00_tables_empty(self):
        '''Tracking tables are empty'''
        for table in ['tracking_raw', 'tracking_summary']:
            self.assert_equal(searchcloud.table_exists(model.Session, table), True)
            result = model.Session.execute(
                'select count(*) from '+table
            ).fetchall()[0][0]
            self.assert_equal(int(result), 0)

    def test_01_viewing_datasets(self):
        '''No recent datasets displayed on home when summary table is empty'''
        rows = mostviewed.get_most_viewed(model.Session, 10)
        self.assert_equal(rows, [])
        home_url = tests.url_for('home')
        res = self.app.get(home_url)
        self.assert_equal("Most viewed datasets" in res, False)

    def _view_datasets(self, ip_fragment=0):
        counter = 0
        for name in range(4):
            # Repeat the view a number of times
            dataset_url = test_api.h.url_for(
                controller='package',
                action='read',
                id='mostviewed'+str(name+1)
            )
            for i in range(name+1):
                counter += 1
                if counter > 255:
                    raise Exception('Test code only designed for 255 requests')
                res = self.app.post(
                    '/_tracking',
                    status=200,
                    headers = {
                        "Content-Type": "application/x-www-form-urlencoded",
                        "Accept": "*/*",
                        "Accept-Language": "en-US,en;q=0.8",
                        "Accept-Charset": "ISO-8859-1,utf-8;q=0.7,*;q=0.3",
                        "Accept-Encoding": "gzip,deflate,sdch",
                        "User-Agent": "Mozilla/5.0",
                    },
                    # We need different remote addresses so that the 
                    # summary code treats each visit separately
                    extra_environ={
                        'REMOTE_ADDR': '127.0.%d.%d'%(ip_fragment, counter)
                    },
                    params = {
                        'url': dataset_url,
                        'type': 'page',
                    }
                )

    def test_02_viewing_datasets(self):
        '''Viewing datasets adds data to the tracking table and not the summary table'''
        # @@@ This fails because the current code is not based on package
        # read, but rather an explicit AJAX get, which these command 
        # line tests don't trigger
        #
        # for name in range(4):
        #     dataset_url = test_api.h.url_for(
        #         controller='package',
        #         action='read', 
        #         id='mostviewed'+str(name+1)
        # )
        #     res = self.app.get(dataset_url, status=200)
        # result = model.Session.execute(
        #     'select count(*) from tracking_raw'
        # ).fetchall()[0][0]
        # self.assert_equal(int(result), 4)

        # @@@ Instead, let's just call the tracking URL directly
        # Check the results are what we wanted 
        self._view_datasets(1)
        result = model.Session.execute(
            'select count(*) from tracking_raw'
        ).fetchall()[0][0]
        self.assert_equal(int(result), 10)
        result = model.Session.execute(
            'select count(*) from tracking_summary'
        ).fetchall()[0][0]
        self.assert_equal(int(result), 0)
        # And that data still isn't on the homepage
        home_url = tests.url_for('home')
        res = self.app.get(home_url)
        self.assert_equal("Recently viewed datasets" in res, False)

    def test_03_running_paster_command_builds_summary_table(self):
        '''Running the paster command builds summary table'''
        os.system(
            "paster --plugin=ckan tracking update --config test-core.ini "+\
            datetime.datetime.now().strftime('%Y-%m-%d')
        )
        result = model.Session.execute(
            'select url, running_total from tracking_summary order by url asc'
        ).fetchall()
        self.assert_equal(
            [x for x in result],
            [
                (u'/dataset/mostviewed1', 1), 
                (u'/dataset/mostviewed2', 2), 
                (u'/dataset/mostviewed3', 3),
                (u'/dataset/mostviewed4', 4),
            ]
        )

    def test_04_changing_data_and_rerunning_paster_command(self):
        '''Rerunning paster command re-builds summary table'''
        self._view_datasets(2)
        os.system(
            "paster --plugin=ckan tracking update --config test-core.ini "+\
            datetime.datetime.now().strftime('%Y-%m-%d')
        )
        result = model.Session.execute(
            'select url, running_total from tracking_summary order by url asc'
        ).fetchall()
        self.assert_equal(
            [x for x in result], 
            [
                (u'/dataset/mostviewed1', 2), 
                (u'/dataset/mostviewed2', 4), 
                (u'/dataset/mostviewed3', 6), 
                (u'/dataset/mostviewed4', 8),
            ]
        )

    def test_05_most_viewed_present_when_summary_present(self):
        '''Most viewed datasets dispalyed with summary present'''
        # Check the old data is still there (ie empty)
        home_url = tests.url_for('home')
        res = self.app.get(home_url)
        self.assert_equal("Most viewed datasets" in res, False)
        # Now bypass the cache and check the new data is there
        # To do this we'll have to set up our own test app 
        # with the cache disabled:
        no_cache_app = paste.deploy.loadwsgi.loadapp(
            'config:test-core.ini',
            relative_to=os.getcwd(),
            global_conf={'beaker.cache.enabled': 'False'},
        )
        # Now test
        home_url = tests.url_for('home')
        res = paste.fixture.TestApp(no_cache_app).get(home_url)
        self.assert_equal("Most viewed datasets" in res, True)

