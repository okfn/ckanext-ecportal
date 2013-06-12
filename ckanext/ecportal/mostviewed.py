import logging
from pylons import config

import ckan.lib.base as base
import ckan.plugins as p

log = logging.getLogger(__name__)


def get_most_viewed(Session, limit=None):
    def cache_most_popular():
        sql = '''
        SELECT most_popular.url, most_popular.running_total,
               package.name, package.title
        FROM (
            SELECT
                url
              , running_total
              , regexp_split_to_array(url, E'\\/') as name
            FROM tracking_summary
            WHERE
                running_total > 0
            AND url LIKE('%/dataset/%')
            AND tracking_date = (select max(tracking_date)
                                 from tracking_summary)
            ) as most_popular
        LEFT JOIN package
        ON most_popular.name[array_length(most_popular.name, 1)] = package.name
        WHERE package.name IS NOT NULL
        ORDER BY
            running_total DESC
        '''
        if limit:
            sql += ' LIMIT ' + str(limit)
        results = Session.execute(sql)
        # return the results in a way that can be JSON serialised
        return [dict(row) for row in results]

    if p.toolkit.asbool(config.get('beaker.cache.enabled', 'True')):
        try:
            most_popular_cache = base.cache.get_cache(
                'get_most_popular', type='memory')
            return most_popular_cache.get_value(
                key='all',  # We don't need a key, but get_value requires one
                createfunc=cache_most_popular,
                expiretime=60 * 5)
        except Exception, e:
            log.error('Couldn\'t use the cache: %r' % (str(e)))
            return cache_most_popular()
    else:
        return cache_most_popular()
