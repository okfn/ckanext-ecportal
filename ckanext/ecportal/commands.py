import logging
import collections
import os
import sys
import csv
import json

import ckan
import ckan.plugins as plugins
import ckan.model as model
import ckan.logic as logic
import ckan.lib.cli as cli
import ckanext.ecportal.forms as forms
import ckanext.ecportal.searchcloud as searchcloud

log = logging.getLogger()


class InvalidDateFormat(Exception):
    pass


class ECPortalCommand(cli.CkanCommand):
    '''
    Commands:
        paster ecportal update-publishers <file (optional)> -c <config>
        paster ecportal migrate-publisher <source> <target> -c <config>
        paster ecportal migrate-odp-namespace -c <config>
        paster ecportal export-datasets <folder> -c <config>
        paster ecportal import-csv-translations -c <config>

        paster ecportal update-all-vocabs -c <config>
        paster ecportal delete-all-vocabs -c <config>

        paster ecportal update-geo-vocab <file (optional)> -c <config>
        paster ecportal update-dataset-type-vocab <file (optional)> -c <config>
        paster ecportal update-language-vocab <file (optional)> -c <config>
        paster ecportal update-status-vocab <file (optional)> -c <config>
        paster ecportal update-interop-vocab <file (optional)> -c <config>
        paster ecportal update-temporal-vocab <file (optional)> -c <config>

        paster ecportal delete-geo-vocab -c <config>
        paster ecportal delete-dataset-type-vocab -c <config>
        paster ecportal delete-language-vocab -c <config>
        paster ecportal delete-status-vocab -c <config>
        paster ecportal delete-interop-vocab -c <config>
        paster ecportal delete-temporal-vocab -c <config>

        paster ecportal purge-publisher-datasets <publisher> -c <config>
        paster ecportal purge-package-extra-revision -c <config>
        paster ecportal purge-task-data -c <config>

        paster ecportal searchcloud-install-tables -c <config>
        paster ecportal searchcloud-generate-unapproved-search-list -c <config>

    Where:
        <data> = path to XML file (format of the Eurostat bulk import metadata)
        <user> = perform actions as this CKAN user (name)
        <publisher> = a publisher name or ID
        <folder> = Output folder for dataset export
        <file> = (optional) path to input JSON or CSV file. If not specified,
                 the default files in the /data directory are used.
        <config> = path to your ckan config file

    The commands should be run from the ckanext-ecportal directory.
    '''
    summary = __doc__.split('\n')[0]
    usage = __doc__

    default_data_dir = os.path.dirname(os.path.abspath(__file__))
    default_file = {
        forms.DATASET_TYPE_VOCAB_NAME:
        default_data_dir + '/../../data/odp-dataset-type.json',
        forms.DATASET_TYPE_VOCAB_NAME:
        default_data_dir + '/../../data/odp-dataset-type.json',
        forms.GEO_VOCAB_NAME:
        default_data_dir + '/../../data/po-countries.json',
        forms.INTEROP_VOCAB_NAME:
        default_data_dir + '/../../data/odp-interoperability-level.json',
        forms.LANGUAGE_VOCAB_NAME:
        default_data_dir + '/../../data/po-languages.json',
        forms.STATUS_VOCAB_NAME:
        default_data_dir + '/../../data/odp-dataset-status.json',
        forms.TEMPORAL_VOCAB_NAME:
        default_data_dir + '/../../data/odp-temporal-granularity.json',
        'publishers': default_data_dir + '/../../data/po-corporate-bodies.json'
    }

    def command(self):
        '''
        Parse command line arguments and call appropriate method.
        '''
        if not self.args or self.args[0] in ['--help', '-h', 'help']:
            print ECPortalCommand.__doc__
            return

        cmd = self.args[0]
        self._load_config()

        user = plugins.toolkit.get_action('get_site_user')(
            {'model': model, 'ignore_auth': True}, {}
        )
        self.user_name = user['name']

        # file_path is used by update-vocab and update-publishers commands
        file_path = self.args[1] if len(self.args) >= 2 else None

        if cmd == 'update-publishers':
            self.update_publishers(file_path)

        elif cmd == 'migrate-publisher':
            if len(self.args) != 3:
                print ECPortalCommand.__doc__
                return
            self.migrate_publisher(self.args[1], self.args[2])

        elif cmd == 'update-geo-vocab':
            self.update_vocab_from_file(forms.GEO_VOCAB_NAME, file_path)

        elif cmd == 'migrate-odp-namespace':
            self.odp_namespace()

        elif cmd == 'delete-geo-vocab':
            self._delete_vocab(forms.GEO_VOCAB_NAME)

        elif cmd == 'update-dataset-type-vocab':
            self.update_vocab_from_file(forms.DATASET_TYPE_VOCAB_NAME,
                                        file_path)

        elif cmd == 'delete-dataset-type-vocab':
            self._delete_vocab(forms.DATASET_TYPE_VOCAB_NAME)

        elif cmd == 'update-language-vocab':
            self.update_vocab_from_file(forms.LANGUAGE_VOCAB_NAME, file_path)

        elif cmd == 'delete-language-vocab':
            self._delete_vocab(forms.LANGUAGE_VOCAB_NAME)

        elif cmd == 'update-status-vocab':
            self.update_vocab_from_file(forms.STATUS_VOCAB_NAME, file_path)

        elif cmd == 'delete-status-vocab':
            self._delete_vocab(forms.STATUS_VOCAB_NAME)

        elif cmd == 'update-interop-vocab':
            self.update_vocab_from_file(forms.INTEROP_VOCAB_NAME, file_path)

        elif cmd == 'delete-interop-vocab':
            self._delete_vocab(forms.INTEROP_VOCAB_NAME)

        elif cmd == 'update-temporal-vocab':
            self.update_vocab_from_file(forms.TEMPORAL_VOCAB_NAME, file_path)

        elif cmd == 'delete-temporal-vocab':
            self._delete_vocab(forms.TEMPORAL_VOCAB_NAME)

        elif cmd == 'update-all-vocabs':
            self.update_all_vocabs()

        elif cmd == 'delete-all-vocabs':
            self.delete_all_vocabs()

        elif cmd == 'purge-publisher-datasets':
            if len(self.args) != 2:
                print ECPortalCommand.__doc__
                return
            self.purge_publisher_datasets(self.args[1])

        elif cmd == 'purge-package-extra-revision':
            self.purge_package_extra_revision()

        elif cmd == 'purge-task-data':
            self.purge_task_data()

        elif cmd == 'searchcloud-install-tables':
            self.searchcloud_install_tables()

        elif cmd == 'searchcloud-generate-unapproved-search-list':
            self.searchcloud_generate_unapproved_search_list()

        elif cmd == 'import-csv-translations':
            self.import_csv_translation()

        else:
            log.error('Command "%s" not recognized' % (cmd,))

    def _read_publishers_from_file(self, file_path=None):
        if not file_path:
            file_path = self.default_file['publishers']
        if not os.path.exists(file_path):
            log.error('File {0} does not exist'.format(file_path))
            sys.exit(1)

        with open(file_path) as json_file:
            full_json = json.loads(json_file.read())

        return list(self._parse_publishers_from(full_json))

    def _add_publishers(self, publishers):
        log.info('Creating CKAN publisher (group) objects')

        groups_title_lookup = {}

        for publisher in publishers:
            context = {'model': model,
                       'session': model.Session,
                       'user': self.user_name}

            if publisher.lang_code == 'en':
                group = {'name': publisher.name,
                         'title': publisher.title,
                         'type': u'organization'}
                plugins.toolkit.get_action('group_create')(context, group)
                log.info('Added new publisher: %s [%s]',
                         publisher.title, publisher.name)
                groups_title_lookup[publisher.name] = \
                    publisher.title or publisher.name

        context = {'model': model,
                   'session': model.Session,
                   'user': self.user_name}
        self._update_translations(publishers, groups_title_lookup, context)

    _Publisher = collections.namedtuple('Publisher', 'name title lang_code')

    def _parse_publishers_from(self, data):
        for item in data['results']['bindings']:
            yield self._Publisher(
                name=item['term']['value'].split('/')[-1].lower(),
                title=item['label']['value'],
                lang_code=item['language']['value'])

    def migrate_publisher(self, source_publisher_name, target_publisher_name):
        '''
        Migrate datasets and users from one publisher to another.
        '''
        context = {'model': model,
                   'session': model.Session,
                   'ecodp_with_package_list': True,
                   'ecodp_update_packages': True,
                   'user': self.user_name}

        source_publisher = plugins.toolkit.get_action('group_show')(
            context, {'id': source_publisher_name})

        target_publisher = plugins.toolkit.get_action('group_show')(
            context, {'id': target_publisher_name})

        # Migrate users
        source_users = self._extract_members(source_publisher['users'])
        target_users = self._extract_members(target_publisher['users'])

        source_publisher['users'] = []
        target_publisher['users'] = self._migrate_user_lists(source_users,
                                                             target_users)

        # Migrate datasets
        source_datasets = self._extract_members(source_publisher['packages'])
        target_datasets = self._extract_members(target_publisher['packages'])

        source_publisher['packages'] = []
        target_publisher['packages'] = self._migrate_dataset_lists(
            source_datasets, target_datasets)

        # Perform the updates
        # TODO: make this one atomic action. (defer_commit)
        plugins.toolkit.get_action('group_update')(context, source_publisher)
        plugins.toolkit.get_action('group_update')(context, target_publisher)

    def odp_namespace(self):
        sql = '''
        begin;

        update tag set name =
            replace(name,
                    'http://ec.europa.eu/open-data',
                    'http://open-data.europa.eu')
        where name like '%http://ec.europa.eu/open-data%';

        update term_translation set term =
            replace(term,
                    'http://ec.europa.eu/open-data',
                    'http://open-data.europa.eu')
        where term like '%http://ec.europa.eu/open-data%';

        update resource set resource_type =
            replace(resource_type,
                    'http://ec.europa.eu/open-data',
                    'http://open-data.europa.eu')
        where resource_type like '%http://ec.europa.eu/open-data%';

        update resource_revision set resource_type =
            replace(resource_type,
                    'http://ec.europa.eu/open-data',
                    'http://open-data.europa.eu')
        where resource_type like '%http://ec.europa.eu/open-data%';

        update package_extra set value =
            replace(value,
                    'http://ec.europa.eu/open-data',
                    'http://open-data.europa.eu')
        where key <> 'rdf' and value like '%http://ec.europa.eu/open-data%';

        commit;
        '''
        model.Session.execute(sql)

    def _extract_members(self, members):
        '''Strips redundant information from members of a group'''
        return [{'name': member['name'],
                 'capacity': member['capacity']}
                for member in members]

    def _migrate_dataset_lists(self, source_datasets, target_datasets):
        '''Migrate datasets from source into target.

        Returns a new list leaving original lists untouched.

        The merging retains the strictest capacity.  That is, if the same
        dataset is 'private' in either list, it will remain private in the
        result.
        '''
        VALID_CAPACITIES = ['private', 'public']

        def user_capacity_merger(c1, c2):
            assert c1 in VALID_CAPACITIES
            assert c2 in VALID_CAPACITIES
            if c1 == c2:
                return c1
            else:
                return 'private'  # assume just two valid capicities

        return self._merge_members(source_datasets,
                                   target_datasets,
                                   user_capacity_merger)

    def _migrate_user_lists(self, source_users, target_users):
        '''Migrate users from source into target.

        Returns a new list leaving original lists untouched.

        The merging is quite simple, and retains user's permissions for both
        lists.

            - The target list will not lose any users.
            - Source users will be added to the target with the highest
              capacity of membership that the user has in either list.  Ie - If
              a user is an admin in the source list, they will become an admin
              in the target list.  Or if a user is an admin in the target list,
              they will retain that capacity, regardless of capacity in the
              source list.
         '''
        VALID_CAPACITIES = ['admin', 'editor']

        def user_capacity_merger(c1, c2):
            assert c1 in VALID_CAPACITIES
            assert c2 in VALID_CAPACITIES
            if c1 == c2:
                return c1
            else:
                return 'admin'  # assume just two valid capicities

        return self._merge_members(source_users,
                                   target_users,
                                   user_capacity_merger)

    def _merge_members(self, source_members, target_members, capacity_merger):
        '''Migrates members from source into target.

        Returns a new list, leaving original lists (and member dicts)
        untouched.

        If the member is found in both lists, then the member's new capacity
        is handled by the ``capacity_merger`` function.

        :param source_members: List of member dicts
        :param target_members: List of member dicts
        :param capacity_merger: Function
                (source_capacity, target_capacity) -> merged_capacity
        '''
        source_member_names = set(member['name'] for member in source_members)
        target_member_names = set(member['name'] for member in target_members)

        target_capacities = dict((member['name'], member['capacity'])
                                 for member in target_members)

        result = [member.copy() for member in target_members
                  if member['name'] not in source_member_names]

        result += [member.copy() for member in source_members
                   if member['name'] not in target_member_names]

        for member in source_members:
            name = member['name']
            if name not in target_member_names:
                continue

            member = member.copy()
            source_capacity = member['capacity']
            target_capacity = target_capacities[name]
            member['capacity'] = capacity_merger(source_capacity,
                                                 target_capacity)

            if source_capacity != target_capacity:
                log.warn('Mismatched member capacities: '
                         '%s will be migrated as %s'
                         % (name, member['capacity']))

            result.append(member)

        return result

    def update_publishers(self, file_path=None):
        '''
        Update existing publisher groups.

         - new publishers are added
         - existing publishers are updated
         - deleted publishers are left untouched
        '''

        context = {'model': model,
                   'session': model.Session,
                   'user': self.user_name}

        group_list_context = context.copy()
        group_list_context['with_datasets'] = True
        existing_groups = plugins.toolkit.get_action('group_list')(
            group_list_context, {'groups': '', 'all_fields': True})

        existing_groups = dict((g['name'], g) for g in existing_groups)

        publishers = self._read_publishers_from_file(file_path)

        new_publishers = [p for p in publishers
                          if p.name not in existing_groups]
        existing_publishers = [p for p in publishers
                               if p.name in existing_groups]

        deleted_publishers = [
            group_name for group_name in existing_groups.keys()
            if group_name not in set(p.name for p in publishers)]

        self._add_publishers(new_publishers)

        # Update existing publishers
        groups_title_lookup = {}
        for publisher in existing_publishers:
            context = {'model': model,
                       'session': model.Session,
                       'user': self.user_name}
            if publisher.lang_code != 'en':
                continue
            existing_group = existing_groups[publisher.name]
            if existing_group['title'] != publisher.title:
                # Update the Group
                log.info('Publisher required update: %s, [%s].  (Was: %s)',
                         publisher.title,
                         publisher.name,
                         existing_group['title'])
                group = existing_group.copy()
                group.update(title=publisher.title)
                plugins.toolkit.get_action('group_update')(context, group)
            # Track the group titles
            groups_title_lookup[publisher.name] = \
                publisher.title or publisher.name

        # Update translations.
        context = {'model': model,
                   'session': model.Session,
                   'user': self.user_name}
        self._update_translations(existing_publishers, groups_title_lookup,
                                  context)

        # Just log which publishers should be deleted.
        for group_name in deleted_publishers:
            group = existing_groups[group_name]
            if group['packages'] == 0:
                log.info('Deleting old group %s as it has no datasets.',
                         group['name'])
                context = {'model': model,
                           'session': model.Session,
                           'user': self.user_name}
                plugins.toolkit.get_action('group_delete')(
                    context, {'id': group['id']})

            else:
                log.warn('Not deleting old publisher: %s because '
                         'it has datasets associated with it.',
                         group_name)

    def _update_translations(self, publishers, groups_title_lookup, context):
        translations = []
        for publisher in publishers:
            if publisher.lang_code == 'en':
                continue
            if not publisher.title:
                continue

            if publisher.name not in groups_title_lookup:
                log.warn('No english version of %s [%s].  Skipping',
                         publisher.title, publisher.name)
                continue

            translations.append({
                'term': groups_title_lookup[publisher.name],
                'term_translation': publisher.title,
                'lang_code': publisher.lang_code
            })

        if translations:
            plugins.toolkit.get_action('term_translation_update_many')(
                context, {'data': translations}
            )

    def _create_vocab(self, context, vocab_name):
        try:
            log.info('Creating vocabulary "%s"' % vocab_name)
            vocab = plugins.toolkit.get_action('vocabulary_create')(
                context, {'name': vocab_name}
            )
        except logic.ValidationError, ve:
            # ignore errors about the vocab already existing
            # if it's a different error, reraise
            if not 'name is already in use' in str(ve.error_dict):
                raise ve
            log.info('Vocabulary "%s" already exists' % vocab_name)
            vocab = plugins.toolkit.get_action('vocabulary_show')(
                context, {'id': vocab_name}
            )
        return vocab

    def _delete_vocab(self, vocab_name):
        log.info('Deleting vocabulary "{0}"'.format(vocab_name))

        context = {'model': model,
                   'session': model.Session,
                   'user': self.user_name}

        try:
            vocab = plugins.toolkit.get_action('vocabulary_show')(
                context, {'id': vocab_name})
        except plugins.toolkit.ObjectNotFound:
                log.info('Vocab "{0}" not found, ignoring'.format(vocab_name))
                return

        for tag in vocab.get('tags'):
            log.info('Deleting tag "%s"' % tag['name'])
            plugins.toolkit.get_action('tag_delete')(
                context, {'id': tag['id']})
        plugins.toolkit.get_action('vocabulary_delete')(
            context, {'id': vocab['id']})

    def update_vocab_from_file(self, vocab_name, file_path=None):
        '''
        Create vocabularies and vocabulary tags using JSON files.
        If the vocabulary already exists, or the tag is already part
        of the vocab, it will be ignored.
        '''
        if not file_path:
            file_path = self.default_file[vocab_name]
        if not os.path.exists(file_path):
            log.error('File {0} does not exist'.format(file_path))
            sys.exit(1)

        context = {'model': model, 'session': model.Session,
                   'user': self.user_name}
        vocab = self._create_vocab(context, vocab_name)

        with open(file_path) as json_file:
            full_json = json.loads(json_file.read())

        translations = []
        tag_schema = ckan.logic.schema.default_create_tag_schema()
        tag_schema['name'] = [unicode]

        existing_tags = plugins.toolkit.get_action('tag_list')(
            context, {'vocabulary_id': vocab['id']})
        updated_tags = []

        for item in full_json['results']['bindings']:
            if item['language']['value'] == 'en':
                context = {'model': model,
                           'session': model.Session,
                           'user': self.user_name,
                           'schema': tag_schema}

                if (item['label']['value'] == 'Multilingual Code' and
                        vocab_name == forms.LANGUAGE_VOCAB_NAME):
                    continue

                term = item['term']['value']

                if not term in existing_tags:
                    log.info('Creating tag "{0}"'.format(term))
                    tag = {'name': term,
                           'vocabulary_id': vocab['id']}
                    plugins.toolkit.get_action('tag_create')(context, tag)

                updated_tags.append(term)

        for item in full_json['results']['bindings']:
            term = item['term']['value']
            translation = item['label']['value']
            if (translation == 'Multilingual Code' and
                    vocab_name == forms.LANGUAGE_VOCAB_NAME):
                continue
            if not translation:
                continue

            translations.append({'term': term,
                                 'term_translation': translation,
                                 'lang_code': item['language']['value']})

        plugins.toolkit.get_action('term_translation_update_many')(
            context, {'data': translations})

        # remove deleted tags
        # TODO: can we also remove translations of deleted tags?
        tags_to_delete = [t for t in existing_tags if not t in updated_tags]
        for tag_name in tags_to_delete:
            log.info('Deleting tag "{0}"'.format(tag_name))
            tag = {'id': tag_name,
                   'vocabulary_id': vocab['id']}
            plugins.toolkit.get_action('tag_delete')(context, tag)

    def _lookup_term(self, en_translation):
        '''
        Lookup existing term in term_translation table that has the given
        English translation. If none found, return the English translation.
        '''
        engine = model.meta.engine
        sql = '''
            SELECT term FROM term_translation
            WHERE term_translation=%s
            AND lang_code='en';
        '''
        result = engine.execute(sql, en_translation).fetchone()
        if not result:
            return en_translation
        else:
            return result[0]

    def import_csv_translation(self):
        file_name = os.path.dirname(os.path.abspath(__file__)) + \
            '/../../data/odp-vocabulary-translate.csv'
        voc_translate = file(file_name)
        voc_dicts = csv.DictReader(voc_translate)
        translations = []

        for line in voc_dicts:
            term = line.pop('en')
            for key in line:
                translations.append(
                    {'term': self._lookup_term(term),
                     'lang_code': key,
                     'term_translation': line[key].decode('utf8')})

        context = {'model': model, 'session': model.Session,
                   'user': self.user_name, 'extras_as_string': True}

        plugins.toolkit.get_action('term_translation_update_many')(
            context, {'data': translations}
        )

    def update_all_vocabs(self):
        self.update_vocab_from_file(forms.GEO_VOCAB_NAME)
        self.update_vocab_from_file(forms.DATASET_TYPE_VOCAB_NAME)
        self.update_vocab_from_file(forms.LANGUAGE_VOCAB_NAME)
        self.update_vocab_from_file(forms.STATUS_VOCAB_NAME)
        self.update_vocab_from_file(forms.INTEROP_VOCAB_NAME)
        self.update_vocab_from_file(forms.TEMPORAL_VOCAB_NAME)
        self.import_csv_translation()

    def delete_all_vocabs(self):
        self._delete_vocab(forms.GEO_VOCAB_NAME)
        self._delete_vocab(forms.DATASET_TYPE_VOCAB_NAME)
        self._delete_vocab(forms.LANGUAGE_VOCAB_NAME)
        self._delete_vocab(forms.STATUS_VOCAB_NAME)
        self._delete_vocab(forms.INTEROP_VOCAB_NAME)
        self._delete_vocab(forms.TEMPORAL_VOCAB_NAME)

    def purge_publisher_datasets(self, publisher_name):
        context = {'model': model, 'session': model.Session,
                   'user': self.user_name}
        log.warn(plugins.toolkit.get_action('purge_publisher_datasets')(
            context, {'name': publisher_name}))

    def purge_package_extra_revision(self):
        context = {'model': model, 'session': model.Session,
                   'user': self.user_name}
        log.warn(plugins.toolkit.get_action('purge_package_extra_revision')(
            context, {}))

    def purge_task_data(self):
        context = {'model': model, 'session': model.Session,
                   'user': self.user_name}
        log.warn(plugins.toolkit.get_action('purge_task_data')(context, {}))

    def searchcloud_generate_unapproved_search_list(self):
        '''
        This command is usually executed via a Cron job once a week to
        replace the data in the search_popular_latest table
        '''
        searchcloud.generate_unapproved_list(model.Session, days=30)
        model.Session.commit()

    def searchcloud_install_tables(self):
        def out(text):
            print text
        searchcloud.install_tables(model.Session, out)
        model.Session.commit()
