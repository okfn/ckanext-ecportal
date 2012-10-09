"""Migrate CKAN datasets

Usage:
    migrate.py from <source> to <target> [options] <dataset-ids>...
    migrate.py create bundle from <source> [options] <dataset-ids>...
    migrate.py upload bundle to <target> [options] <dataset-ids>...

Options:
    -h --help                     Show this screen
    --dry-run                     Don't perform writes on the target machine.
    --source-api-key=<api-key>    API key on the source instance.
    --target-api-key=<api-key>    API key on the target instance.
    --overwrite                   Overwrite existing datasets on the target.

"""

import base64
import ckanclient
import docopt
import json
import logging
import os
import re
import requests
import shutil
import sys
import tempfile
import urlparse

log = logging.getLogger('main')
log.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(logging.Formatter('%(levelname)s : %(message)s'))
log.addHandler(handler)

def main(args):


    if args['create']:
        create_bundle_command(args)
    elif args['upload']:
        upload_bundle_command(args)
    elif args['from']:
        migrate_command(args)
    else:
        raise Exception('Unknown command')


def migrate_command(args):
    source_url = args['<source>']
    target_url = args['<target>']
    source_api_key = args['--source-api-key']
    target_api_key = args['--target-api-key']
    dry_run = args['--dry-run']
    dataset_ids = args['<dataset-ids>']
    overwrite = args['--overwrite']
    
    log.info('Performing migrations from %s to %s',
             source_url,
             target_url)

    if not (valid_ckan_url(source_url) and
            valid_ckan_url(target_url)):
        import sys
        sys.exit(1)

    ckan_source = ckanclient.CkanClient(base_location=source_url,
                                        api_key=source_api_key)
    ckan_target = ckanclient.CkanClient(base_location=target_url,
                                        api_key=target_api_key)

    for dataset in dataset_ids:
        migrate_dataset(dataset,
                        source=ckan_source,
                        target=ckan_target,
                        dry_run=dry_run,
                        overwrite=overwrite)

def create_bundle_command(args):
    source_url = args['<source>']
    source_api_key = args['--source-api-key']
    dataset_ids = args['<dataset-ids>']
    
    if not valid_ckan_url(source_url):
        import sys
        sys.exit(1)

    ckan_source = ckanclient.CkanClient(base_location=source_url,
                                        api_key=source_api_key)

    bundle = {}
    for dataset in dataset_ids:
        add_dataset_to_bundle(dataset,
                              source=ckan_source,
                              bundle=bundle)
    bundle_file = open('ckan-bundle.json', 'w')
    json.dump(bundle, bundle_file)
    bundle_file.close()

def upload_bundle_command(args):
    target_url = args['<target>']
    target_api_key = args['--target-api-key']
    dry_run = args['--dry-run']
    dataset_ids = args['<dataset-ids>']
    overwrite = args['--overwrite']
    
    if not valid_ckan_url(target_url):
        import sys
        sys.exit(1)

    ckan_target = ckanclient.CkanClient(base_location=target_url,
                                        api_key=target_api_key)

    bundle = json.load(open('ckan-bundle.json'))
    for dataset in dataset_ids:
        upload_dataset_from_bundle(dataset,
                                   target=ckan_target,
                                   bundle=bundle,
                                   dry_run=dry_run,
                                   overwrite=overwrite)

def add_dataset_to_bundle(dataset, source, bundle):
    '''Create a bundle of data and resource files from the source machine.'''
    log.info('Retriveing dataset from %s', source.base_location)

    if not dataset_exists(dataset, source):
        log.error("Could not find dataset %s on source", dataset)
        return

    source_dataset = source.package_show(dataset)

    # clean the fields a little
    for key, value in source_dataset.items():
        if isinstance(value, basestring) and \
           len(value) >= 2 and \
           value[0] == value[-1] == '"':
               source_dataset[key] = value.strip('"')

    log.info('Successfully retrieved %s from source' % dataset)
    download_resources(source_dataset, source) # modifies the source_dataset in place
    bundle[dataset] = source_dataset

def upload_dataset_from_bundle(dataset, target, bundle, dry_run=True, overwrite=False):
    '''Upload the given dataset, found in the given bundle, to the target'''
    if dataset not in bundle:
        log.critical('Could not find dataset %s in the bundle', dataset)
        return None

    source_dataset = bundle[dataset]
    
    if not check_groups_exist_on_target(source_dataset['groups'],
                                        target):
        log.error('Cannot migrate dataset %s because reuired group(s) do not exist on the target',
                  dataset)
        return

    log.info('Migrating dataset to target.')
    try:
        if dataset_exists(dataset, target):
            if not overwrite:
                log.error('Dataset %s exists already on target machine.  Not overwriting.', dataset)
                return
            else:

                # ids refer to the ids on the source instance.  Turn them
                # into their 'name' values.
                source_dataset['id'] = source_dataset['name']
                for g in source_dataset['groups']:
                    g['id'] = g['name']

                upload_resources(source_dataset, target, dry_run)

                if dry_run:
                    log.info('Skipping package update (dry-run)')
                else:
                    target.action('package_update', **source_dataset)
                    log.info('Successfully updated %s', dataset)
        else:   # dataset does not exist on the target
            source_dataset.pop('id')
            upload_resources(source_dataset, target, dry_run)
            if dry_run:
                log.info('Skipping package create (dry-run)')
            else:
                target.action('package_create', **source_dataset)
                log.info('Successfully created %s', dataset)
        log.info('Successfully migrated %s', dataset)


    except ckanclient.CkanApiNotAuthorizedError:
        log.critical('Not authorized to add dataset on target')
        return
    except ckanclient.CkanApiConflictError, e:
        log.critical('Conflit error attempting to migrate dataset %s', dataset)
        log.critical('This is most likely caused by invalid data')
        return


def migrate_dataset(dataset, source, target, dry_run=True, overwrite=False):
    '''Migrate a dataset'''
    log.info('Attempting to migrate %s', dataset)

    bundle = {}
    add_dataset_to_bundle(dataset, source, bundle)
    upload_dataset_from_bundle(dataset, target, bundle, dry_run=dry_run, overwrite=overwrite)


def download_resources(dataset, source):
    '''Download any uploaded-files'''
    if 'resources' not in dataset:
        return
    for resource in dataset['resources']:
        if resource['url'].startswith('http'):
            continue    # Skip those that look links

        # downloads resource's data to a temprary file
        data_filename = download_resource_file(resource, source)

        if data_filename is None:
            log.error('Unable to download data for %s',
                      resource['url'])
            continue
 
        # read entire file into the bundle
        resource['__data__'] = base64.encodestring(open(data_filename, 'r').read())


def upload_resources(dataset, target, dry_run):
    '''Upload any file-upload resources.

    And edit the dataset's resource attributes to reflect any changes'''
    if 'resources' not in dataset:
        return
    for resource in dataset['resources']:

        if resource['url'].startswith('http'):
            continue    # Skip those that look links

        if '__data__' not in resource:
            log.error('Could not find data for resource %s', resource['url'])
            continue

        data = base64.decodestring(resource['__data__'])

        # write the data to a file in order that ckanclient can upload it
        data_fh, data_filename = tempfile.mkstemp()
        data_fh = os.fdopen(data_fh, 'w')
        data_fh.write(data)
        data_fh.flush()
        data_fh.close()

        del resource['__data__']

        if dry_run:
            log.info('Skipping resource upload (dry-run)')
        else:
            log.info('Uploading %s to target', resource['url'])
            new_resource_url = upload_datafile(data_filename, target)
            if new_resource_url:
                resource['url'] = new_resource_url
            else:
                continue
            log.info('Successfully uploaded %s to target', resource['url'])


def download_resource_file(resource, ckan_source):
    '''Download the resource's data file.

    Store the contents in a temporary file, and return the filename'''
    # Figure out the URL of the resource's data.
    url_parts = urlparse.urlparse(ckan_source.base_location)
    resource_url = urlparse.urlunparse([
        url_parts.scheme,
        url_parts.netloc,
        resource['url'],
        '', '', ''])

    # ... and download it
    response = requests.get(resource_url)
    if response.status_code != requests.codes.ok:
        log.error('Unable to download resource %s for re-upload.', resource_url)
        return None
    data_fh, data_filename = tempfile.mkstemp()
    data_fh = os.fdopen(data_fh, 'w')
    data_fh.write(response.content)
    data_fh.flush()
    data_fh.close()
    return data_filename


def upload_datafile(filename, target):
    '''Upload the contents of the given file to the target ckan instance

    Using the file-upload mechansim.  Returns the url of the uploaded file.'''
    try:
        # HACK: remove "/api/3" from the end of the base location
        suffix = '/3' if target.base_location.endswith('/3') else ''
        if suffix:
            target.base_location = target.base_location[:-2]

        new_url, errs = target.upload_file(filename)
        if not errs:
            return new_url
        else:
            log.error('Errors uploading to target machine: %s', errs)
            return None
    except Exception, e:
        log.error('Unhandled exception whilst uploading to target machine', str(e))
        return None
    finally:
        if suffix:
            target.base_location = target.base_location + suffix


def dataset_exists(dataset, ckan_instance):
    '''Returns True iff the dataset exists on the given instance'''
    try:
        ckan_instance.package_show(dataset)
        return True
    except ckanclient.CkanApiNotFoundError:
        return False

def check_groups_exist_on_target(groups, target):
    '''Checks that the given list of group dicts exists on the target instance'''
    for group in groups:
        group_name = group['name']
        try:
            target.action('group_show', id=group_name)
            log.info('Group %s exists on target.', group_name)
        except ckanclient.CkanApiNotFoundError, e:
            log.error('Could not find group %s on target instance.',
                      group_name)
            return False
    return True


ckan_url_regex = re.compile(r'https?://.+')
def valid_ckan_url(url):
    '''Validate the given url'''
    if not ckan_url_regex.match(url):
        log.critical('Invalid URL: %s', url)
        return False
    return True

if __name__ == '__main__':
    args = docopt.docopt(__doc__)
    main(args)
