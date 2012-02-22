import os
import json
from ckan import model
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
        rev = model.repo.new_revision()
        rev.message = u'Importing EC Portal Publisher Info'
        for group in groups:
            g = model.Group.get(group)
            if not g:
                # use the english title if we have one
                title_langs = [k.keys()[0] for k in groups[group]['titles']]
                if 'eng' in title_langs:
                    group_title = [t['eng'] for t in groups[group]['titles'] if t.get('eng')][0]
                else:
                    group_title = groups[group]['titles'][0][title_langs[0]]

                g = model.Group(name=group, title=group_title, type=u'publisher')
                model.Session.add(g)
            groups[group]['id'] = g.id

        # TODO: setup group heirarchy

        model.repo.commit_and_remove()
