import logging
import operator
import pylons

from ckan.authz import Authorizer
import ckan.model as model
import ckan.logic as logic
import ckan.logic.schema
import ckan.plugins as p
from ckan.logic.validators import (package_id_not_changed,
                                   package_name_validator)
from ckan.lib.navl.validators import (ignore,
                                      ignore_missing,
                                      keep_extras,
                                      empty,
                                      not_empty,
                                      default)
from ckan.logic.converters import (convert_to_tags,
                                   convert_from_tags,
                                   free_tags_only)
from validators import (ecportal_name_validator,
                        ecportal_date_to_db,
                        convert_to_extras,
                        convert_from_extras,
                        convert_to_groups,
                        convert_from_groups,
                        duplicate_extras_key,
                        publisher_exists,
                        keyword_string_convert,
                        rename,
                        update_rdf,
                        requires_field,
                        convert_resource_type,
                        member_of_vocab,
                        map_licenses,
                        reduce_list,
                        group_name_unchanged)

import ckanext.ecportal.helpers as helpers
import ckanext.ecportal.unicode_sort as unicode_sort

log = logging.getLogger(__name__)
GEO_VOCAB_NAME = u'geographical_coverage'
DATASET_TYPE_VOCAB_NAME = u'dataset_type'
LANGUAGE_VOCAB_NAME = u'language'
STATUS_VOCAB_NAME = u'status'
INTEROP_VOCAB_NAME = u'interoperability_level'
TEMPORAL_VOCAB_NAME = u'temporal_granularity'
UNICODE_SORT = unicode_sort.UNICODE_SORT


def _tags_and_translations(context, vocab, lang, lang_fallback):
    try:
        tags = logic.get_action('tag_list')(context, {'vocabulary_id': vocab})
        tag_translations = helpers.translate(tags, lang, lang_fallback)
        return sorted([(t, tag_translations[t]) for t in tags],
                      key=operator.itemgetter(1))
    except logic.NotFound:
        return []


class ECPortalDatasetForm(p.SingletonPlugin):
    p.implements(p.IDatasetForm, inherit=True)
    p.implements(p.ITemplateHelpers)

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

    def setup_template_variables(self, context, data_dict=None,
                                 package_type=None):
        c = p.toolkit.c

        ckan_lang = str(helpers.current_locale())
        ckan_lang_fallback = str(helpers.fallback_locale())

        c.licences = sorted(model.Package.get_license_options(),
                            key=operator.itemgetter(1))
        default_licence = (
            "Europa Legal Notice",
            "http://ec.europa.eu/open-data/kos/licence/EuropeanCommission")
        c.licences = filter(lambda l: l != default_licence, c.licences)
        c.licences.insert(0, default_licence)

        c.is_sysadmin = Authorizer().is_sysadmin(c.user)

        c.status = _tags_and_translations(
            context, STATUS_VOCAB_NAME, ckan_lang, ckan_lang_fallback)
        c.interoperability_levels = _tags_and_translations(
            context, INTEROP_VOCAB_NAME, ckan_lang, ckan_lang_fallback)
        c.type_of_dataset = _tags_and_translations(
            context, DATASET_TYPE_VOCAB_NAME, ckan_lang, ckan_lang_fallback)
        c.geographical_coverage = _tags_and_translations(
            context, GEO_VOCAB_NAME, ckan_lang, ckan_lang_fallback)
        c.languages = _tags_and_translations(
            context, LANGUAGE_VOCAB_NAME, ckan_lang, ckan_lang_fallback)
        c.temporal_granularity = [(u'', u'')] + _tags_and_translations(
            context, TEMPORAL_VOCAB_NAME, ckan_lang, ckan_lang_fallback)

        # publisher IDs and name translations
        c.publishers = helpers.groups_available(c.user)

        # get new group name if group ID in query string
        new_group_id = pylons.request.params.get('groups__0__id')
        if new_group_id:
            try:
                data = {'id': new_group_id}
                new_group = p.toolkit.get_action('group_show')(context, data)
                c.new_group = new_group['name']
            except p.toolkit.ObjectNotFound:
                c.new_group = None

        # find extras that are not part of our schema
        c.additional_extras = []
        schema_keys = self.form_to_db_schema().keys()
        if c.pkg_dict:
            extras = c.pkg_dict.get('extras', [])
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
                logic.check_access('package_change_state', context)
                c.auth_for_change_state = True
            except logic.NotAuthorized:
                c.auth_for_change_state = False

    def form_to_db_schema_options(self, options):
        'Use ODP schema for WUI and API calls'
        schema = self.form_to_db_schema()

        if options.get('api'):
            schema.update({
                'keywords': logic.schema.default_tags_schema(),
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
                    'name': [ignore_missing, ecportal_name_validator,
                             package_name_validator, unicode],
                    'title': [ignore_missing, unicode]
                })

        return schema

    def form_to_db_schema(self, package_type=None):
        schema = logic.schema.package_form_schema()
        schema.update({
            'name': [not_empty, unicode, ecportal_name_validator,
                     package_name_validator],
            'license_id': [ignore_missing, reduce_list, map_licenses, unicode],
            'keyword_string': [ignore_missing, keyword_string_convert],
            'alternative_title': [ignore_missing, unicode, convert_to_extras],
            'description': [not_empty, unicode],
            'url': [not_empty, unicode],
            'status': [not_empty, convert_to_tags(STATUS_VOCAB_NAME)],
            'identifier': [ignore_missing, unicode, convert_to_extras],
            'interoperability_level': [ignore_missing,
                                       convert_to_tags(INTEROP_VOCAB_NAME)],
            'type_of_dataset': [ignore_missing,
                                convert_to_tags(DATASET_TYPE_VOCAB_NAME)],
            'published_by': [not_empty, unicode, publisher_exists,
                             convert_to_groups('name')],
            'capacity': [ignore_missing, unicode, default(u'private'),
                         convert_to_groups('capacity')],
            'release_date': [ignore_missing, ecportal_date_to_db,
                             convert_to_extras],
            'modified_date': [ignore_missing, ecportal_date_to_db,
                              convert_to_extras],
            'accrual_periodicity': [ignore_missing, unicode,
                                    convert_to_extras],
            'temporal_coverage_from': [ignore_missing, ecportal_date_to_db,
                                       convert_to_extras],
            'temporal_coverage_to': [ignore_missing, ecportal_date_to_db,
                                     convert_to_extras],
            'temporal_granularity': [ignore_missing,
                                     convert_to_tags(TEMPORAL_VOCAB_NAME)],
            'geographical_coverage': [ignore_missing,
                                      convert_to_tags(GEO_VOCAB_NAME)],
            'language': [ignore_missing, convert_to_tags(LANGUAGE_VOCAB_NAME)],
            'metadata_language': [ignore_missing,
                                  member_of_vocab(LANGUAGE_VOCAB_NAME),
                                  convert_to_extras],
            'version_description': [ignore_missing, unicode,
                                    convert_to_extras],
            'rdf': [ignore_missing, unicode, update_rdf, convert_to_extras],
            'contact_name': [ignore_missing, unicode, convert_to_extras],
            'contact_email': [ignore_missing, requires_field('contact_name'),
                              unicode, convert_to_extras],
            'contact_address': [ignore_missing, requires_field('contact_name'),
                                unicode, convert_to_extras],
            'contact_telephone': [ignore_missing,
                                  requires_field('contact_name'),
                                  unicode, convert_to_extras],
            'contact_webpage': [ignore_missing, requires_field('contact_name'),
                                unicode, convert_to_extras],
            '__after': [duplicate_extras_key,
                        rename('keywords', 'tags'),
                        rename('description', 'notes')],
        })

        schema['groups'].update({
            'capacity': [ignore_missing, unicode]
        })

        schema['resources'].update({
            'type': [ignore_missing, unicode, convert_resource_type]
        })

        return schema

    def db_to_form_schema(data, package_type=None):
        schema = logic.schema.package_form_schema()
        schema.update({
            'id': [ignore_missing, unicode],
            'tags': {
                '__extras': [keep_extras, free_tags_only]
            },
            'alternative_title': [convert_from_extras, ignore_missing],
            'status': [convert_from_tags(STATUS_VOCAB_NAME), ignore_missing],
            'identifier': [convert_from_extras, ignore_missing],
            'interoperability_level': [convert_from_tags(INTEROP_VOCAB_NAME),
                                       ignore_missing],
            'type_of_dataset': [convert_from_tags(DATASET_TYPE_VOCAB_NAME),
                                ignore_missing],
            'published_by': [convert_from_groups('name')],
            'capacity': [convert_from_groups('capacity')],
            'release_date': [convert_from_extras, ignore_missing],
            'modified_date': [convert_from_extras, ignore_missing],
            'accrual_periodicity': [convert_from_extras, ignore_missing],
            'temporal_coverage_from': [convert_from_extras, ignore_missing],
            'temporal_coverage_to': [convert_from_extras, ignore_missing],
            'temporal_granularity': [convert_from_tags(TEMPORAL_VOCAB_NAME),
                                     ignore_missing],
            'geographical_coverage': [convert_from_tags(GEO_VOCAB_NAME),
                                      ignore_missing],
            'language': [convert_from_tags(LANGUAGE_VOCAB_NAME),
                         ignore_missing],
            'metadata_language': [convert_from_extras, ignore_missing],
            'version_description': [convert_from_extras, ignore_missing],
            'rdf': [convert_from_extras, ignore_missing],
            'contact_name': [convert_from_extras, ignore_missing],
            'contact_email': [convert_from_extras, ignore_missing],
            'contact_address': [convert_from_extras, ignore_missing],
            'contact_telephone': [convert_from_extras, ignore_missing],
            'contact_webpage': [convert_from_extras, ignore_missing],
            'license_url': [ignore_missing],
            'license_title': [ignore_missing],
            'metadata_created': [ignore_missing],
            'metadata_modified': [ignore_missing],
            '__after': [duplicate_extras_key,
                        rename('tags', 'keywords'),
                        rename('notes', 'description')]
        })

        schema['groups'].update({
            'name': [not_empty, unicode],
            'title': [ignore_missing],
            'capacity': [ignore_missing, unicode]
        })

        schema['resources'].update({
            'created': [ignore_missing],
            'position': [not_empty],
            'last_modified': [ignore_missing],
            'cache_last_updated': [ignore_missing],
            'webstore_last_updated': [ignore_missing]
        })

        return schema

    def check_data_dict(self, data_dict):
        return

    def get_helpers(self):
        return {'current_url': helpers.current_url,
                'current_locale': helpers.current_locale,
                'root_url': helpers.root_url,
                'format_description': helpers.format_description,
                'recent_updates': helpers.recent_updates,
                'top_publishers': helpers.top_publishers,
                'current_date': helpers.current_date,
                'group_facets_by_field': helpers.group_facets_by_field,
                'groups_available': helpers.groups_available}


class ECPortalPublisherForm(p.SingletonPlugin):
    p.implements(p.IGroupForm, inherit=True)
    p.implements(p.IRoutes)

    def before_map(self, map):
        controller = 'ckanext.organizations.controllers:OrganizationController'
        map.connect('/publisher/users/{id}', controller=controller,
                    action='users')
        map.connect('/publisher/apply/{id}', controller=controller,
                    action='apply')
        map.connect('/publisher/apply', controller=controller, action='apply')
        map.connect('/publisher/edit/{id}', controller='group', action='edit')
        map.connect('/publisher/history/{id}', controller='group',
                    action='history')
        map.connect('/publisher/new', controller='group', action='new')
        map.connect('/publisher/{id}', controller='group', action='read')
        map.connect('/publisher',  controller='group', action='index')
        map.redirect('/publishers', '/publisher')
        map.redirect('/organization/{url:.*}', '/publisher/{url}')
        return map

    def after_map(self, map):
        return map

    def group_types(self):
        return ['organization']

    def is_fallback(self):
        return True

    def index_template(self):
        return 'publisher/index.html'

    def read_template(self):
        return 'publisher/read.html'

    def new_template(self):
        return 'publisher/new.html'

    def edit_template(self):
        return 'publisher/edit.html'

    def group_form(self):
        return 'publisher/form.html'

    def history_template(self):
        return 'publisher/history.html'

    def package_form(self):
        return 'publisher/package_form.html'

    def form_to_db_schema(self):
        '''Custom group schema for EC portal.

        Does not allow an existing group's name to be changed.
        '''
        schema = ckan.logic.schema.group_form_schema()
        schema['name'].append(group_name_unchanged)

        return schema

    def db_to_form_schema(self):
        return ckan.logic.schema.group_form_schema()

    def check_data_dict(self, data_dict):
        pass

    def setup_template_variables(self, context, data_dict):
        c = p.toolkit.c

        c.user_groups = c.userobj.get_groups('organization')
        local_ctx = {'model': model, 'session': model.Session,
                     'user': c.user or c.author}

        try:
            logic.check_access('group_create', local_ctx)
            c.is_superuser_or_groupadmin = True
        except logic.NotAuthorized:
            c.is_superuser_or_groupadmin = False

        if 'group' in context:
            group = context['group']

            # Only show possible groups where the current user is a member
            c.possible_parents = c.userobj.get_groups('organization', 'admin')
            c.parent = None
            grps = group.get_groups('organization')
            if grps:
                c.parent = grps[0]
            c.users = group.members_of_type(model.User)
