ECPortal Server Setup
=====================


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
   
    In your home directory run the command below. 
   
    ::
   
        cd ~
        virtualenv ecportal
   
3. Activate your virtual environment.

   To work with CKAN it is best to adjust your shell settings so that your
   shell uses the virtual environment you just created. You can do this like
   so:

   ::

       . ecportal/bin/activate

   When your shell is activated you will see the prompt change to something
   like this:

   ::

       (ecportal)[ckan@host ~/]$

   An activated shell looks in your virtual environment first when choosing
   which commands to run. If you enter ``python`` now it will actually 
   run ``~/ecportal/bin/python``, not the default ``/usr/bin/python`` which is what you want for CKAN. You can install python packages install this new environment and they won't affect the default ``/usr/bin/python``. This is necessary so you can use particular versions of python packages, rather than the ones installed with default paython, and these installs do not affect other python software on your system that may not be compatible with these packages.

4. Install pip
   
   To help with automatically installing CKAN dependencies we use a tool
   called ``pip``. Make sure you have activated your environment (see step 3)
   and then install it from an activated shell like this:
   
   ::
   
       easy_install pip

5. Make a directory to install python packages that are required by ckan

   ::
 
       mkdir ~/ecportal/src
       cd ~/ecportal/src

6. Install CKAN code and other required Python packages into the new environment.

   Choose which version of CKAN to install. Released versions are listed at https://github.com/okfn/ckan - click on the list of tags. For example: ``ckan-1.5.1``

   ::

       pip install --ignore-installed -e git+https://github.com/okfn/ckan.git@ckan-1.5.1#egg=ckan

7. CKAN has a set of dependencies it requires which you should install too. These are listed in three text files: requires/lucid_*.txt, followed by WebOb explicitly.

   First we install two of the three lists of dependencies:

   ::

       pip install --ignore-installed -r ckan/requires/lucid_missing.txt -r ckan/requires/lucid_conflict.txt
       pip install webob==1.0.8

   The ``--ignore-installed`` option ensures ``pip`` installs software into
   this virtual environment even if it is already present on the system.

   WebOb has to be installed explicitly afterwards because by installing pylons with `--ignore-installed` you end up with a newer (incompatible) version than the one that Pylons and CKAN need.

   Now to install the remaining dependencies in requires/lucid_present.txt and you are using Ubuntu Lucid 10.04 you can install the system versions::

       sudo apt-get install python-pybabel python-psycopg2 python-lxml 
       sudo apt-get install python-sphinx python-pylons python-repoze.who 
       sudo apt-get install python-repoze.who-plugins python-tempita python-zope.interface
       
   Alternatively, if you are not using Ubuntu Lucid 10.04 you'll need to install them like this:

   ::

       pip install --ignore-installed -r ecportal/src/ckan/requires/lucid_present.txt
   
   At this point you will need to deactivate and then re-activate your
   virtual environment to ensure that all the scripts point to the correct
   locations:

   ::
   
       cd
       deactivate
       . ecportal/bin/activate

8. Setup a PostgreSQL database.

  List existing databases:

  ::

      sudo -u postgres psql -l

  It is advisable to ensure that the encoding of databases is 'UTF8', or 
  internationalisation may be a problem. Since changing the encoding of PostgreSQL
  may mean deleting existing databases, it is suggested that this is fixed before
  continuing with the CKAN install.

  Next you'll need to create a database user if one doesn't already exist.

  .. tip ::

      If you choose a database name, user or password which are different from the example values suggested below then you'll need to change the sqlalchemy.url value accordingly in the CKAN configuration file you'll create in the next step.

  Here we create a user called ``ecportal`` and will enter ``pass`` for the password when prompted:

  ::

      sudo -u postgres createuser -S -D -R -P ecportal

  Now create the database (owned by ``ecportal``), which we'll also call ``ecportal``:

  ::

      sudo -u postgres createdb -O ecportal ecportal

9. Create a CKAN config file.

    Make sure you are in an activated environment (see step 3) so that Python
    Paste and other modules are put on the python path (your command prompt will
    start with ``(ecportal)`` if you have) then change into the ``ckan`` directory
    which will have been created when you installed CKAN in step 4 and create the
    CKAN config file using Paste. These instructions call it ``development.ini`` since that is the required name for running the CKAN tests. But for a server deployment then you might want to call it say after the server hostname e.g. ``test.ckan.net.ini``.

    ::

        cd ecportal/src/ckan
        paster make-config ckan development.ini

    If you used a different database name or password when creating the database
    in step 5 you'll need to now edit ``development.ini`` and change the
    ``sqlalchemy.url`` line, filling in the database name, user and password you used.

    ::
  
        sqlalchemy.url = postgresql://ckanuser:pass@localhost/ckantest

    If you're using a remote host with password authentication rather than SSL authentication, use::

        sqlalchemy.url = postgresql://<user>:<password>@<remotehost>/ckan?sslmode=disable

    Change the path to the log file in the ckan config (line 197):

    ::

        args = ("/var/log/ckan/ecportal.log", "a", 20000000, 9)

10. Create database tables.

  Now that you have a configuration file that has the correct settings for
  your database, you'll need to create the tables. Make sure you are still in an
  activated environment with ``(ecportal)`` at the front of the command prompt and
  then from the ``ecportal/src/ckan`` directory run this command.

  If your config file is called development.ini:

   ::

       paster --plugin=ckan db init

  or if your config file is something else, you need to specify it. e.g.::

       paster --plugin=ckan db init --config=test.ckan.net.ini

  You should see ``Initialising DB: SUCCESS``. 

  If the command prompts for a password it is likely you haven't set up the 
  database configuration correctly in step 6.

11. Create the cache directory.

  You need to create the Pylon's cache directory specified by 'cache_dir' 
  in the config file.

  (from the ``ecportal/src/ckan`` directory):

  ::

       mkdir data


12. Setup Solr.

   You'll need to edit the Jetty configuration file (`/etc/default/jetty`) with the
   suitable values::

       NO_START=0            # (line 4)
       JETTY_HOST=127.0.0.1  # (line 15)
       JETTY_PORT=8983       # (line 18)

   Start the Jetty server::

       sudo service jetty start

   You should see welcome page from Solr when visiting (replace localhost with your
   server address if needed)::

       http://localhost:8983/solr/

   and the admin site::

       http://localhost:8983/solr/admin

   .. note:: If you get the message `Could not start Jetty servlet engine because no Java Development Kit (JDK) was found.` then you will have to edit /etc/profile and add this line to the end such as this to the end (adjusting the path for your machine's jdk install):

       ``JAVA_HOME=/usr/lib/jvm/java-6-openjdk-amd64/``

   Now run::

       export JAVA_HOME
       sudo service jetty start


   This default setup will use the following locations in your file system:

   * `/usr/share/solr`: Solr home, with a symlink pointing to the configuration dir in `/etc`.
   * `/etc/solr/conf`: Solr configuration files. The more important ones are `schema.xml` and  `solrconfig.xml`.
   * `/var/lib/solr/data/`: This is where the index files are physically stored.

   You will obviously need to replace the default `schema.xml` file with the CKAN one. To do
   so, create a symbolic link to the schema file in the config folder. Use the latest schema version
   supported by the CKAN version you are installing (it will generally be the highest one)::

       sudo mv /etc/solr/conf/schema.xml /etc/solr/conf/schema.xml.bak
       sudo ln -s ~/ecportal/src/ckan/ckan/config/solr/schema-1.3.xml /etc/solr/conf/schema.xml
       sudo service jetty stop
       sudo service jetty start

   Check that Solr is still working.

   Set appropriate values for the ``ckan.site_id`` and ``solr_url`` config variables in your CKAN config file:

   ::

       ckan.site_id=ecportal
       solr_url=http://127.0.0.1:8983/solr


13. [optional] Setup Apache

    ::
        sudo apt-get install apache2 libapache2-mod-wsgi

    Create a document root for the apache site:

    ::

        mkdir ~/ecportal/static

    Add the file /etc/apache2/sites-available/ecportal, containing:

    ::

        <VirtualHost *:80>
            DocumentRoot /home/okfn/ecportal/static
            ServerName ecportal.ckan.localhost

            <Directory />
                allow from all
            </Directory>

            #<Directory /home/okfn/ecportal/src/ckan/>
            #    allow from all
            #</Directory>

            <Directory /home/okfn/ecportal/static>
                allow from all
            </Directory>

            Alias /dump /home/okfn/ecportal/static/dump

            # Disable the mod_python handler for static files
            <Location /dump>
                SetHandler None
                Options +Indexes
            </Location>

            # this is our app
            WSGIScriptAlias / /home/okfn/ecportal/wsgi.py

            # pass authorization info on (needed for rest api)
            WSGIPassAuthorization On

            ErrorLog /var/log/apache2/ecportal.error.log
            CustomLog /var/log/apache2/ecportal.custom.log combined
        </VirtualHost>

    Add the wsgi file (/home/okfn/ecportal/wsgi.py), containing:

    ::

        import os
        instance_dir = '/home/okfn/ecportal'
        config_dir = '/home/okfn/ecportal/src/ckan'
        config_file = 'ecportal.ini'
        pyenv_bin_dir = os.path.join(instance_dir, 'bin')
        activate_this = os.path.join(pyenv_bin_dir, 'activate_this.py')
        execfile(activate_this, dict(__file__=activate_this))

        config_filepath = os.path.join(config_dir, config_file)
        if not os.path.exists(config_filepath):
            raise Exception('No such file %r'%config_filepath)
        from paste.deploy import loadapp
        from paste.script.util.logging_config import fileConfig
        fileConfig(config_filepath)
        application = loadapp('config:%s' % config_filepath)
        from apachemiddleware import MaintenanceResponse
        application = MaintenanceResponse(application)

    Make sure that the user that apache will run as has write permissions to the log and data directories:

    ::

        mkdir /var/log/ckan
        sudo chgrp www-data /var/log/ckan
        sudo chmod 775 var/log/ckan

        mkdir ~/ecportal/src/ckan/sstore
        sudo chgrp www-data ~/ecportal/src/ckan/sstore
        chmod 775 ~/ecportal/src/ckan/sstore

        sudo chgrp www-data ~/ecportal/src/ckan/data
        chmod 775 ~/ecportal/src/ckan/data

    Enable the site:

    ::

        sudo a2ensite ecportal
        sudo service apache2 restart

