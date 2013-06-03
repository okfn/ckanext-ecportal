import datetime
import logging
from pylons import config
import ckan.plugins as p
import ckan.lib.base as base

log = logging.getLogger(__name__)
json = base.json


def update_approved(Session, rows):
    Session.execute('DELETE FROM search_popular_approved;')
    for row in rows:
        Session.execute(
            '''
            INSERT INTO search_popular_approved
                   (search_string, count)
            VALUES (:search_string, :count)
            ''',
            {'search_string': row[0], 'count': row[1]},
        )

    # TODO: should we also check for beaker.cache.enabled in config here?
    try:
        approved_cache = base.cache.get_cache('approved', type="memory")
        if approved_cache:
            approved_cache.clear()
    except Exception, e:
        log.error('Couldn\'t clear the cache: %r' % (str(e)))


def get_latest(Session):
    results = Session.execute(
        '''
        SELECT search_string, count
        FROM search_popular_latest
        ORDER BY count DESC;
        '''
    )
    # return the results in a form that can be JSON-serialised
    return [list(row) for row in results]


def table_exists(Session, table_name):
    sql_table_exists = '''
        SELECT EXISTS(SELECT * FROM information_schema.tables
                      WHERE table_name=:table_name)
    '''
    return Session.execute(sql_table_exists,
                           {'table_name': table_name}).fetchone()[0]


def index_exists(Session, table_name, index_name):
    sql_index_exists = '''
        SELECT EXISTS
        (
            SELECT
                t.relname AS table_name
              , i.relname AS index_name
              , array_to_string(array_agg(a.attname), ', ') AS column_names
            FROM
                pg_class AS t
              , pg_class AS i
              , pg_index AS ix
              , pg_attribute AS a
            WHERE
                t.oid = ix.indrelid
                and i.oid = ix.indexrelid
                and a.attrelid = t.oid
                and a.attnum = ANY(ix.indkey)
                and t.relkind = 'r'
                and t.relname = :table_name
                and i.relname = :index_name
            GROUP BY
                t.relname
              , i.relname
            ORDER BY
                t.relname
              , i.relname
        )
        '''
    return Session.execute(sql_index_exists,
                           {'table_name': table_name,
                            'index_name': index_name}).fetchone()[0]


def install_tables(Session, out):
    created_count = 0

    if not table_exists(Session, 'search_query'):
        out('Creating the search_query table ...')
        Session.execute('''
            CREATE TABLE search_query (
                lang VARCHAR(10) NOT NULL
              , search_string VARCHAR NOT NULL
              -- This is only for use during the analysis
              , searched_at TIMESTAMP default NOW()
            );
        ''')
        created_count += 1
        out('done.')

    if not table_exists(Session, 'search_popular_latest'):
        out('Creating the search_popular_latest table ...')
        Session.execute('''
            CREATE TABLE search_popular_latest (
                lang VARCHAR(10) -- Can be NULL
              , search_string VARCHAR NOT NULL
              , count BIGINT
            );
        ''')
        created_count += 1
        out('done.')

    if not table_exists(Session, 'search_popular_approved'):
        out('Creating the search_popular_approved table ...')
        Session.execute('''
            CREATE TABLE search_popular_approved (
                lang VARCHAR(10)
              , search_string VARCHAR NOT NULL
              , count BIGINT NOT NULL
            );
        ''')
        created_count += 1
        out('done.')

    if not index_exists(Session, 'search_query', 'search_query_date'):
        out('Creating the search_query_date index ...')
        Session.execute('''
            CREATE INDEX search_query_date ON search_query (searched_at);
        ''')
        out('done.')
    else:
        out('The index already exists')

    if created_count == 0:
        out('The tables already exist')


def generate_unapproved_list(Session, days=30):
    Session.execute(
        '''
        DELETE FROM search_popular_latest;
        '''
    )
    Session.execute(
        '''
        INSERT INTO search_popular_latest (lang, search_string, count) (
            SELECT
                -- currently ignoring language
                NULL
              , search_string
              , count(*)
            FROM search_query
            WHERE searched_at > :since
            GROUP BY
                -- We don't need to group by lang at the moment
                search_string
            ORDER BY count(*) DESC
            LIMIT 100
        );
        ''',
        {'since': datetime.datetime.now() - datetime.timedelta(days=30)}
    )


def get_approved(Session):
    def approved():
        results = Session.execute(
            'SELECT search_string, count FROM search_popular_approved;'
        )
        # return the results in a form that can be JSON-serialised
        return [list(row) for row in results]

    # TODO: fix this - tests fail when cache is used
    #
    # if p.toolkit.asbool(config.get('beaker.cache.enabled', 'True')):
    #     try:
    #         approved_cache = base.cache.get_cache('approved', type="memory")
    #         return approved_cache.get_value(
    #             key='all',  # We don't need a key, but get_value requires one
    #             createfunc=approved,
    #             expiretime=60 * 5
    #         )
    #     except Exception, e:
    #         log.error('Couldn\'t use the cache: %r' % (str(e)))
    #         return approved()
    # else:
    #     return approved()

    return approved()


def track_term(Session, lang, search_string):
    Session.execute(
        '''
        INSERT INTO search_query (lang, search_string)
        VALUES (:lang, :search_string)
        ''',
        {'lang': lang, 'search_string': search_string}
    )


def approved_to_json(rows):
    # Note: We don't use jqcloud's build in link
    #       functionality as it causes terms to be
    #       double escaped, instead there is a JS
    #       click handler on the front-end
    cloud_data = []
    for row in rows:
        cloud_data.append({'text': row[0],
                           'weight': row[1]})
    return json.dumps(cloud_data)


def unify_terms(search_string, max_length=200):
    if not search_string.strip() or search_string == '*:*':
        return ''
    while '  ' in search_string:
        search_string = search_string.replace('  ', ' ')
    search_string = search_string.strip()
    if len(search_string) > max_length:
        terms = search_string.split()
        if len(terms) == 1:
            search_string = search_string[:max_length]
        else:
            search_string = ''
            for term in terms:
                if len(search_string) + len(term) + 1 < max_length:
                    search_string += term + ' '
            search_string = search_string[:-1]
    return search_string
