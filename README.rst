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

