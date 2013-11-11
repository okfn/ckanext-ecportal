import ckan.plugin.toolkit as toolkit

_ = toolkit._


def terms_for_translation():
    '''
    Additional terms for translation.
    Terms from Python files and template files should be extracted
    automatically using the python setup.py extract_messages command.
    The terms in this file are ones that would be missed by this
    process. For example: terms in configuration files, 3rd party
    libraries, etc.
    '''
    # header
    _('Open Data Portal')
    _('European Union Open Data Portal')

    # search
    _('Tags')
    _('Keywords')
    _('Resource formats')
    _('Publisher')
    _('Language')
    _('Geographical Coverage')

    # from ckan/templates/_util.html
    # (ignored as a lot of the strings are not required)
    _('Number of datasets')
    _('View dataset resources')
    _('No downloadable resources.')
    _('No description for this item')

    # errors
    _('Not authorized to see this page')
    _('Unauthorized to read package %s')
    _('Unauthorized to read resource %s')
    _('The resource could not be found.')
    _('Dataset not found')
    _('Tag not found')
