#!/bin/bash

## Produces an RPM for the migration script and its dependencies to be installed
## in /applications/ecodp/users/ecodp/ckan-migrate This includes a python
## virtualenv which is separate to the pyenv used by CKAN (as it has conflicting
## dependencies).
## 
## This script is meant to be run on a VM that mirrors the layout of the target
## machine, ie - with the /appliocations/ecodp/... layout

set -e

CKAN_MIGRATE=/applications/ecodp/users/ecodp/ckan-migrate
PYENV="$CKAN_MIGRATE/pyenv"
PIP="$PYENV/bin/pip"

echo 'Installing dependencies for building pyenv'
sudo yum install python-distribute
sudo easy_install pip
sudo pip install virtualenv

echo 'Removing any old pyenvs, and ensuring directories exist'
sudo mkdir -p "$CKAN_MIGRATE"
rm -rf "$CKAN_MIGRATE"
sudo mkdir -p "$CKAN_MIGRATE"

echo 'Building pyenv'
virtualenv --no-site-packages $PYENV

echo 'Installing ckan-migrate dependencies into pyenv'
$PIP install -r ./pip-requirements.txt
mkdir "$CKAN_MIGRATE/src"
cp ./*.py "$CKAN_MIGRATE/src/"
$PIP install -e "$CKAN_MIGRATE/src/"
ln -s "$PYENV/bin/migrate.py" "$CKAN_MIGRATE/migrate.py"
chown -R ecodp "$CKAN_MIGRATE"
chgrp -R ecodp "$CKAN_MIGRATE"

echo 'Installing dependencies for fpm'
yum install -y ruby ruby-devel rubygems rpm-build gcc
gem install fpm

echo 'Building RPM'
rm -f ecportal-ckan-migrate-0.1-1.x86_64.rpm
fpm -s dir -t rpm -n 'ecportal-ckan-migrate' -v 0.1 -a x86_64 $CKAN_MIGRATE
