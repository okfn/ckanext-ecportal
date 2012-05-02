import paste.fixture
import ckan.model as model
import ckan.lib as lib
import ckan.lib.helpers as h
import ckan.tests as tests
import test_api

try:
    import json
except ImportError:
    import simplejson as json


# paste.fixture.Field.Select does not handle multiple selects currently,
# so replace with our own implementations of Form and Select
class Form(paste.fixture.Form):
    def __init__(self, response, text):
        paste.fixture.Form.__init__(self, response, text)

    def submit_fields(self, name=None, index=None):
        """
        Return a list of ``[(name, value), ...]`` for the current
        state of the form.
        """
        submit = []
        if name is not None:
            field = self.get(name, index=index)
            submit.append((field.name, field.value_if_submitted()))
        for name, fields in self.fields.items():
            if name is None:
                continue
            for field in fields:
                value = field.value
                if value is None:
                    continue
                if isinstance(value, list):
                    for v in value:
                        submit.append((name, v))
                else:
                    submit.append((name, value))
        return submit


class Select(paste.fixture.Field):
    def __init__(self, *args, **attrs):
        paste.fixture.Field.__init__(self, *args, **attrs)
        self.options = []
        self.selectedIndex = None

    def value__set(self, value):
        if not value:
            self.selectedIndex = None
            self.options = [(option, False) for (option, checked) in self.options]
            return

        new_options = []
        for option, checked in self.options:
            if option and option in value:
                new_options.append((option, True))
            else:
                new_options.append((option, False))
        self.options = new_options

    def value__get(self):
        return [option for (option, checked) in self.options if checked]

    value = property(value__get, value__set)


class TestWUI(tests.WsgiAppCase):
    @classmethod
    def setup_class(cls):
        lib.create_test_data.CreateTestData.create('publisher')
        cls.sysadmin_user = model.User.get('testsysadmin')
        cls.dset = model.Package.get('warandpeace')
        cls.geo_tags = [(u'uk', u'United Kingdom'), (u'ie', u'Ireland')]

        model.repo.new_revision()
        g = model.Group.get('david')
        g.type = 'organization'
        model.Session.add(g)
        model.Session.commit()

        # use our custom select class for this test suite
        cls.old_select = paste.fixture.Field.classes['select']
        paste.fixture.Field.classes['select'] = Select

        cls.extra_environ = {'Authorization': str(cls.sysadmin_user.apikey)}

        # create status vocab
        status = test_api.create_vocab(u'status', cls.sysadmin_user.name)
        test_api.add_tag_to_vocab(u'http://purl.org/adms/status/Completed',
                                  status['id'], cls.sysadmin_user.name)
        test_api.add_tag_to_vocab(u'http://purl.org/adms/status/Withdrawn',
                                  status['id'], cls.sysadmin_user.name)

        # create geographical coverage vocab
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
                                    extra_environ=cls.extra_environ)
            assert json.loads(response.body)['success']

        # create temporal granularity
        temporal = test_api.create_vocab(u'temporal_granularity',
                                         cls.sysadmin_user.name)
        test_api.add_tag_to_vocab(u'day', temporal['id'],
                                  cls.sysadmin_user.name)
        test_api.add_tag_to_vocab(u'month', temporal['id'],
                                  cls.sysadmin_user.name)

    @classmethod
    def teardown_class(cls):
        paste.fixture.Field.classes['select'] = cls.old_select
        model.repo.rebuild_db()

    def _remove_vocab_tags(self, dataset_id, vocab_id, tag_name):
        params = json.dumps({'id': dataset_id})
        response = self.app.post('/api/action/package_show', params=params)
        dataset = json.loads(response.body)['result']
        dataset['geographical_coverage'] = []
        params = json.dumps(dataset)
        response = self.app.post('/api/action/package_update', params=params,
                                 extra_environ=self.extra_environ)
        assert json.loads(response.body)['success']

    def test_geo_tags_translated(self):
        response = self.app.get(
            h.url_for(controller='package', action='edit', id=self.dset.id),
            extra_environ=self.extra_environ
        )
        assert '<option value="ie">Ireland</option>' in response.body
        assert '<option value="uk">United Kingdom</option>' in response.body

    def test_dataset_create(self):
        dataset = {
            'name': u'test-create',
            'description': u'test description',
            'published_by': u'david',
            'status': u'http://purl.org/adms/status/Completed',
            'contact_name': u'dataset-contact'
        }

        # create the dataset
        response = self.app.get(
            h.url_for(controller='package', action='new'),
            extra_environ=self.extra_environ
        )
        fv = response.forms['dataset-edit']
        fv = Form(fv.response, fv.text)
        for k in dataset.keys():
            fv[k] = dataset[k]
        response = fv.submit('save', extra_environ=self.extra_environ)

        # check values
        response = response.follow(extra_environ=self.extra_environ)
        for k in dataset.keys():
            assert dataset[k] in response

    def test_dataset_edit(self):
        # TODO: add remaining vocab fields
        dataset = {
            'name': u'test-edit',
            'title': u'Test Title',
            'description': u'test description',
            'published_by': u'david',
            'status': u'http://purl.org/adms/status/Completed',
            'contact_name': u'dataset-contact',
            'alternative_title': u'test alt title',
            'identifier': u'test-id',
            'release_date': u'2012-01-01',
            'modified_date': u'2012-01-01',
            'accrual_periodicity': u'quarterly',
            'temporal_coverage_from': u'2012-01',
            'temporal_coverage_to': u'2012-02',
            'temporal_granularity': u'month',
            'version': u'1.0',
            'version_description': u'test version description',
            'contact_email': u'test@contact.com',
            'contact_address': u'123 contact st',
            'contact_telephone': u'0123456789',
            'contact_webpage': u'http://test.contact.com'
        }
        response = self.app.post('/api/action/package_create',
                                 params=json.dumps(dataset),
                                 extra_environ=self.extra_environ)
        assert json.loads(response.body)['success']

        dataset.update({
            'title': u'Test Title 2',
            'description': u'test description 2',
            'status': u'http://purl.org/adms/status/Withdrawn',
            'contact_name': u'dataset-contact-2',
            'alternative_title': u'test alt title 2',
            'identifier': u'test-id-2',
            'release_date': u'2012-01-02',
            'modified_date': u'2012-01-02',
            'accrual_periodicity': u'never',
            'temporal_coverage_from': u'2012-02',
            'temporal_coverage_to': u'2012-03',
            'temporal_granularity': u'day',
            'version': u'2.0',
            'version_description': u'test version description 2',
            'contact_email': u'test2@contact.com',
            'contact_address': u'123 contact st 2',
            'contact_telephone': u'0123',
            'contact_webpage': u'http://test2.contact.com'
        })
        response = self.app.get(
            h.url_for(controller='package', action='edit', id=dataset['name']),
            extra_environ=self.extra_environ
        )
        fv = response.forms['dataset-edit']
        fv = Form(fv.response, fv.text)
        for k in dataset.keys():
            fv[k] = dataset[k]
        response = fv.submit('save', extra_environ=self.extra_environ)

        response = self.app.get(
            h.url_for(controller='package', action='edit', id=dataset['name']),
            extra_environ=self.extra_environ
        )
        fv = response.forms['dataset-edit']
        fv = Form(fv.response, fv.text)
        for k in dataset.keys():
            # TODO: select values returned as a list, should return a single
            # value if it is a standard select object (not multi-select)
            if not isinstance(fv[k].value, list):
                assert fv[k].value == dataset[k], (fv[k].value, dataset[k])
            else:
                assert fv[k].value[0] == dataset[k], (fv[k].value[0], dataset[k])
