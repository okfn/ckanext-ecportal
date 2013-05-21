import ckan.plugins as p

import ckanext.ecportal.logic as ecportal_logic
import ckanext.ecportal.auth as ecportal_auth


class ECPortalPlugin(p.SingletonPlugin):
    p.implements(p.IConfigurable)
    p.implements(p.IConfigurer)
    p.implements(p.IRoutes)
    p.implements(p.IActions)
    p.implements(p.IAuthFunctions)

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

        return map

    def after_map(self, map):
        return map
