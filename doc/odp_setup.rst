ODP Setup
=========


Install the Source
------------------

1. Ensure the required packages are installed.

    If you have access to ``apt-get``, you can install these packages as follows:

    ::

        sudo apt-get install mercurial python-dev postgresql libpq-dev
        sudo apt-get install libxml2-dev libxslt-dev python-virtualenv
        sudo apt-get install wget build-essential git-core subversion
        sudo apt-get install solr-jetty openjdk-6-jdk

    Otherwise, you should install these packages from source.

    =====================  ===============================================
    Package                Description
    =====================  ===============================================
    mercurial              `Source control <http://mercurial.selenic.com/>`_
    python                 `Python v2.5-2.7 <http://www.python.org/getit/>`_
    postgresql             `PostgreSQL database <http://www.postgresql.org/download/>`_
    libpq                  `PostgreSQL library <http://www.postgresql.org/docs/8.1/static/libpq.html>`_
    libxml2                `XML library development files <http://xmlsoft.org/>`_
    libxslt                `XSLT library development files <http://www.linuxfromscratch.org/blfs/view/6.3/general/libxslt.html>`_
    virtualenv             `Python virtual environments <http://pypi.python.org/pypi/virtualenv>`_
    wget                   `Command line tool for downloading from the web <http://www.gnu.org/s/wget/>`_
    build-essential        Tools for building source code (or up-to-date Xcode on Mac)
    git                    `Git source control (for getting MarkupSafe src) <http://book.git-scm.com/2_installing_git.html>`_
    subversion             `Subversion source control (for pyutilib) <http://subversion.apache.org/packages.html>`_
    solr                   `Search engine <http://lucene.apache.org/solr>`_
    jetty                  `HTTP server <http://jetty.codehaus.org/jetty/>`_ (used for Solr)
    openjdk-6-jdk          `OpenJDK Java library <http://openjdk.java.net/install/>`_
    =====================  ===============================================

2. Create a Python virtual environment.

    In the installation directory run:

    ::

        virtualenv odp

3. Activate your virtual environment.

   To work with CKAN it is best to adjust your shell settings so that your
   shell uses the virtual environment you just created. You can do this like
   so:

   ::

       . odp/bin/activate

   When your shell is activated you will see the prompt change to something
   like this:

   ::

       (odp)[ckan@host ~/]$

   An activated shell looks in your virtual environment first when choosing
   which commands to run. If you enter ``python`` now it will actually
   run ``<installation directory>/odp/bin/python``, not the default
   ``/usr/bin/python`` which is what you want for CKAN.
   You can install python packages install this new environment and they won't
   affect the default ``/usr/bin/python``.
   This is necessary so you can use particular versions of python packages,
   rather than the ones installed with default paython, and these installs do
   not affect other python software on your system that may not be compatible
   with these packages.

4. Install pip

   To help with automatically installing CKAN dependencies we use a tool
   called ``pip``. Make sure you have activated your environment (see step 3)
   and then install it from an activated shell like this:

   ::

       easy_install pip

5. Make a directory to install python packages that are required by ckan

   ::

       mkdir <installation directory>/odp/src
       cd <installation directory>/odp/src

6. Install CKAN code and other required Python packages into the new
   environment.

   The EU Open Data Portal currently uses the release-v1.7.1-ecportal CKAN
   branch.

   ::

       pip install --ignore-installed -e git+https://github.com/okfn/ckan.git@release-v1.7.1-ecportal#egg=ckan

7. CKAN has a set of dependencies it requires which you should install too. 
   These are listed in ``pip-requirements.txt``

   To install all dependencies, run:

   ::

       pip install --ignore-installed -r pip-requirements.txt

   The ``--ignore-installed`` option ensures ``pip`` installs software into
   this virtual environment even if it is already present on the system.

   At this point you should need to deactivate and then re-activate your
   virtual environment to ensure that all the scripts point to the correct
   locations:

   ::

       cd <installation directory>
       deactivate
       . odp/bin/activate

8. Setup a PostgreSQL database.

  List existing databases:

  ::

      sudo -u postgres psql -l

  It is advisable to ensure that the encoding of databases is 'UTF8', or
  internationalisation may be a problem. Since changing the encoding of
  PostgreSQL may mean deleting existing databases, it is suggested that this is
  fixed before continuing with the CKAN install.

  Next you'll need to create a database user if one doesn't already exist.

  Here we create a user called ``odp`` and will enter ``pass`` for the
  password when prompted:

  ::

      sudo -u postgres createuser -S -D -R -P odp

  Now create the database (owned by ``odp``), which we'll also call ``odp``:

  ::

      sudo -u postgres createdb -O odp odp

9. Create the CKAN config file.

    Make sure you are in an activated environment (see step 3) so that Python
    Paste and other modules are put on the python path (your command prompt
    will start with ``(odp)`` if you have) then change into the ``ckan``
    directory which will have been created when you installed CKAN in step 4
    and create the CKAN config file using Paste.

    ::

        cd odp/src/ckan
        paster make-config ckan odp.ini

    You'll need to now edit ``odp.ini`` and change the
    ``sqlalchemy.url`` line, filling in the database name, user and password
    that you used.

    ::

        sqlalchemy.url = postgresql://odp:pass@localhost/odp

    Change the path to the log file in the ckan config (line 197):

    ::

        args = ("/var/log/ckan/odp.log", "a", 20000000, 9)

10. Create database tables.

  Now that you have a configuration file that has the correct settings for
  your database, you'll need to create the tables. Make sure you are still in an
  activated environment with ``(odp)`` at the front of the command prompt and
  then from the ``odp/src/ckan`` directory run this command:

  ::

       paster --plugin=ckan db init --config=odp.ini

  You should see ``Initialising DB: SUCCESS``.

  If the command prompts for a password it is likely you haven't set up the
  database configuration correctly in step 6.

11. Create the cache directory.

  You need to create the Pylon's cache directory specified by 'cache_dir'
  in the config file.

  (from the ``odp/src/ckan`` directory):

  ::

       mkdir data


12. Setup Solr.

   You'll need to edit the Jetty configuration file (`/etc/default/jetty`)
   with suitable values::

       NO_START=0            # (line 4)
       JETTY_HOST=127.0.0.1  # (line 15)
       JETTY_PORT=8983       # (line 18)

   Start the Jetty server::

       sudo service jetty start

   You should see welcome page from Solr when visiting
   (replace localhost with your server address if needed)::

       http://localhost:8983/solr/

   and the admin site::

       http://localhost:8983/solr/admin

   If you get the message 
   `Could not start Jetty servlet engine because no Java Development Kit
   (JDK) was found.` then you will have to edit ``/etc/profile`` and add this 
   line to the end such as this to the end
   (adjusting the path for your machine's jdk install):

       ``JAVA_HOME=/usr/lib/jvm/java-6-openjdk-amd64/``

   Now run::

       export JAVA_HOME
       sudo service jetty start


   This default setup will use the following locations in your file system:

   * `/usr/share/solr`: Solr home, with a symlink pointing to the configuration
     dir in `/etc`.
   * `/etc/solr/conf`: Solr configuration files. The more important ones are
     `schema.xml` and  `solrconfig.xml`.
   * `/var/lib/solr/data/`: This is where the index files are physically
     stored.

   You will obviously need to replace the default `schema.xml` file with the
   CKAN one. To do so, create a symbolic link to the schema file in the
   EC Portal extension source.::

       sudo mv /etc/solr/conf/schema.xml /etc/solr/conf/schema.xml.bak
       sudo ln -s <installation directory>/odp/src/ckanext-ecportal/ckanext/ecportal/solr/schema.xml /etc/solr/conf/schema.xml
       sudo service jetty stop
       sudo service jetty start

   Check that Solr is still working.

   Set appropriate values for the ``ckan.site_id`` and ``solr_url`` config
   variables in your CKAN config file:

   ::

       ckan.site_id=odp
       solr_url=http://127.0.0.1:8983/solr


13. Install the CKAN EC Portal Extension

    First, clone the ``ckanext-ecportal`` Git repository to the ``odp/src``
    directory:

    ::

        cd <installation directory>/odp/src
        git clone https://github.com/okfn/ckanext-ecportal.git

    Make sure that the odp virtualenv is active (step 3), and install the
    extension:

    ::

        cd ckanext-ecportal
        pip install -e .

    The following plugins must be enabled in the CKAN config file
    (by adding them to the ``ckan.plugins`` line):

    ::

        synchronous_search
        ecportal
        ecportal_form
        ecportal_publisher_form
        ecportal_controller
        multilingual_dataset
        multilingual_group
        multilingual_tag
        qa
        datastorer

    Finally, restart CKAN (or Apache).


14. For a guide to deploying CKAN with Apache,
    see: http://docs.ckan.org/en/ckan-1.7.2/deployment.html
