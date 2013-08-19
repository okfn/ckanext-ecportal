import logging
import json
import sqlalchemy.exc
import pylons.config
import pylons

import ckan.model as model
import ckan.plugins as p
import ckan.config.routing as routing
import ckanext.multilingual.plugin as multilingual

import ckanext.ecportal.logic as ecportal_logic
import ckanext.ecportal.auth as ecportal_auth
import ckanext.ecportal.searchcloud as searchcloud
import ckanext.ecportal.helpers as helpers
import ckanext.ecportal.unicode_sort as unicode_sort

log = logging.getLogger(__file__)
UNICODE_SORT = unicode_sort.UNICODE_SORT

LANGS = ['en', 'fr', 'de', 'it', 'es', 'pl', 'ga', 'lv', 'bg',
         'lt', 'cs', 'da', 'nl', 'et', 'fi', 'el', 'hu', 'mt',
         'pt', 'ro', 'sk', 'sl', 'sv', 'hr']

KEYS_TO_IGNORE = ['state', 'revision_id', 'id',  # title done seperately
                  'metadata_created', 'metadata_modified', 'site_id',
                  'data_dict', 'rdf']


class MulitlingualDataset(multilingual.MultilingualDataset):
    def before_index(self, search_data):
        # same code as in ckanext multilingual except language codes and
        # where mareked

        default_lang = search_data.get(
            'lang_code',
            pylons.config.get('ckan.locale_default', 'en')
        )

        # translate title
        title = search_data.get('title')
        search_data['title_' + default_lang] = title
        title_translations = p.toolkit.get_action('term_translation_show')(
            {'model': model},
            {'terms': [title],
             'lang_codes': LANGS})

        for translation in title_translations:
            title_field = 'title_' + translation['lang_code']
            search_data[title_field] = translation['term_translation']

        # EC change add sort order field.
        for lang in LANGS:
            title_field = 'title_' + lang
            title_value = search_data.get(title_field)
            title_string_field = 'title_string_' + lang
            if not title_value:
                title_value = title

            # Strip accents first and if equivilant do next stage comparison.
            # Leaving space and concatonating is to avoid having todo a real
            # 2 level sort.
            sortable_title = \
                unicode_sort.strip_accents(title_value) + '   ' + title_value
            search_data[title_string_field] = \
                sortable_title.translate(UNICODE_SORT)

        ##########################################

        ## translate rest
        all_terms = []
        for key, value in search_data.iteritems():
            if key in KEYS_TO_IGNORE or key.startswith('title'):
                continue
            if isinstance(value, list):
                all_terms.extend(value)
            elif not isinstance(value, basestring):
                continue
            else:
                all_terms.append(value)

        field_translations = p.toolkit.get_action('term_translation_show')(
            {'model': model},
            {'terms': all_terms,
             'lang_codes': LANGS})

        text_field_items = dict(('text_' + lang, []) for lang in LANGS)

        text_field_items['text_' + default_lang].extend(all_terms)

        for translation in sorted(field_translations):
            lang_field = 'text_' + translation['lang_code']
            text_field_items[lang_field].append(
                translation['term_translation'])

        for key, value in text_field_items.iteritems():
            search_data[key] = ' '.join(value)

        return search_data

    def before_search(self, search_params):
        lang_set = set(LANGS)
        current_lang = pylons.request.environ['CKAN_LANG']
        # fallback to default locale if locale not in suported langs
        if not current_lang in lang_set:
            current_lang = pylons.config.get('ckan.locale_default')
        # fallback to english if default locale is not supported
        if not current_lang in lang_set:
            current_lang = 'en'
        # treat current lang differenly so remove from set
        lang_set.remove(current_lang)

        # weight current lang more highly
        query_fields = 'title_%s^8 text_%s^4' % (current_lang, current_lang)

        for lang in lang_set:
            query_fields += ' title_%s^2 text_%s' % (lang, lang)

        search_params['qf'] = query_fields

        search_string = search_params.get('q') or ''
        if not search_string and not search_params.get('sort'):
            search_params['sort'] = 'title_string_%s asc' % current_lang

        return search_params


class ECPortalPlugin(p.SingletonPlugin):
    p.implements(p.IConfigurer)
    p.implements(p.IRoutes)
    p.implements(p.IActions)
    p.implements(p.IAuthFunctions)
    p.implements(p.IPackageController, inherit=True)
    p.implements(p.ITemplateHelpers)

    def get_auth_functions(self):
        return {
            'package_update': ecportal_auth.package_update,
            'show_package_edit_button': ecportal_auth.show_package_edit_button,
            'group_create': ecportal_auth.group_create,
            'user_create': ecportal_auth.user_create,
            'purge_revision_history': ecportal_auth.purge_revision_history,
            'purge_package_extra_revision':
            ecportal_auth.purge_revision_history,
            'purge_task_data': ecportal_auth.purge_task_data
        }

    def get_actions(self):
        return {
            'group_list': ecportal_logic.group_list,
            'group_update': ecportal_logic.group_update,
            'group_show': ecportal_logic.group_show,
            'purge_revision_history': ecportal_logic.purge_revision_history,
            'purge_package_extra_revision':
            ecportal_logic.purge_package_extra_revision,
            'purge_task_data': ecportal_logic.purge_task_data,
            'user_create': ecportal_logic.user_create,
            'user_update': ecportal_logic.user_update,
            'package_show': ecportal_logic.package_show
        }

    def update_config(self, config):
        p.toolkit.add_template_directory(config, 'templates')
        p.toolkit.add_public_directory(config, 'public')

        # ECPortal should use group auth
        config['ckan.auth.profile'] = 'publisher'

    def before_map(self, map):
        # disable user list, password reset and user registration pages
        map.redirect('/user', '/not_found')
        map.redirect('/user/reset', '/not_found')
        map.redirect('/user/register', '/not_found')

        # disable dataset history page
        map.redirect('/dataset/history/{url:.*}', '/not_found')
        map.redirect('/dataset/history_ajax/{url:.*}', '/not_found')

        # search cloud map
        searchcloud_controller = \
            'ckanext.ecportal.controllers:ECPortalSearchCloudAdminController'
        with routing.SubMapper(map, controller=searchcloud_controller) as m:
            m.connect('/searchcloud', action='index')
            m.connect('/searchcloud/', action='index')
            m.connect('/searchcloud/{action}')
        return map

    def after_map(self, map):
        return map

    def before_search(self, search_params):
        search_string = search_params.get('q') or ''

        # for search cloud we don't make any changes to the search_params,
        # just log the search string to the database for later analysis.

        # do some clean up of the search string so that the analysis
        # will be easier later
        search_string = searchcloud.unify_terms(search_string, max_length=200)
        if not search_string:
            return search_params
        lang = str(helpers.current_locale())
        try:
            # Unfortunately a nested sessin doesn't behave the way we want,
            # failing to actually commit the change made.
            # We can either create a separate connection for this
            # functionality on each request (potentially costly),
            # or just commit at this point on the basis that for a search
            # request, no changes that can't be committed will have been
            # saved to the database. For now, we choose the latter.
            ## model.Session.begin_nested() # establish a savepoint
            searchcloud.track_term(model.Session, lang, search_string)
        except sqlalchemy.exc.ProgrammingError, e:
            # We don't want the non-existence of the search_query table to
            # crash searches, we just won't log queries
            log.error(e)
            if 'relation "search_query" does not exist' in str(e):
                log.error('Please run the paster searchcloud-install-tables '
                          'command to set up the correct tables for '
                          'search logging')
                model.Session.rollback()
            else:
                raise
        except Exception, e:
            # Exceptions from here don't appear to bubble up, so we make sure
            # to log them so that someone debugging a problem has a chance to
            # find the source error.
            log.error(e)
            raise
        else:
            model.Session.commit()
            log.debug(
                'Inserted the term %r into the search_query table'
                ' and committed successfully',
                search_string
            )
        return search_params

    def before_index(self, pkg_dict):
        title = pkg_dict.get('title', pkg_dict.get('name'))
        # Strip accents first and if equivilant do next stage comparison.
        # Leaving space and concatenating is to avoid having todo a real
        # 2 level sort.
        pkg_dict['title_sort'] = (unicode_sort.strip_accents(title) +
                                  '   '
                                  + title).translate(UNICODE_SORT)

        # set 'metadata_modified' field to value of metadata_modified if
        # not present (this field is used to sort datasets according to
        # their last update date).
        if not 'modified_date' in pkg_dict:
            pkg_dict['modified_date'] = pkg_dict['metadata_modified']
        else:
            # modify dates (SOLR is quite picky with dates, and only accepts
            # ISO dates with UTC time (i.e trailing Z)
            pkg_dict['modified_date'] = helpers.ecportal_date_to_iso(
                pkg_dict['modified_date']) + 'Z'

        return pkg_dict

    def get_helpers(self):
        return {'current_url': helpers.current_url,
                'current_locale': helpers.current_locale,
                'root_url': helpers.root_url,
                'format_description': helpers.format_description,
                'recent_updates': helpers.recent_updates,
                'top_publishers': helpers.top_publishers,
                'current_date': helpers.current_date,
                'group_facets_by_field': helpers.group_facets_by_field,
                'groups_available': helpers.groups_available,
                'ecportal_date_to_iso': helpers.ecportal_date_to_iso,
                'most_viewed_datasets': helpers.most_viewed_datasets,
                'approved_search_terms': helpers.approved_search_terms}


class ECPortalHomepagePlugin(p.SingletonPlugin):
    p.implements(p.IConfigurable)
    p.implements(p.ITemplateHelpers)

    home_content = None
    maintenance = None

    def _read_json_file(self, file_path):
        try:
            with open(file_path, 'r') as f:
                return json.loads(f.read())
        except IOError, e:
            log.error('Cannot open homepage content JSON file {0}'.format(
                file_path))
            log.error(e)
        except ValueError, e:
            log.error('Cannot load homepage content JSON file {0}'.format(
                file_path))
            log.error(e)

    def configure(self, config):
        content_path = config.get('ckan.home.content')
        if content_path:
            log.info('Reading homepage content from {0}'.format(content_path))
            self.home_content = self._read_json_file(content_path)

        maintenance_path = config.get('ckan.home.maintenance')
        if maintenance_path:
            log.info('Reading maintenance message from {0}'.format(
                maintenance_path))
            self.maintenance = self._read_json_file(maintenance_path)

    def get_helpers(self):
        return {'homepage_content': self.homepage_content,
                'maintenance_message': self.maintenance_message}

    def homepage_content(self, language='en'):
        if self.home_content:
            title = (self.home_content.get('title', {}).get(language) or
                     self.home_content.get('title', {}).get('en'))
            body = (self.home_content.get('body', {}).get(language) or
                    self.home_content.get('body', {}).get('en'))
            return {'title': title, 'body': p.toolkit.literal(body)}

    def maintenance_message(self, language='en'):
        if self.maintenance:
            message = (self.maintenance.get('message', {}).get(language) or
                       self.maintenance.get('message', {}).get('en'))
            maintenance_class = self.maintenance.get('class', 'red')
            return {'message': message, 'class': maintenance_class}
