import datetime
import operator
import pylons.config as config
import genshi
import ckan
import ckan.model as model
import ckan.plugins as p
import ckan.lib.search as search
import ckan.lib.i18n as i18n

NUM_TOP_PUBLISHERS = 6


def current_url():
    return p.toolkit.request.environ['CKAN_CURRENT_URL'].encode('utf-8')


def current_locale():
    return i18n.get_locales_dict().get(p.toolkit.request.environ['CKAN_LANG'])\
        or i18n.get_locales_dict().get(config.get('ckan.locale_default', 'en'))


def root_url():
    if current_locale() == 'en':
        return '/'
    else:
        return '/%s/' % current_locale()


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
