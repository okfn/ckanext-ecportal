CKAN EC Portal Extension
========================

**Status:** Production

**CKAN Version:** release-v1.7.1-ecportal


Testing
-------

To run the tests with sqlite, from the ckanext-ecportal directory run:

::

    nosetests --ckan --with-pylons=test.ini tests


Or to run the postgres tests:

::

    nosetests --ckan --with-pylons=test-core.ini tests


Available paster commands
-------------------------

Paster commands that are available when using the ecportal extension.

export-datasets
~~~~~~~~~~~~~~~

export-datasets will export all of the active datasets in the installation and
write them as RDF formatted output to the specified folder::

  paster ecportal export-datasets /tmp_folder/ -c config.ini

Search Cloud
------------

The new search cloud functionality on the homepage requires that some new tables and indexes are added. This must be done before the server is started with the following command::

  paster --plugin=ckanext-ecportal ecportal searchcloud-install-tables -c config.ini

It is safe to run the command more than once.

The workflow for creating a search cloud on the homepage goes like this:

#. As users search, their searches are saved to the ``search_query`` table via a ``before_search()`` method on an ``IPackageController`` plugin
#. A cron job run the ``searchcloud-generate-unapproved-search-list`` paster command to populate the ``search_popular_latest`` table with summarised counts of the most popular searches from the last 30 days. This cron job runs each day.
#. A sysadmin visits ``/data/searchcloud`` and downloads a JSON representation of the data from the ``search_popular_latest`` table.
#. The sysadmin edits that JSON to moderate the terms they want to appear on the search cloud.
#. Making sure the file is still a strict, valid JSON file, they upload it to the site at ``/data/searchcloud/upload``. They are shown a preview and if they are happy with it they save the changes.
#. Saving causes the data in the ``search_popular_approved`` table to be replaced with the data that was parsed from the uploaded JSON file.
#. When a user visits the homepage, the data from the ``search_popular_approved`` table is queried to generate a search cloud for them.

To set up the cron job, the following command must be run every day at midnight::

  paster --plugin=ckanext-ecportal ecportal searchcloud-generate-unapproved-search-list -c config.ini

Most viewed datasets
--------------------

Most viewed datasets code is based on the existing CKAN ``TrackingMiddleware``
functionality and so its behaviour follows the behaviour of the generic
tracking.

A key is generated for each unique visitor based on::

    key = ''.join([
        environ['HTTP_USER_AGENT'],
        environ['REMOTE_ADDR'],
        environ['HTTP_ACCEPT_LANGUAGE'],
        environ['HTTP_ACCEPT_ENCODING'],
    ])
    key = hashlib.md5(key).hexdigest()

Each visit of a dataset page results in an AJAX request to ``/_tracking`` which
logs a new entry for this key in the ``tracking_raw`` table. A paster command
is used to build a summary table for this raw data, but it only counts unique
visits since the last time it was run. The optional ``date`` argument specifies
which days to rebuild for::

  paster --plugin=ckan tracking update -c config.ini

A cron job should be set up at 1 minute past mindnight to run this paster
command to aggregate unique visitors for each dataset for the day just gone
into the summary table. For example::

  1 0 * * * /applications/ecodp/users/ecodp/ckan/lib/ecodp/pyenv/bin/paster --plugin=ckan tracking update -c /applications/ecodp/users/ecodp/ckan/etc/ecodp/ecodp.ini

The datasets displayed on the homepage are based on the data in this summary
table. The actual query extracts the URL from the table, calculates the dataset
name and joins on ``package`` to find the top datasets. The query is cached.

Boolean Search Operators
------------------------

ECPortal presents the user with a choice of radio buttons to allow
customisation of the search boolean logic. The choices are ``all``, ``exact``
or ``any``. This required a change in CKAN search behaviour. Previously dataset
queries used the Solr dismax handler whereas publisher queries did not. Now
both use the dismax handler which means that the group name has to be added to
the ``fq`` parameter to filter by publisher, rather than the term being part of
the main ``q`` parameter as it was before.

To implement exact search, the terms entered are wrapped in quotes. To
implement all, the ``mm`` parameter is set to ``100%`` to implement any it is
set to ``0``. 

The default search method is now ``all``.

When a user chooses a search boolean operator during a search, the choice is
remembered and saved in the session which sets a cookie that expires when the
user's browser is exited. That means that their search preference will be
remembered for the session.

