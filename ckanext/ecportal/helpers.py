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
import ckan.lib.dictization as dictization
from ckan.authz import Authorizer
import ckanext.ecportal.unicode_sort as unicode_sort

NUM_TOP_PUBLISHERS = 6
UNICODE_SORT = unicode_sort.UNICODE_SORT

def translate(terms, lang, fallback_lang):
    translations = logic.get_action('term_translation_show')(
        {'model': model},
        {'terms': terms, 'lang_codes': [lang]}
    )

    term_translations = {}
    for translation in translations:
        term_translations[translation['term']] = \
            translation['term_translation']

    for term in terms:
        if not term in term_translations:
            translation = logic.get_action('term_translation_show')(
                {'model': model},
                {'terms': [term], 'lang_codes': [fallback_lang]}
            )
            if translation:
                term_translations[term] = translation[0]['term_translation']
            else:
                term_translations[term] = term

    return term_translations


def tags_and_translations(context, vocab, lang, lang_fallback):
    try:
        tags = logic.get_action('tag_list')(context, {'vocabulary_id': vocab})
        tag_translations = translate(tags, lang, lang_fallback)
        return sorted([(t, tag_translations[t]) for t in tags],
                      key=operator.itemgetter(1))
    except logic.NotFound:
        return []

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
    context = {'model': model, 'session': model.Session, 'user': user}
    userobj = model.User.get(user)

    ckan_lang = str(current_locale())
    ckan_lang_fallback = str(fallback_locale())

    if Authorizer().is_sysadmin(user):
        group_type = config.get('ckan.default.group_type',
                                'organization')
        groups = logic.get_action('group_list')(
            context, {'all_fields': True})
        groups = [group for group in groups
                  if group.get('type') == group_type]
    elif userobj:
        groups = []
        for group in userobj.get_groups():
             group_dict = dictization.table_dictize(group, context)
             group_dict['display_name'] = group.display_name
             groups.append(group_dict)
    else:
        groups = []

    group_translations = translate(
        [group.get('display_name') for group in groups],
        ckan_lang, ckan_lang_fallback)

    def sort_translations(key):
        # Strip accents first and if equivilant do next stage comparison.
        # leaving space and concatenating is to avoid having todo a real
        # 2 level sort.
        display_name = key[1]
        return (unicode_sort.strip_accents(display_name) +
                '   ' +
                display_name).translate(UNICODE_SORT)

    publishers = [
        (group['name'],
         group_translations[group.get('display_name')] or group['name'])
        for group in groups]
    publishers.sort(key=sort_translations)

    return publishers

