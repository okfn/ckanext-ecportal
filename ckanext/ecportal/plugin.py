import logging
import operator

import ckan.plugins as p
import ckan.logic.action.create as create
import ckan.logic.action.get as get
import ckan.logic.action.update as update
import ckan.logic as logic
import ckan.lib.navl.dictization_functions
import ckan.plugins as plugins
import ckan.lib.plugins as lib_plugins
import ckan.lib.dictization as d
import ckan.lib.dictization.model_dictize as model_dictize
import ckan.config.routing as routing

import ckanext.ecportal.auth as ecportal_auth
import ckanext.ecportal.schema as schema

log = logging.getLogger('ckan.logic')

# define some shortcuts
validate = ckan.lib.navl.dictization_functions.validate
check_access = logic.check_access
NotFound = logic.NotFound


# Wrapper around group update, *always* adds on packages.

def group_update(context, data_dict):
    '''Update a group.

    You must be authorized to edit the group.

    Note: unlike ``group_create()``, the list of packages belonging to the
          group is ignored.  This is a deviation from the standard CKAN API
          specific to ECODP.

    :param id: the name or id of the group to update
    :type id: string

    :param name: the name of the group, a string between 2 and 100 characters
        long, containing only lowercase alphanumeric characters, ``-`` and
        ``_``
    :type name: string
    :param title: the title of the group (optional)
    :type title: string
    :param description: the description of the group (optional)
    :type description: string
    :param image_url: the URL to an image to be displayed on the group's page
        (optional)
    :type image_url: string
    :param type: the type of the group (optional), ``IGroupForm`` plugins
        associate themselves with different group types and provide custom
        group handling behaviour for these types
    :type type: string
    :param state: the current state of the group, e.g. ``'active'`` or
        ``'deleted'``, only active groups show up in search results and
        other lists of groups, this parameter will be ignored if you are not
        authorized to change the state of the group (optional, default:
        ``'active'``)
    :type state: string
    :param approval_status: (optional)
    :type approval_status: string
    :param extras: the group's extras (optional), extras are arbitrary
        (key: value) metadata items that can be added to groups, each extra
        dictionary should have keys ``'key'`` (a string), ``'value'`` (a
        string), and optionally ``'deleted'``
    :type extras: list of dataset extra dictionaries
    :param groups: the groups that belong to the group, a list of dictionaries
        each with key ``'name'`` (string, the id or name of the group) and
        optionally ``'capacity'`` (string, the capacity in which the group is
        a member of the group)
    :type groups: list of dictionaries
    :param users: the users that belong to the group, a list of dictionaries
        each with key ``'name'`` (string, the id or name of the user) and
        optionally ``'capacity'`` (string, the capacity in which the user is
        a member of the group)
    :type users: list of dictionaries

    :returns: the updated group
    :rtype: dictionary
    '''
    model = context['model']
    user = context['user']
    session = context['session']

    id = data_dict.get('id')
    group = model.Group.get(id)

    if group is None:
        raise NotFound('Group was not found.')

    # If the context requires it, then update the packages, as would normally
    # happen with the group_update action.
    if not context.get('ecodp_update_packages', False):

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

    if context.get('ecodp_with_package_list', False):
        result_dict['packages'] = d.obj_list_dictize(
            model_dictize._get_members(context, group, 'packages'),
            context)

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
    '''Return the details of a group.

    :param id: the id or name of the group
    :type id: string

    :rtype: dictionary
    '''
    model = context['model']
    id = data_dict['id']
    group = model.Group.get(id)
    context['group'] = group

    if group is None or group.state == u'deleted':
        raise NotFound

    check_access('group_show', context, data_dict)

    group_dict = group_dictize(group, context)

    for item in plugins.PluginImplementations(plugins.IGroupController):
        item.read(group)

    group_plugin = lib_plugins.lookup_group_plugin(group_dict['type'])
    try:
        schema = group_plugin.db_to_form_schema_options({
            'type': 'show',
            'api': 'api_version' in context,
            'context': context
        })
    except AttributeError:
        schema = group_plugin.db_to_form_schema()

    if schema:
        package_dict, errors = validate(group_dict, schema, context=context)

    return group_dict


def group_list(context, data_dict):
    '''Return a list of the names of the site's groups.

    :param order_by: the field to sort the list by, must be ``'name'`` or
      ``'packages'`` (optional, default: ``'name'``) Deprecated use sort.
    :type order_by: string
    :param sort: sorting of the search results.  Optional.  Default:
        "name asc" string of field name and sort-order. The allowed fields are
        'name' and 'packages'
    :type sort: string
    :param groups: a list of names of the groups to return, if given only
        groups whose names are in this list will be returned (optional)
    :type groups: list of strings
    :param all_fields: return full group dictionaries instead of  just names
        (optional, default: ``False``)
    :type all_fields: boolean

    :rtype: list of strings
    '''
    groups = get.group_list(context, data_dict)

    if context.get('for_view', False):
        # In the context of the web interface, and if the request comes from an
        # anonymous user, then only present publishers with published datasets.

        model = context['model']
        userobj = model.User.get(context['user'])

        if not userobj:  # anonymous user
            # Depending upon the context, group['packages'] may be either a
            # count of the packages, or the actual list of packages.
            if groups and isinstance(groups[0]['packages'], int):
                groups = [g for g in groups if g['packages'] > 0]
            else:
                groups = [g for g in groups if len(g['packages']) > 0]

    return sorted(groups, key=operator.itemgetter('display_name'))


def package_show(context, data_dict):
    '''Override package_show to sort the resources by name'''
    result = get.package_show(context, data_dict)
    if 'resources' in result:
        result['resources'].sort(key=operator.itemgetter('name'))
    return result


def purge_revision_history(context, data_dict):
    '''
    Purge a given publisher's unused revision history.

    :param group: the name or id of the publisher
    :type group: string

    :returns: number of resources and revisions purged.
    :rtype: dictionary
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


def user_create(context, data_dict):
    '''Create a new user.

    You must be authorized to create users.

    Wrapper around core user_create action ensures that the ECODP custom user
    schema are used.

    :param name: the name of the new user, a string between 2 and 100
        characters in length, containing only alphanumeric characters, ``-``
        and ``_``
    :type name: string
    :param email: the email address for the new user (optional)
    :type email: string
    :param password: the password of the new user, a string of at least 4
        characters
    :type password: string
    :param id: the id of the new user (optional)
    :type id: string
    :param fullname: the full name of the new user (optional)
    :type fullname: string
    :param about: a description of the new user (optional)
    :type about: string
    :param openid: (optional)
    :type openid: string

    :returns: the newly created user
    :rtype: dictionary
    '''
    if 'schema' not in context:
        new_context = context.copy()  # Don't modify caller's context
        new_context['schema'] = schema.default_user_schema()
    else:
        new_context = context
    return create.user_create(new_context, data_dict)


def user_update(context, data_dict):
    '''Update a user account.

    Normal users can only update their own user accounts. Sysadmins can update
    any user account.

    For further parameters see ``user_create()``.

    :param id: the name or id of the user to update
    :type id: string

    :returns: the updated user account
    :rtype: dictionary

    '''
    if 'schema' not in context:
        new_context = context.copy()  # Don't modify caller's context
        new_context['schema'] = schema.default_update_user_schema()
    else:
        new_context = context
    return update.user_update(new_context, data_dict)


class ECPortalPlugin(p.SingletonPlugin):
    p.implements(p.IConfigurable)
    p.implements(p.IConfigurer)
    p.implements(p.IRoutes)
    p.implements(p.IActions)
    p.implements(p.IAuthFunctions)

    def get_actions(self):
        return {
            'group_list': group_list,
            'group_update': group_update,
            'group_show': group_show,
            'purge_revision_history': purge_revision_history,
            'user_create': user_create,
            'user_update': user_update,
            'package_show': package_show
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
            # Note: openid users have slashes in their ids, so need the
            # wildcard in the route.
            m.connect('/user/edit/{id:.*}', action='edit')
            m.connect('/user/reset/{id:.*}', action='perform_reset')
            m.connect('/user/login', action='login')
            m.connect('/user/_logout', action='logout')
            m.connect('/user/logged_in', action='logged_in')
            m.connect('/user/logged_out', action='logged_out')
            m.connect('/user/logged_out_redirect', action='logged_out_page')
            m.connect('/user/me', action='me')
            m.connect('/user/set_lang/{lang}', action='set_lang')
            m.connect('/user/{id:.*}', action='read')

        # disable user list, password reset and user registration pages
        map.redirect('/user', '/not_found')
        map.redirect('/user/reset', '/not_found')
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
