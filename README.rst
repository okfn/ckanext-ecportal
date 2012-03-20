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
