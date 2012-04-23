import json
import pylons
from ckan.lib.base import c, model
from ckan.authz import Authorizer
from ckan.lib.navl.validators import ignore, ignore_missing, keep_extras,\
    empty, not_empty
from ckan.logic import get_action, check_access
from ckan.logic import NotFound, NotAuthorized
from ckan.logic.converters import convert_from_extras
from ckan.logic.validators import package_id_not_changed,\
    name_validator, package_name_validator
from ckan.logic.schema import package_form_schema, default_tags_schema
from ckan.logic.converters import convert_to_tags, convert_from_tags, free_tags_only
import ckan.plugins as plugins
import field_values
from validators import use_other, extract_other, ecportal_date_to_db,\
    convert_to_extras, convert_to_groups, convert_from_groups,\
    duplicate_extras_key, publisher_exists, keyword_string_convert, rename, \
    update_rdf
import helpers

import logging
log = logging.getLogger(__name__)

GEO_VOCAB_NAME = u'geographical_coverage'


class ECPortalDatasetForm(plugins.SingletonPlugin):
    plugins.implements(plugins.IDatasetForm, inherit=True)
    plugins.implements(plugins.ITemplateHelpers)

    def package_form(self):
        return 'package/new_package_form.html'

    def new_template(self):
        return 'package/new.html'

    def comments_template(self):
        return 'package/comments.html'

    def search_template(self):
        return 'package/search.html'

    def read_template(self):
        return 'package/read.html'

    def history_template(self):
        return 'package/history.html'

    def is_fallback(self):
        return True

    def package_types(self):
        return ['dataset']

    def setup_template_variables(self, context, data_dict=None, package_type=None):
        c.licences = model.Package.get_license_options()
        c.interoperability_levels = field_values.interoperability_levels
        c.type_of_dataset = field_values.type_of_dataset
        c.accrual_periodicity = field_values.accrual_periodicity
        c.temporal_granularity = field_values.temporal_granularity
        c.is_sysadmin = Authorizer().is_sysadmin(c.user)

        ckan_lang = pylons.request.environ['CKAN_LANG']
        ckan_lang_fallback = pylons.config.get('ckan.locale_default', 'en')

        # get publisher IDs and name translations
        group_type = pylons.config.get('ckan.default.group_type', 'organization')
        groups = get_action('group_list')(context, {'all_fields': True})
        groups = [g for g in groups if g.get('type') == group_type]
        publishers = []

        for group in groups:
            translation = get_action('term_translation_show')(
                {'model': model},
                {'terms': group['title'], 'lang_code': ckan_lang}
            )
            if not translation:
                translation = get_action('term_translation_show')(
                    {'model': model},
                    {'terms': group['title'], 'lang_code': ckan_lang_fallback}
                )
            group_translation = translation[0]['term_translation'] if translation else group['title']
            publishers.append((group['id'], group_translation))
        c.publishers = publishers

        # get geo tag translations (full names)
        # eg: 'UK' translates to 'United Kingdom' in English
        try:
            geo_tags = get_action('tag_list')(context, {'vocabulary_id': GEO_VOCAB_NAME})

            geographical_coverage = []
            for geo_tag in geo_tags:
                translation = get_action('term_translation_show')(
                    {'model': model},
                    {'terms': geo_tag, 'lang_code': ckan_lang}
                )
                if not translation:
                    translation = get_action('term_translation_show')(
                        {'model': model},
                        {'terms': geo_tag, 'lang_code': ckan_lang_fallback}
                    )

                tag_translation = translation[0]['term_translation'] if translation else geo_tag
                geographical_coverage.append((geo_tag, tag_translation))

            c.geographical_coverage = geographical_coverage

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

        # This is messy as auths take domain object not data_dict
        context_pkg = context.get('package', None)
        pkg = context_pkg or c.pkg
        if pkg:
            try:
                if not context_pkg:
                    context['package'] = pkg
                check_access('package_change_state', context)
                c.auth_for_change_state = True
            except NotAuthorized:
                c.auth_for_change_state = False

    def form_to_db_schema_options(self, options):
        'Use ODP schema for WUI and API calls'
        schema = self.form_to_db_schema()

        if options.get('api'):
            schema.update({
                'keywords': default_tags_schema(),
                'groups': {
                    'id': [ignore_missing, unicode],
                    'name': [ignore_missing, unicode],
                    '__extras': [ignore],
                }
            })

            if options.get('type') == 'create':
                schema.update({'id': [empty]})
            else:
                schema.update({
                    'id': [ignore_missing, package_id_not_changed],
                    'name': [ignore_missing, name_validator, package_name_validator, unicode],
                    'title': [ignore_missing, unicode]
                })

        return schema

    def form_to_db_schema(self, package_type=None):
        schema = package_form_schema()
        schema.update({
            'keyword_string': [ignore_missing, keyword_string_convert],
            'alternative_title': [ignore_missing, unicode, convert_to_extras],
            'description': [not_empty, unicode],
            'status': [not_empty, unicode, convert_to_extras],
            'identifier': [ignore_missing, unicode, convert_to_extras],
            'interoperability_level': [ignore_missing, unicode, convert_to_extras],
            'type_of_dataset': [ignore_missing, unicode, convert_to_extras],
            'published_by': [ignore_missing, unicode, publisher_exists, convert_to_groups],
            'release_date': [ignore_missing, ecportal_date_to_db, convert_to_extras],
            'modified_date': [ignore_missing, ecportal_date_to_db, convert_to_extras],
            'accrual_periodicity': [ignore_missing, use_other, unicode, convert_to_extras],
            'accrual_periodicity-other': [ignore_missing, unicode],
            'temporal_coverage_from': [ignore_missing, ecportal_date_to_db, convert_to_extras],
            'temporal_coverage_to': [ignore_missing, ecportal_date_to_db, convert_to_extras],
            'temporal_granularity': [ignore_missing, unicode, convert_to_extras],
            'geographical_coverage': [ignore_missing, convert_to_tags(GEO_VOCAB_NAME)],
            'version_description': [ignore_missing, unicode, convert_to_extras],
            'skos_note': [ignore_missing, unicode, convert_to_extras],
            'change_note': [ignore_missing, unicode, convert_to_extras],
            'definition_note': [ignore_missing, unicode, convert_to_extras],
            'editorial_note': [ignore_missing, unicode, convert_to_extras],
            'history_note': [ignore_missing, unicode, convert_to_extras],
            'scope_note': [ignore_missing, unicode, convert_to_extras],
            'example_note': [ignore_missing, unicode, convert_to_extras],
            'rdf': [ignore_missing, unicode, update_rdf, convert_to_extras],
            '__after': [duplicate_extras_key,
                        rename('keywords', 'tags'),
                        rename('description', 'notes')],
        })

        schema['groups'].update({
            'capacity': [ignore_missing, unicode]
        })
        return schema

    def db_to_form_schema(data, package_type=None):
        schema = package_form_schema()
        schema.update({
            'tags': {
                '__extras': [keep_extras, free_tags_only]
            },
            'alternative_title': [convert_from_extras, ignore_missing],
            'status': [convert_from_extras, ignore_missing],
            'identifier': [convert_from_extras, ignore_missing],
            'interoperability_level': [convert_from_extras, ignore_missing],
            'type_of_dataset': [convert_from_extras, ignore_missing],
            'published_by': [convert_from_groups, ignore_missing],
            'release_date': [convert_from_extras, ignore_missing],
            'modified_date': [convert_from_extras, ignore_missing],
            'accrual_periodicity': [convert_from_extras, ignore_missing,
                                    extract_other(field_values.accrual_periodicity)],
            'temporal_coverage_from': [convert_from_extras, ignore_missing],
            'temporal_coverage_to': [convert_from_extras, ignore_missing],
            'temporal_granularity': [convert_from_extras, ignore_missing],
            'geographical_coverage': [convert_from_tags(GEO_VOCAB_NAME), ignore_missing],
            'version_description': [convert_from_extras, ignore_missing],
            'skos_note': [convert_from_extras, ignore_missing],
            'change_note': [convert_from_extras, ignore_missing],
            'definition_note': [convert_from_extras, ignore_missing],
            'editorial_note': [convert_from_extras, ignore_missing],
            'history_note': [convert_from_extras, ignore_missing],
            'scope_note': [convert_from_extras, ignore_missing],
            'example_note': [convert_from_extras, ignore_missing],
            'rdf': [convert_from_extras, ignore_missing],
            'license_url': [ignore_missing],
            'license_title': [ignore_missing],
            '__after': [duplicate_extras_key,
                        rename('tags', 'keywords'),
                        rename('notes', 'description')]
        })

        schema['groups'].update({
            'name': [not_empty, unicode],
            'title': [ignore_missing],
            'capacity': [ignore_missing, unicode]
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

    def get_helpers(self):
        return {'format_description': helpers.format_description}
