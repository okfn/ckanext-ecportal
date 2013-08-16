import ckan.logic as logic
import ckan.plugins as plugins
import ckan.lib.dictization as d
import ckan.lib.navl.dictization_functions
import ckan.lib.plugins as lib_plugins
import json
import pylons
import urlparse

import ckanext.ecportal.schema as schema
import ckanext.ecportal.unicode_sort as unicode_sort 
UNICODE_SORT = unicode_sort.UNICODE_SORT
_RESOURCE_MAPPING = None

_validate = ckan.lib.navl.dictization_functions.validate

def _get_filename_and_extension(resource):
    url = resource.get('url').rstrip('/')
    if '?' in url:
        return '', ''
    if 'URL' in url:
        return '', ''
    url = urlparse.urlparse(url).path
    split = url.split('/')
    last_part = split[-1]
    ending = last_part.split('.')[-1].lower()
    if len(ending) in [2,3,4] and len(last_part) > 4 and len(split) > 1:
        return last_part, ending
    return '', ''

def _get_resource_mapping():
    global _RESOURCE_MAPPING
    if not _RESOURCE_MAPPING:
        file_location = pylons.config.get(
             'ecportal.resource_mapping',
             '/applications/ecodp/users/ecodp/ckan/conf/resource_mapping.json'
        )
        with open(file_location) as resource_file:
            _RESOURCE_MAPPING = json.loads(resource_file.read())

    return _RESOURCE_MAPPING


# wrapper around group update, *always* adds on packages

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
    session = context['session']

    id = data_dict.get('id')
    group = model.Group.get(id)

    if group is None:
        raise logic.NotFound('Group was not found.')

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

    # can't save display_name so remove it from data_dict
    data_dict.pop('display_name', None)

    return logic.action.update.group_update(context, data_dict)


# copy of group_dictize form core only change removing package_list dictize

def group_dictize(group, context):
    result_dict = d.table_dictize(group, context)

    result_dict['display_name'] = group.display_name

    result_dict['extras'] = d.model_dictize.extras_dict_dictize(
        group._extras, context)

    context['with_capacity'] = True

    if context.get('ecodp_with_package_list', False):
        result_dict['packages'] = d.obj_list_dictize(
            d.model_dictize._get_members(context, group, 'packages'),
            context)

    result_dict['tags'] = d.model_dictize.tag_list_dictize(
        d.model_dictize._get_members(context, group, 'tags'),
        context)

    result_dict['groups'] = d.model_dictize.group_list_dictize(
        d.model_dictize._get_members(context, group, 'groups'),
        context)

    result_dict['users'] = d.model_dictize.user_list_dictize(
        d.model_dictize._get_members(context, group, 'users'),
        context)

    context['with_capacity'] = False

    if context.get('for_view'):
        for item in plugins.PluginImplementations(plugins.IGroupController):
            result_dict = item.before_view(result_dict)

    return result_dict


# copy of core group show only change is using group_dictize above

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
        raise logic.NotFound

    logic.check_access('group_show', context, data_dict)

    group_dict = group_dictize(group, context)

    for item in plugins.PluginImplementations(plugins.IGroupController):
        item.read(group)

    group_plugin = lib_plugins.lookup_group_plugin(group_dict['type'])
    try:
        group_schema = group_plugin.db_to_form_schema_options({
            'type': 'show',
            'api': 'api_version' in context,
            'context': context
        })
    except AttributeError:
        group_schema = group_plugin.db_to_form_schema()

    if group_schema:
        package_dict, errors = _validate(group_dict, group_schema,
                                         context=context)

    return group_dict


def sort_group(key):
    if isinstance(key, basestring):
        display_name = key
    else:
        display_name = key.get('display_name', '')
    # Strip accents first and if equivilant do next stage comparison.
    # Leaving space and concatenating is to avoid having todo a real
    # 2 level sort.
    return (unicode_sort.strip_accents(display_name) +
            '   ' +
            display_name).translate(UNICODE_SORT)


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
    groups = logic.action.get.group_list(context, data_dict)

    if context.get('for_view', False):
        # in the web UI only list publishers with published datasets

        # depending upon the context, group['packages'] may be either a
        # count of the packages, or the actual list of packages
        if groups and isinstance(groups[0]['packages'], int):
            groups = [g for g in groups if g['packages'] > 0]
        else:
            groups = [g for g in groups if len(g['packages']) > 0]

    return sorted(groups, key=sort_group)

def _change_resource_details(resource):
    formats = _get_resource_mapping().keys()
    resource_format = resource.get('format', '').lower().lstrip('.')
    filename, extension = _get_filename_and_extension(resource)
    if not resource_format:
        resource_format = extension
    if resource_format in formats:
        resource['format'] = _get_resource_mapping()[resource_format][0]
        if resource.get('name', '') in ['Unnamed resource', '', None]:
            resource['name'] = _get_resource_mapping()[resource_format][1]
            if filename:
                resource['name'] = resource['name']
    elif resource.get('name', '') in ['Unnamed resource', '', None]:
        if extension and not resource_format:
            resource['format'] = extension.upper()
        resource['name'] = 'Web Page'

    if filename and not resource.get('description'):
        resource['description'] = filename


def package_show(context, data_dict):
    '''Override package_show to sort the resources by name'''
    result = logic.action.get.package_show(context, data_dict)

    def order_key(resource):
        return resource.get('name', resource.get('description', ''))

    if 'resources' in result:
        result['resources'].sort(key=order_key)

    for resource in result['resources']:
        _change_resource_details(resource)

    return result

def resource_show(context, data_dict):
    resource = logic.action.get.resource_show(context, data_dict)
    _change_resource_details(resource)
    return resource


def purge_revision_history(context, data_dict):
    '''
    Purge a given publisher's unused revision history.

    :param group: the name or id of the publisher
    :type group: string

    :returns: number of resources and revisions purged.
    :rtype: dictionary
    '''
    logic.check_access('purge_revision_history', context, data_dict)

    model = context['model']
    engine = model.meta.engine
    group_identifier = logic.get_or_bust(data_dict, 'group')
    group = model.Group.get(group_identifier)

    if not group:
        raise logic.NotFound

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

    except Exception, e:
        raise logic.ActionError('Error executing sql: %s' % e)

    return {'number_revisions_deleted': number_revisions_deleted,
            'number_resources_deleted': number_resources_deleted}


def purge_package_extra_revision(context, data_dict):
    '''
    Purge old data from the package_extra_revision table.

    :returns: number of revisions purged.
    :rtype: dictionary
    '''
    logic.check_access('purge_package_extra_revision', context, data_dict)

    model = context['model']
    engine = model.meta.engine

    delete_old_extra_revisions = '''
        DELETE FROM package_extra_revision WHERE current=false;
    '''

    try:
        revision_rows_deleted = engine.execute(
            delete_old_extra_revisions).rowcount

    except Exception, e:
        raise logic.ActionError('Error executing sql: %s' % e)

    return {'revision_rows_deleted': revision_rows_deleted}


def purge_task_data(context, data_dict):
    '''
    Purge data from the task_status and kombu_message tables
    (used by CKAN tasks and Celery).

    To just clear the Celery data (and not the task_status table),
    see the 'celery clean' command in CKAN core.

    :returns: number of task_status and Celery (kombu_message) rows deleted.
    :rtype: dictionary
    '''
    logic.check_access('purge_task_data', context, data_dict)

    model = context['model']
    engine = model.meta.engine

    purge_task_status = 'DELETE FROM task_status;'
    purge_celery_data = 'DELETE FROM kombu_message;'

    try:
        task_status_rows_deleted = engine.execute(purge_task_status).rowcount
        celery_rows_deleted = engine.execute(purge_celery_data).rowcount

    except Exception, e:
        raise logic.ActionError('Error executing sql: %s' % e)

    return {'task_status_rows_deleted': task_status_rows_deleted,
            'celery_rows_deleted': celery_rows_deleted}


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
    new_context = context.copy()  # Don't modify caller's context
    new_context['schema'] = schema.default_user_schema()
    return logic.action.create.user_create(new_context, data_dict)


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
    new_context = context.copy()  # Don't modify caller's context
    new_context['schema'] = schema.default_update_user_schema()
    return logic.action.update.user_update(new_context, data_dict)
