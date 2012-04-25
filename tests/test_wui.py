import json
import paste.fixture
from ckan import model
from ckan.lib.create_test_data import CreateTestData
import ckan.lib.helpers as h
from ckan.tests import WsgiAppCase
from ckanext.ecportal.forms import GEO_VOCAB_NAME


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

        for v in value:
            if not v in [option for (option, checked) in self.options]:
                raise ValueError("Option %r not found (from %s)"
                    % (value, ', '.join(
                    [repr(o) for o, checked in self.options]))
                )

        new_options = [(option, True) for (option, checked) in self.options if option in value]
        new_options += [(option, False) for (option, checked) in self.options if not option in value]
        self.options = new_options

    def value__get(self):
        return [option for (option, checked) in self.options if checked]

    value = property(value__get, value__set)


class TestWUI(WsgiAppCase):
    @classmethod
    def setup_class(cls):
        CreateTestData.create()
        cls.sysadmin_user = model.User.get('testsysadmin')
        cls.dset = model.Package.get('warandpeace')
        cls.geo_tags = [(u'uk', u'United Kingdom'), (u'ie', u'Ireland')]

        # use our custom select class for this test suite
        cls.old_select = paste.fixture.Field.classes['select']
        paste.fixture.Field.classes['select'] = Select

        extra_environ = {'Authorization': str(cls.sysadmin_user.apikey)}

        # create a test vocab
        params = json.dumps({'name': GEO_VOCAB_NAME})
        response = cls.app.post('/api/action/vocabulary_create', params=params,
                                extra_environ=extra_environ)
        assert json.loads(response.body)['success']
        cls.geo_vocab_id = json.loads(response.body)['result']['id']

        for tag in cls.geo_tags:
            # add tags to the vocab
            params = json.dumps({'name': tag[0],
                                 'vocabulary_id': cls.geo_vocab_id})
            response = cls.app.post('/api/action/tag_create',
                                    params=params,
                                    extra_environ=extra_environ)
            assert json.loads(response.body)['success']
            # add tag translations
            params = json.dumps({
                'term': tag[0],
                'term_translation': tag[1],
                'lang_code': u'en'
            })
            response = cls.app.post('/api/action/term_translation_update',
                                    params=params,
                                    extra_environ=extra_environ)
            assert json.loads(response.body)['success']

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
        extra_environ = {'Authorization': str(self.sysadmin_user.apikey)}
        response = self.app.post('/api/action/package_update', params=params,
                                 extra_environ=extra_environ)
        assert json.loads(response.body)['success']

    def test_geo_tags_translated(self):
        response = self.app.get(h.url_for(
            controller='package', action='edit', id=self.dset.id
        ), extra_environ={'Authorization': str(TestWUI.sysadmin_user.apikey)})
        assert '<option value="ie">Ireland</option>' in response.body, response.body
        assert '<option value="uk">United Kingdom</option>' in response.body, response.body
