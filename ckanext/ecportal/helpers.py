import pylons.i18n as i18n
import genshi
import ckan
import ckan.model as model
import ckan.plugins as p


def format_description(description):
    '''
    Convert description from a string (with markdown formatting) to HTML.
    '''
    try:
        formatted = ckan.misc.MarkdownFormat().to_html(description)
        return genshi.HTML(formatted)
    except Exception:
        error_msg = "<span class='inline-warning'>%s</span>" % \
            i18n._("Cannot render package description")
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
    search_results = p.toolkit.get_action('package_search')(context, data)
    return search_results.get('results', [])
