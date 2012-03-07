import os
import glob
import json
import urllib
from ckan import model
from ckan.logic import get_action, NotFound
from ckan.lib.cli import CkanCommand
import forms
import field_values

import logging
log = logging.getLogger()


class ECPortalCommand(CkanCommand):
    '''
    Commands:

        paster ecportal import-data <data> -c <config>
        paster ecportal import-publishers <translations> <structure> -c <config>
        paster ecportal create-geo-vocab -c <config>

    Where:
        <data> = path to json file, or directory containing json files
        <translations> = path to translations.json
        <structure> = path to structure.json
        <config> = path to your ckan config file

    The commands should be run from the ckanext-ecportal directory.
    '''
    summary = __doc__.split('\n')[0]
    usage = __doc__

    def command(self):
        '''
        Parse command line arguments and call appropriate method.
        '''
        if not self.args or self.args[0] in ['--help', '-h', 'help']:
            print ECPortalCommand.__doc__
            return

        cmd = self.args[0]
        self._load_config()

        if cmd == 'import-data':
            if not len(self.args) == 2:
                print ECPortalCommand.__doc__
                return
            self.import_data(self.args[1])

        elif cmd == 'import-publishers':
            if not len(self.args) == 3:
                print ECPortalCommand.__doc__
                return
            translations_path = self.args[1]
            structure_path = self.args[2]

            if os.path.isfile(translations_path) and \
               os.path.isfile(structure_path):
                with open(translations_path, 'r') as t:
                    with open(structure_path, 'r') as s:
                        self.import_publishers(json.loads(t.read()),
                                               json.loads(s.read()))
            else:
                log.error('Could not open files %s and %s' %
                    (translations_path, structure_path)
                )

        elif cmd == 'create-geo-vocab':
            self.create_geo_vocab()

        else:
            log.error('Command "%s" not recognized' % (cmd,))

    def import_data(self, path):
        if os.path.isfile(path):
            self.import_dataset(path)
        elif os.path.isdir(path):
            for file_path in glob.glob(os.path.join(path, '*.json')):
                self.import_dataset(file_path)
        else:
            log.error('Error: can not add %s' % path)

    def import_dataset(self, path):
        with open(path, 'r') as f:
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
                    extras['responsible_department'] = department
                # remove encoding of support extra
                if extras.get('support'):
                    extras['support'] = urllib.unquote(extras['support'])
                # convert to list of dicts
                dataset[u'extras'] = [{'key': k, 'value': json.dumps(extras[k])}
                                      for k in extras.keys() if extras[k]]

            # remove encoding of url and resource.url fields
            if dataset.get('url'):
                dataset['url'] = urllib.unquote(dataset['url'])
            for resource in dataset.get('resources', []):
                if resource.get('url'):
                    resource['url'] = urllib.unquote(resource['url'])

            # rename tags
            if dataset.get('tags'):
                dataset[u'keywords'] = dataset['tags']
                dataset.pop('tags')

            log.info("Adding dataset: %s" % dataset['name'])
            user = get_action('get_site_user')({'model': model, 'ignore_auth': True}, {})
            context = {'model': model, 'session': model.Session, 'user': user['name']}
            get_action('package_create')(context, dataset)

    def import_publishers(self, translations, structure):
        '''
        Create publisher groups based on translations and structure JSON objects.
        '''
        # get group names and title translations
        log.info("Reading group structure and names/translations")
        groups = {}
        for group in translations['results']['bindings']:
            name_uri = group['s']['value']
            group_name = name_uri.split('/')[-1].lower()
            lang_uri = group['lang']['value']
            lang_name = lang_uri.split('/')[-1].lower()
            if not group_name in groups:
                groups[group_name] = {}
                groups[group_name]['titles'] = {}
            groups[group_name]['titles'][lang_name] = group['f']['value']

        # get list of child groups for each group
        for group in groups:
            groups[group]['children'] = []

            for relationship in structure['results']['bindings']:
                parent = relationship['ch']['value'].split('/')[-1].lower()
                if parent == group:
                    child = relationship['s']['value'].split('/')[-1].lower()
                    groups[group]['children'].append(child)

        # create CKAN groups
        log.info("Creating CKAN group objects")
        user = get_action('get_site_user')({'model': model, 'ignore_auth': True}, {})
        context = {'model': model, 'session': model.Session, 'user': user['name']}

        for group in groups:
            try:
                g = get_action('group_show')(context, {'id': group})
            except NotFound:
                # use the english title if we have one
                group_title = groups[group]['titles'].get('eng')
                if not group_title:
                    group_title = groups[group]['titles'].values()[0]

                group_data = {
                    'name': unicode(group),
                    'title': unicode(group_title),
                    'type': u'publisher'
                }
                g = get_action('group_create')(context, group_data)
            groups[group]['dict'] = g

        # updating group heirarchy
        log.info("Updating group hierarchy")
        for group in groups:
            if not groups[group]['children']:
                continue

            parent = groups[group]['dict']
            for child in groups[group]['children']:

                # check that child is not already in the group
                child_names = [g['name'] for g in parent.get('groups', [])]
                if child in child_names:
                    continue

                child_dict = {
                    'name': unicode(groups[child]['dict']['name']),
                    'capacity': u'member'
                }
                if 'groups' in parent:
                    parent['groups'].append(child_dict)
                else:
                    parent['groups'] = [child_dict]

            get_action('group_update')(context, parent)

        # update French translation
        log.info("Updating French translations")
        term_translations = []
        for group in groups:
            if not 'eng' in groups[group]['titles'] or\
               not 'fra' in groups[group]['titles']:
                continue

            term = groups[group]['titles']['eng']
            translation = groups[group]['titles']['fra']
            term_translations.append({
                'term': unicode(term),
                'term_translation': unicode(translation),
                'lang_code': u'fr'
            })
        get_action('term_translation_update_many')(
            context, {'data': term_translations}
        )

    def create_geo_vocab(self):
        log.info("Creating vocabulary for geographical coverage")
        user = get_action('get_site_user')({'model': model, 'ignore_auth': True}, {})
        context = {'model': model, 'session': model.Session, 'user': user['name']}

        try:
            data = {'id': forms.GEO_VOCAB_NAME}
            get_action('vocabulary_show')(context, data)
            log.error("Vocabulary %s already exists." % forms.GEO_VOCAB_NAME)
        except NotFound:
            data = {'name': forms.GEO_VOCAB_NAME}
            vocab = get_action('vocabulary_create')(context, data)
            for country_code in field_values.geographical_coverage:
                log.info("Adding tag %s to vocab %s" %
                         (country_code[0], forms.GEO_VOCAB_NAME))
                data = {'name': country_code[0], 'vocabulary_id': vocab['id']}
                get_action('tag_create')(context, data)
