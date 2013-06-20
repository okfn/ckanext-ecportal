import datetime
import operator
import pylons.config as config
import genshi
import ckan
import ckan.model as model
import ckan.plugins as p
import ckan.lib.search as search
import ckan.lib.i18n as i18n
import ckan.logic as logic

NUM_TOP_PUBLISHERS = 6


def current_url():
    return p.toolkit.request.environ['CKAN_CURRENT_URL'].encode('utf-8')


def current_locale():
    return i18n.get_locales_dict().get(p.toolkit.request.environ['CKAN_LANG'])\
        or fallback_locale()


def fallback_locale():
    return i18n.get_locales_dict().get(config.get('ckan.locale_default', 'en'))


def root_url():
    locale = p.toolkit.request.environ.get('CKAN_LANG')
    default_locale = p.toolkit.request.environ.get('CKAN_LANG_IS_DEFAULT',
                                                   True)

    if default_locale:
        return '/'
    else:
        return '/{0}/'.format(locale)


def format_description(description):
    '''
    Convert description from a string (with markdown formatting) to HTML.
    '''
    try:
        formatted = ckan.misc.MarkdownFormat().to_html(description)
        return genshi.HTML(formatted)
    except Exception:
        error_msg = "<span class='inline-warning'>%s</span>" % \
            p.toolkit._("Cannot render package description")
        return genshi.HTML(error_msg)


def recent_updates(n):
    '''
    Return a list of the n most recently updated datasets.
    '''
    context = {'model': model,
               'session': model.Session,
               'user': p.toolkit.c.user or p.toolkit.c.author}
    data = {'rows': n,
            'sort': u'metadata_modified desc',
            'facet': u'false',
            'fq': u'capacity: "public"'}
    try:
        search_results = p.toolkit.get_action('package_search')(context, data)
    except search.SearchError:
        search_results = {}
    return search_results.get('results', [])


def top_publishers(groups):
    '''
    Updates the 'packages' field in each group dict (up to a maximum
    of NUM_TOP_PUBLISHERS) to show the number of public datasets in the group.
    '''
    publishers = [g for g in groups if g['packages'] > 0]
    publishers.sort(key=operator.itemgetter('packages'), reverse=True)

    return publishers[:NUM_TOP_PUBLISHERS]


def current_date():
    return datetime.date.today().strftime('%d/%m/%Y')


def group_facets_by_field(fields):
    facets = {}
    for field, value in fields:
        if field in facets:
            facets[field].append(value)
        else:
            facets[field] = [value]
    return facets

def groups_available(user):
    ''' return a list of available groups '''
    context = {'model': model, 'session': model.Session, 'user': user}
    data_dict = {'available_only': True}
    return logic.get_action('group_list_authz')(context, data_dict)
