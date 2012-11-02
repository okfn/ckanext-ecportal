import ckan.plugins as p
import ckan.logic.action.update as update
import ckan.logic.action.get as get
import ckan.logic as logic
import logging
import ckan.lib.navl.dictization_functions
import ckan.plugins as plugins
import ckan.lib.plugins as lib_plugins
import ckan.lib.dictization as d
import ckan.lib.dictization.model_dictize as model_dictize
import ckan.config.routing as routing

import ckanext.ecportal.auth as ecportal_auth

log = logging.getLogger('ckan.logic')

# define some shortcuts
validate = ckan.lib.navl.dictization_functions.validate
check_access = logic.check_access
NotFound = logic.NotFound

##Wrapper around group update, *always* adds on packages.

def group_update(context, data_dict):

    model = context['model']
    user = context['user']
    session = context['session']

    id = data_dict.get('id')
    group = model.Group.get(id)

    if group is None:
        raise NotFound('Group was not found.')

    members = session.query(model.Member.table_id).filter_by(
        table_name='package',
        group_id=group.id,
        state='active'
    ).all()
    packages = []

    for member in members:
        packages.append({'name': member[0]})
    data_dict['packages'] = packages

    return update.group_update(context, data_dict)

###########################################################################
##Copy of group_dictize form core only change removing pacakge_list dictize
###########################################################################

def group_dictize(group, context):
    model = context['model']
    result_dict = d.table_dictize(group, context)

    result_dict['display_name'] = group.display_name

    result_dict['extras'] = model_dictize.extras_dict_dictize(
        group._extras, context)

    context['with_capacity'] = True

    result_dict['tags'] = model_dictize.tag_list_dictize(
        model_dictize._get_members(context, group, 'tags'),
        context)

    result_dict['groups'] = model_dictize.group_list_dictize(
        model_dictize._get_members(context, group, 'groups'),
        context)

    result_dict['users'] = model_dictize.user_list_dictize(
        model_dictize._get_members(context, group, 'users'),
        context)

    context['with_capacity'] = False

    if context.get('for_view'):
        for item in plugins.PluginImplementations(plugins.IGroupController):
            result_dict = item.before_view(result_dict)

    return result_dict

#####################################################################
##Copy of core group show only change is using group_dictize above.
#####################################################################

def group_show(context, data_dict):
    '''Shows group details'''
    model = context['model']
    id = data_dict['id']
    group = model.Group.get(id)
    context['group'] = group

    if group is None or group.state == u'deleted':
        raise NotFound

    check_access('group_show',context, data_dict)

    group_dict = group_dictize(group, context)

    for item in plugins.PluginImplementations(plugins.IGroupController):
        item.read(group)

    group_plugin = lib_plugins.lookup_group_plugin(group_dict['type'])
    try:
        schema = group_plugin.db_to_form_schema_options({
            'type':'show',
            'api': 'api_version' in context,
            'context': context })
    except AttributeError:
        schema = group_plugin.db_to_form_schema()

    if schema:
        package_dict, errors = validate(group_dict, schema, context=context)

    return group_dict

def group_list(context, data_dict):
    return sorted(
        get.group_list(context, data_dict),
        key=lambda x:x['display_name']
    )

def purge_revision_history(context, data_dict):
    '''
    Purge a given publisher's unused revision history.
    '''

    check_access('purge_revision_history', context, data_dict)

    model = context['model']
    engine = model.meta.engine
    group_identifier = logic.get_or_bust(data_dict, 'group')
    group = model.Group.get(group_identifier)

    if not group:
        raise NotFound

    RESOURCE_IDS_SQL = '''
        SELECT resource.id FROM resource
        JOIN resource_group ON resource.resource_group_id = resource_group.id
        JOIN member ON member.table_id = resource_group.package_id
        JOIN "group" ON "group".id = member.group_id
        WHERE "group".name      = %s
          AND "group".type      = 'organization'
          AND member.table_name = 'package'
          AND resource.state    = 'deleted'
    '''

    DELETE_REVISIONS_SQL = '''
        DELETE FROM resource_revision
            WHERE id IN ({sql})
    '''.format(sql=RESOURCE_IDS_SQL)

    # Not necessary to use a sub-select, but it allows re-use of sql statement
    # and this isn't performance critical code.
    DELETE_RESOURCES_SQL = '''
        DELETE FROM resource WHERE id IN ({sql})
    '''.format(sql=RESOURCE_IDS_SQL)

    try:
        number_revisions_deleted = engine.execute(
                DELETE_REVISIONS_SQL,
                group.name
            ).rowcount

        number_resources_deleted = engine.execute(
                DELETE_RESOURCES_SQL,
                group.name
            ).rowcount
        return {
            'number_revisions_deleted': number_revisions_deleted,
            'number_resources_deleted': number_resources_deleted
        }

    except Exception, e:
        raise logic.ActionError('Error executing sql: %s' % e)

class ECPortalPlugin(p.SingletonPlugin):
    p.implements(p.IConfigurable)
    p.implements(p.IConfigurer)
    p.implements(p.IRoutes)
    p.implements(p.IActions)
    p.implements(p.IAuthFunctions)

    def get_actions(self):

        return {'group_list': group_list,
                'group_update': group_update,
                'group_show': group_show,
                'purge_revision_history': purge_revision_history,
               }

    def configure(self, config):
        self.site_url = config.get('ckan.site_url')

        ## Do not automatically notify for now for performance reasons
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

        user_controller = 'ckanext.ecportal.controllers:ECPortalUserController'

        with routing.SubMapper(map, controller=user_controller) as m:
            m.connect('/user/edit', action='edit')
            # Note: openid users have slashes in their ids, so need the wildcard
            # in the route.
            m.connect('/user/edit/{id:.*}', action='edit')
            m.connect('/user/reset/{id:.*}', action='perform_reset')
            m.connect('/user/login', action='login')
            m.connect('/user/_logout', action='logout')
            m.connect('/user/logged_in', action='logged_in')
            m.connect('/user/logged_out', action='logged_out')
            m.connect('/user/logged_out_redirect', action='logged_out_page')
            m.connect('/user/reset', action='request_reset')
            m.connect('/user/me', action='me')
            m.connect('/user/set_lang/{lang}', action='set_lang')
            m.connect('/user/{id:.*}', action='read')
            m.connect('/user', action='index')
        map.redirect('/user/register', '/not_found')
        return map

    def after_map(self, map):
        return map

    ##
    ## IAuthFunctions implementation
    ##

    def get_auth_functions(self):
        return {
            'package_update': ecportal_auth.package_update,
            'show_package_edit_button': ecportal_auth.show_package_edit_button,
            'group_create': ecportal_auth.group_create,
            'user_create': ecportal_auth.user_create,
            'purge_revision_history': ecportal_auth.purge_revision_history,
        }
