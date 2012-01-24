#!/usr/bin/env python

import sys
import os
import glob
import urllib
import json
import ckanclient

def _add_dataset(file_path, ckan_url, ckan_api_key):
    ckan = ckanclient.CkanClient(base_location=ckan_url, api_key=ckan_api_key)

    with open(file_path, 'r') as f:
        dataset = json.loads(f.read())
        extras = dataset.get('extras')

        if extras:
            # change licenseLink to license_link
            if extras.get('licenseLink'):
                license_link = extras['licenseLink']
                del extras['licenseLink']
                extras['license_link'] = license_link
                extras['license_link'] = urllib.unquote(extras['license_link'])
            # change responsable_department to responsible_department
            if extras.get('responsable_department'):
                department = extras['responsable_department']
                del extras['responsable_department']
                extras['responsable_department'] = department
            # remove encoding of support extra
            if extras.get('support'):
                extras['support'] = urllib.unquote(extras['support'])

        # remove encoding of url and resource.url fields
        if dataset.get('url'):
            dataset['url'] = urllib.unquote(dataset['url'])
        for resource in dataset.get('resources', []):
            if resource.get('url'):
                resource['url'] = urllib.unquote(resource['url'])

        try:
            print "Adding dataset: %s" % dataset['name']
            ckan.package_register_post(dataset)
        except Exception as e:
            print "Error: Could not add dataset (%s: %s)" % (e.__class__.__name__, e.message)
            print "Dataset:", dataset

if __name__ == '__main__':
    if len(sys.argv) != 4:
        print 'Usage:', __file__, '<ckan url> <ckan api key> <Eurostat JSON file or directory with JSON files>'
        sys.exit(1)

    ckan_url = sys.argv[1]
    ckan_api_key = sys.argv[2]
    json_path = sys.argv[3]

    if os.path.isfile(json_path):
        _add_dataset(json_path, ckan_url, ckan_api_key)
    elif os.path.isdir(json_path):
        for file_path in glob.glob(os.path.join(json_path, '*.json')):
            _add_dataset(file_path, ckan_url, ckan_api_key)
    else:
        print 'Error: can not add %s' % json_path
        sys.exit(2)

