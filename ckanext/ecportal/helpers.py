import pylons.i18n as i18n
import genshi
import ckan
import ckan.model as model
import ckan.logic as logic


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
    context = {'model': model, 'session': model.Session, 'user': 'john'}
    data = {'rows': n, 'sort': u'metadata_modified desc', 'facet': u'false'}
    return logic.get_action('package_search')(context, data).get('results', [])
