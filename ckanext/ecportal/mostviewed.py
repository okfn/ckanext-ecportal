def get_most_viewed(Session, limit=None):
    sql = '''
    SELECT most_popular.url, most_popular.running_total,
           package.name, package.title
    FROM (SELECT package_id, url, MAX(running_total) AS running_total
          FROM tracking_summary
          WHERE url LIKE('%/dataset/%')
          GROUP BY package_id, url) AS most_popular
    INNER JOIN package ON most_popular.package_id = package.id
    ORDER BY most_popular.running_total DESC
    '''
    if limit:
        sql += ' LIMIT ' + str(limit)
    results = Session.execute(sql)
    # return the results in a way that can be JSON serialised
    return [dict(row) for row in results]
