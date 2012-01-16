from ckan.lib.base import c, model
from ckan.lib.field_types import DateType, DateConvertError
from ckan.authz import Authorizer
from ckan.lib.navl.dictization_functions import Invalid
from ckan.lib.navl.dictization_functions import missing
from ckan.lib.navl.validators import (ignore_missing,
                                      not_empty,
                                      empty,
                                      ignore,
                                      keep_extras,
                                     )
import ckan.logic.validators as val
from ckan.logic.converters import convert_from_extras, convert_to_extras, date_to_form
import ckan.logic.schema as default_schema
from ckan.controllers.package import PackageController
from field_types import GeoCoverageType
from field_values import type_of_dataset, publishers, geographic_granularity,\
    update_frequency, temporal_granularity 

import logging
log = logging.getLogger(__name__)


class ECPortalController(PackageController):
    package_form = 'package_ecportal.html'

    def _setup_template_variables(self, context, data_dict=None):
        c.licences = [('', '')] + model.Package.get_license_options()
        c.type_of_dataset = type_of_dataset
        c.publishers = publishers

        c.geographic_granularity = geographic_granularity
        c.update_frequency = update_frequency
        c.temporal_granularity = temporal_granularity 

        c.is_sysadmin = Authorizer().is_sysadmin(c.user)
        c.resource_columns = model.Resource.get_columns()

        # This is messy as auths take domain object not data_dict
        pkg = context.get('package') or c.pkg
        if pkg:
            c.auth_for_change_state = Authorizer().am_authorized(
                c, model.Action.CHANGE_STATE, pkg)

    def _form_to_db_schema(self):
        schema = {
            'title': [not_empty, unicode],
            'name': [not_empty, unicode, val.name_validator, val.package_name_validator],
            'notes': [not_empty, unicode],

            'type_of_dataset': [ignore_missing, unicode, convert_to_extras],
            'responsible_department': [ignore_missing, unicode, convert_to_extras],
            'published_by': [ignore_missing, unicode, convert_to_extras],
            'release_date': [ignore_missing, ecportal_date_to_db, convert_to_extras],
            'modified_date': [ignore_missing, ecportal_date_to_db, convert_to_extras],
            'update_frequency': [use_other, unicode, convert_to_extras],
            'update_frequency-other': [],
            'temporal_coverage_from': [ignore_missing, ecportal_date_to_db, convert_to_extras],
            'temporal_coverage_to': [ignore_missing, ecportal_date_to_db, convert_to_extras],

            # 'precision': [unicode, convert_to_extras],
            # 'geographic_granularity': [use_other, unicode, convert_to_extras],
            # 'geographic_granularity-other': [],
            'geographic_coverage': [ignore_missing, convert_geographic_to_db, convert_to_extras],
            # 'temporal_granularity': [use_other, unicode, convert_to_extras],
            # 'temporal_granularity-other': [],
            'url': [unicode],
            # 'taxonomy_url': [unicode, convert_to_extras],

            'resources': default_schema.default_resource_schema(),
            
            'published_via': [ignore_missing, unicode, convert_to_extras],
            'author': [ignore_missing, unicode],
            'author_email': [ignore_missing, unicode],
            'mandate': [ignore_missing, unicode, convert_to_extras],
            'license_id': [ignore_missing, unicode],
            'tag_string': [ignore_missing, val.tag_string_convert],
            'national_statistic': [ignore_missing, convert_to_extras],
            'state': [val.ignore_not_admin, ignore_missing],

            'log_message': [unicode, val.no_http],

            '__extras': [ignore],
            '__junk': [empty],
        }
        return schema
    
    def _db_to_form_schema(data):
        schema = {
            'type_of_dataset': [convert_from_extras, ignore_missing],
            'responsible_department': [convert_from_extras, ignore_missing],
            'published_by': [convert_from_extras, ignore_missing],
            'release_date': [convert_from_extras, ignore_missing],
            'modified_date': [convert_from_extras, ignore_missing],
            'update_frequency': [convert_from_extras, ignore_missing, extract_other(update_frequency)],
            'temporal_coverage_from': [convert_from_extras, ignore_missing, date_to_form],
            'temporal_coverage_to': [convert_from_extras, ignore_missing, date_to_form],

            # 'precision': [convert_from_extras, ignore_missing],
            # 'geographic_granularity': [convert_from_extras, ignore_missing, extract_other(geographic_granularity)],
            'geographic_coverage': [convert_from_extras, ignore_missing, convert_geographic_to_form],
            # 'temporal_granularity': [convert_from_extras, ignore_missing, extract_other(temporal_granularity)],
            # 'taxonomy_url': [convert_from_extras, ignore_missing],

            'resources': default_schema.default_resource_schema(),
            'extras': {
                'key': [],
                'value': [],
                '__extras': [keep_extras]
            },
            'tags': {
                '__extras': [keep_extras]
            },
            
            'published_via': [convert_from_extras, ignore_missing],
            'mandate': [convert_from_extras, ignore_missing],
            'national_statistic': [convert_from_extras, ignore_missing],
            '__extras': [keep_extras],
            '__junk': [ignore],
        }
        return schema

    def _check_data_dict(self, data_dict):
        return

def ecportal_date_to_db(value, context):
    if not value:
        return
    try:
        timedate_dict = DateType.parse_timedate(value, 'db')
    except DateConvertError, e:
        # Cannot parse
        raise Invalid(str(e))
    try:
        value = DateType.format(timedate_dict, 'db')
    except DateConvertError, e:
        # Values out of range
        raise Invalid(str(e))
    return value

def use_other(key, data, errors, context):
    other_key = key[-1] + '-other'
    other_value = data.get((other_key,), '').strip()
    if other_value:
        data[key] = other_value

def extract_other(option_list):
    def other(key, data, errors, context):
        value = data[key]
        if value in dict(option_list).keys():
            return
        elif value is missing:
            data[key] = ''
            return
        else:
            data[key] = 'other'
            other_key = key[-1] + '-other'
            data[(other_key,)] = value
    return other
            
def convert_geographic_to_db(value, context):
    if isinstance(value, list):
        regions = value
    elif value:
        regions = [value]
    else:
        regions = []
    return GeoCoverageType.get_instance().form_to_db(regions)

def convert_geographic_to_form(value, context):
    return GeoCoverageType.get_instance().db_to_form(value)

