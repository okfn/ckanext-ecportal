import json
from ckan.lib.base import c, model
from ckan.authz import Authorizer
from ckan.lib.navl.validators import ignore_missing, keep_extras
from ckan.logic.converters import convert_from_extras
from ckan.logic.schema import package_form_schema
from ckan.plugins import implements, SingletonPlugin, IDatasetForm
from field_values import type_of_dataset, publishers, geographical_granularity,\
    update_frequency, temporal_granularity, eurovoc_theme
from validators import use_other, extract_other, ecportal_date_to_db,\
    convert_to_extras, duplicate_extras_key

import logging
log = logging.getLogger(__name__)

# TODO: clarify these metadata changes (from MetadataModel.ods):
#
# note: Notes on the dataset. Can be multiple. Must be typed. (different to CKAN extras?)
# license: Add EC license (and set as default) when available.
# author_email: Is this needed?
# maintainer_email: Is this needed?
# responsible_department: Is this redundant (same as published_by)?
# Do we still need the eurostat extras? Or should they be custom extras only? Set as custom for now.


class ECPortalDatasetForm(SingletonPlugin):
    implements(IDatasetForm, inherit=True)

    def package_form(self):
        return 'package/package_ecportal.html'

    def is_fallback(self):
        return True

    def package_types(self):
        return ['dataset']

    def setup_template_variables(self, context, data_dict=None, package_type=None):
        c.licences = [('', '')] + model.Package.get_license_options()
        c.type_of_dataset = type_of_dataset
        c.publishers = publishers
        c.update_frequency = update_frequency
        c.temporal_granularity = temporal_granularity 
        c.geographical_granularity = geographical_granularity
        c.eurovoc_theme = eurovoc_theme
        c.is_sysadmin = Authorizer().is_sysadmin(c.user)

        # find extras that are not part of our schema
        c.additional_extras = []
        schema_keys = self.form_to_db_schema().keys()
        
        if c.pkg_json:
            extras = json.loads(c.pkg_json).get('extras', [])
            for extra in extras:
                if not extra['key'] in schema_keys:
                    c.additional_extras.append(extra)

        # This is messy as auths take domain object not data_dict
        pkg = context.get('package') or c.pkg
        if pkg:
            c.auth_for_change_state = Authorizer().am_authorized(
                c, model.Action.CHANGE_STATE, pkg)

    def form_to_db_schema(self, package_type=None):
        schema = package_form_schema()
        schema.update({
            'type_of_dataset': [ignore_missing, unicode, convert_to_extras],
            'responsible_department': [ignore_missing, unicode, convert_to_extras],
            'published_by': [ignore_missing, unicode, convert_to_extras],
            'release_date': [ignore_missing, ecportal_date_to_db, convert_to_extras],
            'modified_date': [ignore_missing, ecportal_date_to_db, convert_to_extras],
            'update_frequency': [use_other, unicode, convert_to_extras],
            'update_frequency-other': [],
            'temporal_coverage_from': [ignore_missing, ecportal_date_to_db, convert_to_extras],
            'temporal_coverage_to': [ignore_missing, ecportal_date_to_db, convert_to_extras],
            'temporal_granularity': [use_other, unicode, convert_to_extras],
            'temporal_granularity-other': [],
            'geographical_coverage': [ignore_missing, unicode, convert_to_extras],
            'geographical_granularity': [use_other, unicode, convert_to_extras],
            'geographical_granularity_other': [],
            'eurovoc_theme': [ignore_missing, unicode, convert_to_extras],
            # 'eurovoc_tag': [ignore_missing, unicode, convert_to_extras],

            # 'code': [ignore_missing, unicode, convert_to_extras],
            # 'type': [ignore_missing, unicode, convert_to_extras],
            # 'theme1': [ignore_missing, unicode, convert_to_extras],
            # 'theme2': [ignore_missing, unicode, convert_to_extras],
            # 'theme3': [ignore_missing, unicode, convert_to_extras],
            # 'license_link': [ignore_missing, unicode, convert_to_extras],
            # 'support': [ignore_missing, unicode, convert_to_extras],

            '__after': [duplicate_extras_key],
        })
        return schema
    
    def db_to_form_schema(data, package_type=None):
        schema = package_form_schema()
        schema.update({
            'tags': {
                '__extras': [keep_extras]
            },

            'type_of_dataset': [convert_from_extras, ignore_missing],
            'responsible_department': [convert_from_extras, ignore_missing],
            'published_by': [convert_from_extras, ignore_missing],
            'release_date': [convert_from_extras, ignore_missing],
            'modified_date': [convert_from_extras, ignore_missing],
            'update_frequency': [convert_from_extras, ignore_missing, extract_other(update_frequency)],
            'temporal_coverage_from': [convert_from_extras, ignore_missing],
            'temporal_coverage_to': [convert_from_extras, ignore_missing],
            'temporal_granularity': [convert_from_extras, ignore_missing, extract_other(temporal_granularity)],
            'geographical_coverage': [convert_from_extras, ignore_missing],
            'geographical_granularity': [convert_from_extras, ignore_missing, extract_other(geographical_granularity)],
            'eurovoc_theme': [convert_from_extras, ignore_missing],
            # 'eurovoc_tag': [convert_from_extras, ignore_missing],

            # 'code': [convert_from_extras, ignore_missing],
            # 'type': [convert_from_extras, ignore_missing],
            # 'theme1': [convert_from_extras, ignore_missing],
            # 'theme2': [convert_from_extras, ignore_missing],
            # 'theme3': [convert_from_extras, ignore_missing],
            # 'license_link': [convert_from_extras, ignore_missing],
            # 'support': [convert_from_extras, ignore_missing],
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

