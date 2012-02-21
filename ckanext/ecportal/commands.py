import os
import json
from ckan import model
from ckan.lib.cli import CkanCommand
from ckan.logic import get_action, NotFound

import logging
log = logging.getLogger()


class ECPortalCommand(CkanCommand):
    '''
    Usage::

        paster ecportal import-publishers <path to translations JSON file> <path to structure JSON file> -c <path to config file>

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
        '''
        user = get_action('get_site_user')({'model': model, 'ignore_auth': True}, {})
        context = {'model': model, 'session': model.Session, 'user': user['name']}
        print translations
        print structure
