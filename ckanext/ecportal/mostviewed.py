# -*- coding: utf8 -*-

import datetime
import ckan.lib.base
import logging
from paste.deploy.converters import asbool

log = logging.getLogger(__name__)

# Model 

def get_most_viewed(Session, limit=None):
    def cache_most_popular():
        sql = '''
        SELECT most_popular.url, most_popular.running_total, package.name, package.title
        FROM (
            SELECT 
                url
              , running_total
              , regexp_split_to_array(url, E'\\/') as name
            FROM tracking_summary
            WHERE
                running_total > 0
            AND url LIKE('%/dataset/%')
            AND tracking_date = (select max(tracking_date) from tracking_summary)
            ) as most_popular
        LEFT JOIN package
        ON most_popular.name[array_length(most_popular.name, 1)] = package.name
        WHERE package.name IS NOT NULL
        ORDER BY
            running_total DESC
        '''
        if limit:
            sql += ' LIMIT '+str(limit)
        results = Session.execute(sql)
        # Return the results in a form that can be JSON-serialised
        return [dict(row) for row in results]

    if asbool(ckan.lib.base.config.get('beaker.cache.enabled', 'True')):
        try:
            most_popular_cache = ckan.lib.base.cache.get_cache('get_most_popular', type="memory")
            return most_popular_cache.get_value(
                key='all', # We don't need a key, but get_value requires one
                createfunc=cache_most_popular,
                expiretime=60*5, # We don't need to cache for long
            )
        except Exception, e:
            log.error('Couldn\'t use the cache: %r'%(str(e))) 
            return cache_most_popular()
    else:
        return cache_most_popular()



