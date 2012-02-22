import os
import json
from ckan import model
from ckan.logic import get_action, NotFound
from ckan.lib.cli import CkanCommand

import logging
log = logging.getLogger()


class ECPortalCommand(CkanCommand):
    '''
    Usage:

        paster ecportal import-publishers <translations> <structure> -c <config>

    Where:
        <translations> = path to translations.json
        <structure> = path to structure.json
        <config> = path to your ckan config file

    The command should be run from the ckanext-ecportal directory.
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

        if cmd == 'import-publishers':
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
        else:
            log.error('Command "%s" not recognized' % (cmd,))

    def import_publishers(self, translations, structure):
        '''
        Create publisher groups based on translations and structure JSON objects.
        '''
        # get group names and title translations
        log.info("Reading group structure and names/translations")
        groups = {}
        for group in translations['results']['bindings']:
            translation = {}
            name_uri = group['s']['value']
            group_name = name_uri.split('/')[-1].lower()
            lang_uri = group['lang']['value']
            lang_name = lang_uri.split('/')[-1].lower()
            translation[lang_name] = group['f']['value']
            if not group_name in groups:
                groups[group_name] = {}
                groups[group_name]['titles'] = []
            groups[group_name]['titles'].append(translation)

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
                title_langs = [k.keys()[0] for k in groups[group]['titles']]
                if 'eng' in title_langs:
                    group_title = groups[group]['titles'][0]['eng']
                else:
                    group_title = groups[group]['titles'][0][title_langs[0]]

                group_data = {
                    'name': group,
                    'title': group_title,
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
                    'name': groups[child]['dict']['name'],
                    'capacity': u'member'
                }
                if 'groups' in parent:
                    parent['groups'].append(child_dict)
                else:
                    parent['groups'] = [child_dict]

            get_action('group_update')(context, parent)
