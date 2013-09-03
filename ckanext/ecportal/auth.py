'''
Customised authorization for the ecportal extension.
'''

import ckan.authz as authz
import ckan.logic.auth as ckan_auth
import ckan.logic.auth.publisher as publisher_auth


def _sysadmins_only(context, action_string):
    user = context['user']

    if authz.Authorizer().is_sysadmin(unicode(user)):
        return {'success': True}

    return {'success': False,
            'msg': 'You are not authorized to {0}'.format(action_string)}


def group_create(context, data_dict=None):
    '''
    Only sysadmins can create Groups.

    All the Groups are created through the API using a paster command.  So
    there's no need for non-sysadmin users to be able to create new Groups.
    '''
    user = context['user']

    if not user:
        return {'success': False,
                'msg': 'User is not authorized to create groups'}

    if user and authz.Authorizer.is_sysadmin(user):
        return {'success': True}
    else:
        return {'success': False,
                'msg': 'User is not authorized to create groups'}


def package_update(context, data_dict):
    '''
    Customised package_update auth overrides default ckan behaviour.

    Packages that have been imported by the RDF importer should not be edited
    via the web interface.  But obviously, they need to be updateable via the
    API.

    RDF-imported packages are identified by having an 'rdf' field.
    '''
    authorised_by_core = publisher_auth.update.package_update(
        context, data_dict)
    if authorised_by_core['success'] is False:
        return authorised_by_core
    elif 'api_version' in context:
        return authorised_by_core
    else:
        package = ckan_auth.get_package_object(context, data_dict)
        if 'rdf' in package.extras:
            return {
                'success': False,
                'msg': 'Not authorized to edit RDF-imported datasets by hand. '
                       'Please re-import this dataset instead.'
            }
        else:
            return authorised_by_core


def purge_publisher_datasets(context, data_dict):
    '''
    Only sysadmins can purge a publisher's deleted datasets.
    '''
    return _sysadmins_only(context, 'purge publisher datasets')


def purge_revision_history(context, data_dict):
    '''
    Only sysadmins can purge a publisher's revision history.
    '''
    return _sysadmins_only(context, 'purge revision history')


def purge_package_extra_revision(context, data_dict):
    '''
    Only sysadmins can remove old data from the package_extra_revision table.
    '''
    return _sysadmins_only(context, 'purge package extra revision')


def purge_task_data(context, data_dict):
    '''
    Only sysadmins can remove old task data.
    '''
    return _sysadmins_only(context, 'purge task data.')


def show_package_edit_button(context, data_dict):
    '''
    Custom ecportal auth function.

    This auth function is only used in one place: on the package layout
    template.  Its sole purpose is to determine whether to display the edit
    button for a given package.  This is determined by the core (default) ckan
    auth layer.  This allows the edit button to be displayed for RDF-imported
    datasets, even though the user won't have the rights to edit an
    RDF-imported dataset (see `package_update` auth above).  This allows the
    edit button to be displayed, but de-activated: giving the user feedback
    on how to update the dataset (ie - re-running the import).
    '''
    return publisher_auth.update.package_update(context, data_dict)


def package_search_private_datasets(context, data_dict):
    '''
    Custom ecportal auth function.

    Used in ecportal package_search to see if a user has permission to
    view private datasets in group search listings.

    Only applies to sysadmins for now, as group members can already
    see private datasets in the search listing (sysadmins cannot).
    '''
    return _sysadmins_only(context, 'view private datasets')


def user_create(context, data_dict=None):
    '''
    Only allow sysadmins to create new Users
    '''
    return _sysadmins_only(context, 'create new users')
