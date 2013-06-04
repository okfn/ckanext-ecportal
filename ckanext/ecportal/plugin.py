import sqlalchemy.exc
from pylons.i18n.translation import get_lang

import ckan.model as model
import ckan.plugins as p
import ckan.config.routing as routing

import ckanext.ecportal.logic as ecportal_logic
import ckanext.ecportal.auth as ecportal_auth
import ckanext.ecportal.searchcloud as searchcloud

import logging
log = logging.getLogger(__file__)


class ECPortalPlugin(p.SingletonPlugin):
    p.implements(p.IConfigurable)
    p.implements(p.IConfigurer)
    p.implements(p.IRoutes)
    p.implements(p.IActions)
    p.implements(p.IAuthFunctions)
    p.implements(p.IPackageController, inherit=True)

    def get_auth_functions(self):
        return {
            'package_update': ecportal_auth.package_update,
            'show_package_edit_button': ecportal_auth.show_package_edit_button,
            'group_create': ecportal_auth.group_create,
            'user_create': ecportal_auth.user_create,
            'purge_revision_history': ecportal_auth.purge_revision_history,
        }

    def get_actions(self):
        return {
            'group_list': ecportal_logic.group_list,
            'group_update': ecportal_logic.group_update,
            'group_show': ecportal_logic.group_show,
            'purge_revision_history': ecportal_logic.purge_revision_history,
            'user_create': ecportal_logic.user_create,
            'user_update': ecportal_logic.user_update,
            'package_show': ecportal_logic.package_show
        }

    def configure(self, config):
        self.site_url = config.get('ckan.site_url')

        # do not automatically notify for now for performance reasons
        def no_notify(entity, operation=None):
            return

        for plugin in p.PluginImplementations(p.IDomainObjectModification):
            if plugin.name in ('QAPlugin', 'WebstorerPlugin'):
                plugin.notify = no_notify

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

        # home map
        home_controller = 'ckanext.ecportal.controllers:ECPortalHomeController'
        with routing.SubMapper(map, controller=home_controller) as m:
            m.connect('home', '/', action='index')
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
        '''
        We don't make any changes to the search_params, just log
        the search string to the database for later analysis.
        '''
        search_string = search_params.get('q') or ''
        # do some clean up of the search string so that the analysis
        # will be easier later
        search_string = searchcloud.unify_terms(search_string, max_length=200)
        if not search_string:
            return search_params
        # Let's get the current langauge via Pylons (then this plugin
        # is robust to URL changes)
        lang = get_lang()
        if lang is not None:
            # get_lang returns a list of languages
            lang = lang[0]
        else:
            lang = 'default'
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
