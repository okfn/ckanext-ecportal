CKAN EC Portal Extension
========================

**Status:** Alpha

**CKAN Version:** 0.1


Testing
-------

To run the tests with sqlite, from the CKAN directory run:

::

    nosetests --ckan --with-pylons=../ckanext-ecportal/test.ini ../ckanext-ecportal/tests


Or to run the postgres tests:

::

    nosetests --ckan --with-pylons=../ckanext-ecportal/test-core.ini ../ckanext-ecportal/tests
