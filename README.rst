CKAN EC Portal Extension
========================

**Status:** Alpha

**CKAN Version:** 0.1


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

