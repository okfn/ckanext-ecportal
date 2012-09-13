import ckan.plugins as p
import ckan.logic.action.update as update
import ckan.logic as logic
import logging
import ckan.lib.navl.dictization_functions
import ckan.plugins as plugins
import ckan.lib.plugins as lib_plugins
import ckan.lib.dictization as d

import ckan.lib.dictization.model_dictize as model_dictize

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

    if group is None:
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

class ECPortalPlugin(p.SingletonPlugin):
    p.implements(p.IConfigurable)
    p.implements(p.IConfigurer)
    p.implements(p.IRoutes)
    p.implements(p.IActions)

    def get_actions(self):

        return {'group_update': group_update,
                'group_show': group_show}

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
        map.redirect('/user/register', '/not_found')
        return map

    def after_map(self, map):
        return map
