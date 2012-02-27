import json
from ckan.lib.base import c, model
from ckan.authz import Authorizer
from ckan.lib.navl.validators import ignore_missing, keep_extras
from ckan.logic import get_action, NotFound
from ckan.logic.converters import convert_from_extras
from ckan.logic.schema import package_form_schema
from ckan.logic.converters import convert_to_tags, convert_from_tags, free_tags_only
from ckan.plugins import implements, SingletonPlugin, IDatasetForm
from field_values import type_of_dataset, update_frequency,\
    temporal_granularity
from validators import use_other, extract_other, ecportal_date_to_db,\
    convert_to_extras, duplicate_extras_key

import logging
log = logging.getLogger(__name__)

GEO_VOCAB_NAME = u'geographical_coverage'


class ECPortalDatasetForm(SingletonPlugin):
    implements(IDatasetForm, inherit=True)

    def package_form(self):
        return 'package/package_ecportal.html'

    def is_fallback(self):
        return True

    def package_types(self):
        return ['dataset']

    def setup_template_variables(self, context, data_dict=None, package_type=None):
        c.licences = model.Package.get_license_options()
        c.type_of_dataset = type_of_dataset
        c.publishers = []
        c.update_frequency = update_frequency
        c.temporal_granularity = temporal_granularity
        c.is_sysadmin = Authorizer().is_sysadmin(c.user)

        try:
            c.geographical_coverage = get_action('tag_list')(context, {'vocabulary_id': GEO_VOCAB_NAME})
        except NotFound:
            c.geographical_coverage = []

        # find extras that are not part of our schema
        c.additional_extras = []
        schema_keys = self.form_to_db_schema().keys()
        if c.pkg_json:
            extras = json.loads(c.pkg_json).get('extras', [])
            for extra in extras:
                if not extra['key'] in schema_keys:
                    c.additional_extras.append(extra)

    def form_to_db_schema(self, package_type=None):
        schema = package_form_schema()
        schema.update({
            'type_of_dataset': [ignore_missing, unicode, convert_to_extras],
            'published_by': [ignore_missing, unicode, convert_to_extras],
            'release_date': [ignore_missing, ecportal_date_to_db, convert_to_extras],
            'modified_date': [ignore_missing, ecportal_date_to_db, convert_to_extras],
            'update_frequency': [use_other, unicode, convert_to_extras],
            'update_frequency-other': [],
            'temporal_coverage_from': [ignore_missing, ecportal_date_to_db, convert_to_extras],
            'temporal_coverage_to': [ignore_missing, ecportal_date_to_db, convert_to_extras],
            'temporal_granularity': [use_other, unicode, convert_to_extras],
            'geographical_coverage': [ignore_missing, unicode, convert_to_tags(GEO_VOCAB_NAME)],
            '__after': [duplicate_extras_key],
        })
        return schema

    def db_to_form_schema(data, package_type=None):
        schema = package_form_schema()
        schema.update({
            'tags': {
                '__extras': [keep_extras, free_tags_only]
            },

            'type_of_dataset': [convert_from_extras, ignore_missing],
            'published_by': [convert_from_extras, ignore_missing],
            'release_date': [convert_from_extras, ignore_missing],
            'modified_date': [convert_from_extras, ignore_missing],
            'update_frequency': [convert_from_extras, ignore_missing, extract_other(update_frequency)],
            'temporal_coverage_from': [convert_from_extras, ignore_missing],
            'temporal_coverage_to': [convert_from_extras, ignore_missing],
            'temporal_granularity': [convert_from_extras, ignore_missing],
            'geographical_coverage': [convert_from_tags(GEO_VOCAB_NAME), ignore_missing],
        })

        # Remove isodate validator
        schema['resources'].update({
            'last_modified': [ignore_missing],
            'cache_last_updated': [ignore_missing],
            'webstore_last_updated': [ignore_missing]
        })

        return schema

    def check_data_dict(self, data_dict):
        return
