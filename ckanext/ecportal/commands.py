import collections
import os
import sys
import re
import csv
import json
import urllib
import lxml.etree
import ckan
import ckan.model as model
import ckan.logic as logic
import ckan.lib.cli as cli
import requests
import forms
import ckanext.ecportal.searchcloud as searchcloud
import logging

log = logging.getLogger()


class InvalidDateFormat(Exception):
    pass


class ECPortalCommand(cli.CkanCommand):
    '''
    Commands:

        paster ecportal import-data <data> <user> -c <config>
        paster ecportal import-publishers -c <config>
        paster ecportal update-publishers -c <config>
        paster ecportal migrate-publisher <source> <target> -c <config>
        paster ecportal export-datasets <folder> -c <config>
        paster ecportal import-csv-translations -c <config>

        paster ecportal create-geo-vocab -c <config>
        paster ecportal create-dataset-type-vocab -c <config>
        paster ecportal create-language-vocab -c <config>
        paster ecportal create-status-vocab -c <config>
        paster ecportal create-interop-vocab -c <config>
        paster ecportal create-temporal-vocab -c <config>
        paster ecportal create-all-vocabs -c <config>

        paster ecportal delete-geo-vocab -c <config>
        paster ecportal delete-dataset-type-vocab -c <config>
        paster ecportal delete-language-vocab -c <config>
        paster ecportal delete-status-vocab -c <config>
        paster ecportal delete-interop-vocab -c <config>
        paster ecportal delete-temporal-vocab -c <config>
        paster ecportal delete-all-vocabs -c <config>

        paster ecportal searchcloud-install-tables -c <config>
        paster ecportal searchcloud-generate-unapproved-search-list -c <config>

    Where:
        <data> = path to XML file (format of the Eurostat bulk import metadata)
        <user> = perform actions as this CKAN user (name)
        <folder> = Output folder for dataset export
        <config> = path to your ckan config file

    The commands should be run from the ckanext-ecportal directory.
    '''
    summary = __doc__.split('\n')[0]
    usage = __doc__

    # date formats used in data-import command
    year = re.compile('\d\d\d\d\Z')
    year_month = re.compile('\d\d\d\dM\d\d\Z')
    year_month_day = re.compile('\d\d\d\dM\d\dD\d\d\Z')
    year_quarter = re.compile('\d\d\d\dQ\d\Z')
    year_half = re.compile('\d\d\d\dS\d\Z')
    day_month_year = re.compile('\d\d\.\d\d\.\d\d\d\d\Z')

    # data-import: languages with translations in the imported metadata file
    data_import_langs = [u'fr', u'de']

    def command(self):
        '''
        Parse command line arguments and call appropriate method.
        '''
        if not self.args or self.args[0] in ['--help', '-h', 'help']:
            print ECPortalCommand.__doc__
            return

        cmd = self.args[0]
        self._load_config()

        user = logic.get_action('get_site_user')(
            {'model': model, 'ignore_auth': True}, {}
        )
        self.user_name = user['name']

        if cmd == 'import-data':
            if not len(self.args) in [2, 3]:
                print ECPortalCommand.__doc__
                return

            data = self.args[1]
            if len(self.args) == 3:
                self.user_name = self.args[2]

            if 'http://' in data:
                self.import_data(urllib.urlopen(data))
            else:
                self.import_data(data)

        elif cmd == 'export-datasets':
            if not len(self.args) == 3:
                print ECPortalCommand.__doc__
                return
            self.export_datasets(self.args[1], self.args[2])

        elif cmd == 'import-publishers':
            if not len(self.args) == 1:
                print ECPortalCommand.__doc__
                return
            self.import_publishers()

        elif cmd == 'update-publishers':
            self.update_publishers()

        elif cmd == 'migrate-publisher':
            if len(self.args) != 3:
                print ECPortalCommand.__doc__
                return
            self.migrate_publisher(self.args[1], self.args[2])

        elif cmd == 'create-geo-vocab':
            if not len(self.args) == 1:
                print ECPortalCommand.__doc__
                return
            self.create_geo_vocab()

        elif cmd == 'delete-geo-vocab':
            self.delete_geo_vocab()

        elif cmd == 'create-dataset-type-vocab':
            self.create_dataset_type_vocab()

        elif cmd == 'delete-dataset-type-vocab':
            self.delete_dataset_type_vocab()

        elif cmd == 'create-language-vocab':
            self.create_language_vocab()

        elif cmd == 'delete-language-vocab':
            self.delete_language_vocab()

        elif cmd == 'create-status-vocab':
            self.create_status_vocab()

        elif cmd == 'delete-status-vocab':
            self.delete_status_vocab()

        elif cmd == 'create-interop-vocab':
            self.create_interop_vocab()

        elif cmd == 'delete-interop-vocab':
            self.delete_interop_vocab()

        elif cmd == 'create-temporal-vocab':
            self.create_temporal_vocab()

        elif cmd == 'delete-temporal-vocab':
            self.delete_temporal_vocab()

        elif cmd == 'create-all-vocabs':
            self.create_all_vocabs()

        elif cmd == 'delete-all-vocabs':
            self.delete_all_vocabs()

        elif cmd == 'searchcloud-install-tables':
            self.searchcloud_install_tables()

        elif cmd == 'searchcloud-generate-unapproved-search-list':
            self.searchcloud_generate_unapproved_search_list()

        elif cmd == 'import-csv-translations':
            self.import_csv_translation()

        else:
            log.error('Command "%s" not recognized' % (cmd,))

    def _temporal_granularity(self, isodate):
        '''
        Return the granularity (string) of isodate: year, month or day.
        '''
        if len(isodate) == 4:
            return 'year'
        elif len(isodate) == 7:
            return 'month'
        elif len(isodate) == 10:
            return 'day'
        else:
            raise InvalidDateFormat

    def _isodate(self, date):
        '''
        Return a unicode string consisting of date converted to ISO 8601 format
        (YYYY-MM-DD, YYYY-MM or YYYY).
        '''
        if not date:
            return None

        isodate = None

        if self.day_month_year.match(date):
            dd = date.split('.')[0]
            mm = date.split('.')[1]
            yyyy = date.split('.')[2]
            isodate = u'%s-%s-%s' % (yyyy, mm, dd)
        elif self.year.match(date):
            isodate = unicode(date)
        elif self.year_month.match(date):
            yyyy = date.split('M')[0]
            mm = date.split('M')[1]
            isodate = u'%s-%s' % (yyyy, mm)
        elif self.year_month_day.match(date):
            yyyy = date.split('M')[0]
            mm_dd = date.split('M')[1]
            mm = mm_dd.split('D')[0]
            dd = mm_dd.split('D')[1]
            isodate = u'%s-%s-%s' % (yyyy, mm, dd)
        elif self.year_quarter.match(date):
            yyyy = date.split('Q')[0]
            q = int(date.split('Q')[1])
            mm = ((q - 1) * 3) + 1
            isodate = u'%s-%02d' % (yyyy, mm)
        elif self.year_half.match(date):
            yyyy = date.split('S')[0]
            h = int(date.split('S')[1])
            mm = ((h - 1) * 6) + 1
            isodate = u'%s-%02d' % (yyyy, mm)

        return isodate

    def _import_dataset(self, node, parents, namespace=''):
        '''
        From a leaf node in the Eurostat metadata, create and add
        a CKAN dataset.
        '''
        dataset = {}
        dataset['name'] = unicode(node.find('{%s}code' % namespace).text)
        dataset['title'] = unicode(node.find('{%s}title[@language="en"]' % namespace).text)
        dataset['license_id'] = u'ec-eurostat'
        dataset['published_by'] = u'estat'

        # modified date
        modified = self._isodate(node.find('{%s}lastUpdate' % namespace).text)
        if modified:
            dataset['modified_date'] = modified

        # temporal coverage and granularity
        tc_from = self._isodate(node.find('{%s}dataStart' % namespace).text)
        if tc_from:
            dataset['temporal_coverage_from'] = tc_from
            dataset['temporal_granularity'] = self._temporal_granularity(tc_from)
        tc_to = self._isodate(node.find('{%s}dataEnd' % namespace).text)
        if tc_to:
            dataset['temporal_coverage_to'] = tc_to

        url = node.find('{%s}metadata' % namespace).text
        if url:
            dataset['url'] = unicode(url)

        # themes as extras
        dataset['extras'] = []
        themes = [n.find('{%s}title[@language="en"]' % namespace).text
                  for n in parents[1:]]
        for n, theme in enumerate(themes):
            dataset['extras'].append({
                'key': u'theme%d' % (n + 1),
                'value': unicode(theme)
            })

        # add resources
        dataset['resources'] = []
        resources = node.findall('{%s}downloadLink' % namespace)
        for resource in resources:
            dataset['resources'].append({
                'url': unicode(resource.text),
                'format': unicode(resource.attrib['format'])
            })

        # add dataset to CKAN instance
        log.info('Adding dataset: %s' % dataset['name'])
        context = {'model': model, 'session': model.Session,
                    'user': self.user_name, 'extras_as_string': True}
        try:
            logic.get_action('package_create')(context, dataset)
        except logic.ValidationError, ve:
            log.error('Could not add dataset %s: %s' %
                      (dataset['name'], str(ve.error_dict)))

        # add title translations to translation table
        log.info('Updating translations for dataset %s' % dataset['name'])
        translations = []

        for lang in self.data_import_langs:
            lang_node = node.find('{%s}title[@language="%s"]' % (namespace, lang))
            if lang_node is not None:
                translations.append({
                    'term': dataset['title'],
                    'term_translation': unicode(lang_node.text),
                    'lang_code': lang
                })

        if translations:
            logic.get_action('term_translation_update_many')(
                context, {'data': translations}
            )

    def _import_data_node(self, node, parents, namespace=''):
        if node.tag == ('{%s}leaf' % namespace):
            self._import_dataset(node, parents, namespace)

        elif node.tag == ('{%s}branch' % namespace):
            # add title translations to translation table
            title = node.find('{%s}title[@language="en"]' % namespace)
            if title is not None:
                log.info('Updating translations for theme %s' % title.text)
                translations = []

                for lang in self.data_import_langs:
                    lang_node = node.find('{%s}title[@language="%s"]' % (namespace, lang))
                    if lang_node is not None:
                        translations.append({
                            'term': unicode(title.text),
                            'term_translation': unicode(lang_node.text),
                            'lang_code': lang
                        })

                if translations:
                    context = {'model': model, 'session': model.Session,
                                'user': self.user_name, 'extras_as_string': True}
                    logic.get_action('term_translation_update_many')(
                        context, {'data': translations}
                    )

            # add this node as a parent and import child nodes
            for child in node:
                self._import_data_node(child, parents + [node], namespace)

        elif node.tag == ('{%s}children' % namespace):
            for child in node:
                self._import_data_node(child, parents, namespace)

    def import_data(self, xml_file):
        '''
        Import datasets in the format of the Eurostat bulk downloads
        metadata XML file.
        '''
        tree = lxml.etree.parse(xml_file)
        namespace = tree.getroot().tag[1:].split('}')[0]
        self._import_data_node(tree.getroot()[0], [], namespace)

    def export_datasets(self, output_folder, fetch_url):
        '''
        Export datasets as RDF to an output folder.
        '''
        import urlparse

        user = logic.get_action('get_site_user')({'model': model, 'ignore_auth': True}, {})
        context = {'model': model, 'session': model.Session, 'user': user['name']}
        dataset_names = logic.get_action('package_list')(context, {})
        for dataset_name in dataset_names:
            dataset_dict = logic.get_action('package_show')(context, {'id': dataset_name})
            if not dataset_dict['state'] == 'active':
                continue

            url = ckan.lib.helpers.url_for(controller='package',
                                           action='read',
                                           id=dataset_dict['name'])

            url = urlparse.urljoin(fetch_url, url[1:]) + '.rdf'

            try:
                filename = os.path.join(output_folder, dataset_dict['name']) + ".rdf"
                print filename
                r = requests.get(url, auth=('ec', 'ecportal'))
                with open(filename, 'wb') as f:
                    f.write(r.content)
            except IOError, ioe:
                sys.stderr.write(str(ioe) + "\n")

    def import_publishers(self):
        '''
        Create publisher groups based on translations and structure JSON objects.
        '''
        # get group names and title translations
        log.info('Reading group structure and names/translations')

        publishers = self._read_publishers_from_file()
        self._add_publishers(publishers)

    def _read_publishers_from_file(self):
        file_name = os.path.dirname(os.path.abspath(__file__)) + '/../../data/po-corporate-bodies.json'
        with open(file_name) as json_file:
            full_json = json.loads(json_file.read())

        return list(self._parse_publishers_from(full_json))

    def _add_publishers(self, publishers):

        ### get out english 

        groups_title_lookup = {}

        log.info('Creating CKAN group objects')
        user = logic.get_action('get_site_user')({'model': model, 'ignore_auth': True}, {})

        for publisher in publishers:
            context = {'model': model, 'session': model.Session, 'user': user['name']}

            if publisher.lang_code == "en":
                group = {
                    'name': publisher.name,
                    'title': publisher.title,
                    'type': u'organization'
                }
                logic.get_action('group_create')(context, group)
                log.info("Added new publisher: %s [%s]", publisher.title, publisher.name)
                groups_title_lookup[publisher.name] = publisher.title or publisher.name

        context = {'model': model, 'session': model.Session, 'user': user['name']}
        self._update_translations(publishers, groups_title_lookup, context)

    _Publisher = collections.namedtuple('Publisher', 'name title lang_code')
    
    def _parse_publishers_from(self, data):
        
        for item in data['results']['bindings']:
            yield self._Publisher(
                    name = item["term"]["value"].split('/')[-1].lower(),
                    title = item["label"]["value"],
                    lang_code = item["language"]["value"])

    def migrate_publisher(self, source_publisher_name, target_publisher_name):
        '''
        Migrate datasets and users from one publisher to another.
        '''

        user = logic.get_action('get_site_user')({'model': model, 'ignore_auth': True}, {})
        context = {'model': model,
                   'session': model.Session,
                   'ecodp_with_package_list': True,
                   'ecodp_update_packages': True,
                   'user': user['name']}

        source_publisher = logic.get_action('group_show')(
                context,
                {'id': source_publisher_name})

        target_publisher = logic.get_action('group_show')(
                context,
                {'id': target_publisher_name})

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
        target_publisher['packages'] = self._migrate_dataset_lists(source_datasets,
                                                                   target_datasets)

        # Perform the updates
        # TODO: make this one atomic action. (defer_commit)
        logic.get_action('group_update')(context, source_publisher)
        logic.get_action('group_update')(context, target_publisher)

    def _extract_members(self, members):
        '''Strips redundant information from members of a group'''
        return [ { 'name': member['name'],
                   'capacity': member['capacity'] } \
                           for member in members ]
                    

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
                return 'private'  ## Assume just two valid capicities

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
                return 'admin'  ## Assume just two valid capicities

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

        source_member_names = set( member['name'] for member in source_members)
        target_member_names = set( member['name'] for member in target_members)

        target_capacities = dict((member['name'], member['capacity']) \
                                    for member in target_members)

        result = [ member.copy() for member in target_members \
                               if member['name'] not in source_member_names ]

        result += [ member.copy() for member in source_members \
                                if member['name'] not in target_member_names ]

        for member in source_members:
            name = member['name']
            if name not in target_member_names:
                continue

            member = member.copy()
            source_capacity = member['capacity']
            target_capacity = target_capacities[name]
            member['capacity'] = capacity_merger(source_capacity, target_capacity)

            if source_capacity != target_capacity:
                log.warn('Mismatched member capacities: %s will be migrated as %s' % (
                            name, member['capacity']))

            result.append(member)
        
        return result


    def update_publishers(self):
        '''
        Update existing publisher groups.

         - new publishers are added
         - existing publishers are updated
         - deleted publishers are left untouched
        '''

        user = logic.get_action('get_site_user')({'model': model, 'ignore_auth': True}, {})
        context = {'model': model, 'session': model.Session, 'user': user['name']}

        group_list_context = context.copy()
        group_list_context['with_datasets'] = True
        existing_groups = logic.get_action('group_list')(
                group_list_context,
                {'groups': '', 'all_fields': True})

        existing_groups = dict((g['name'], g) for g in existing_groups)

        publishers = self._read_publishers_from_file()

        new_publishers = [ p for p in publishers if p.name not in existing_groups ]
        existing_publishers = [ p for p in publishers if p.name in existing_groups ]

        deleted_publishers = [ group_name for group_name in existing_groups.keys() \
                                 if group_name not in set(p.name for p in publishers) ]

        self._add_publishers(new_publishers)

        # Update existing publishers
        groups_title_lookup = {}
        for publisher in existing_publishers:
            context = {'model': model, 'session': model.Session, 'user': user['name']}
            if publisher.lang_code != "en":
                continue
            existing_group = existing_groups[publisher.name]
            if existing_group["title"] != publisher.title:
                # Update the Group
                log.info("Publisher required update: %s, [%s].  (Was: %s)",
                         publisher.title,
                         publisher.name,
                         existing_group['title'])
                group = existing_group.copy()
                group.update(title=publisher.title)
                logic.get_action('group_update')(context, group)
            # Track the group titles
            groups_title_lookup[publisher.name] = publisher.title or publisher.name

        # Update translations.
        context = {'model': model, 'session': model.Session, 'user': user['name']}
        self._update_translations(existing_publishers, groups_title_lookup, context)

        # Just log which publishers should be deleted.
        for group_name in deleted_publishers:
            group = existing_groups[group_name]
            if group['packages'] == 0:
                log.info("Deleting old group %s as it has no datasets.", group['name'])
                context = {'model': model, 'session': model.Session, 'user': user['name']}
                logic.get_action('group_delete')(context, {'id': group['id']})

            else:
                log.warn("Not deleting old publisher: %s because it has datasets associated with it.", group_name)

    def _update_translations(self, publishers, groups_title_lookup, context):
        translations = []
        for publisher in publishers:
            if publisher.lang_code == "en":
                continue
            if not publisher.title:
                continue

            if publisher.name not in groups_title_lookup:
                log.warn("No english version of %s [%s].  Skipping", publisher.title, publisher.name)
                continue

            translations.append({
                "term": groups_title_lookup[publisher.name],
                "term_translation": publisher.title,
                "lang_code": publisher.lang_code
            })

        logic.get_action('term_translation_update_many')(
            context, {'data': translations}
        )

    def _create_vocab(self, context, vocab_name):
        try:
            log.info('Creating vocabulary "%s"' % vocab_name)
            vocab = logic.get_action('vocabulary_create')(
                context, {'name': vocab_name}
            )
        except logic.ValidationError, ve:
            # ignore errors about the vocab already existing
            # if it's a different error, reraise
            if not 'name is already in use' in str(ve.error_dict):
                raise ve
            log.info('Vocabulary "%s" already exists' % vocab_name)
            vocab = logic.get_action('vocabulary_show')(
                context, {'id': vocab_name}
            )
        return vocab

    def _delete_vocab(self, vocab_name):
        log.info('Deleting vocabulary "%s"' % vocab_name)
        context = {'model': model, 'session': model.Session, 'user': self.user_name}
        vocab = logic.get_action('vocabulary_show')(context, {'id': vocab_name})
        for tag in vocab.get('tags'):
            logic.get_action('tag_delete')(context, {'id': tag['id']})
        logic.get_action('vocabulary_delete')(context, {'id': vocab['id']})

    def create_vocab_from_file(self, vocab_name, file_name):
        context = {'model': model, 'session': model.Session,
                   'user': self.user_name}
        vocab = self._create_vocab(context, vocab_name)

        with open(file_name) as json_file:
            full_json = json.loads(json_file.read())

        translations = []
        tag_schema = ckan.logic.schema.default_create_tag_schema()
        tag_schema['name'] = [unicode]

        user = logic.get_action('get_site_user')({'model': model, 'ignore_auth': True}, {})

        for item in full_json['results']['bindings']:
            if item["language"]["value"] == "en":
                context = {'model': model, 'session': model.Session, 'user': user['name'],
                           'schema': tag_schema}

                if item["label"]["value"] == "Multilingual Code" and vocab_name == forms.LANGUAGE_VOCAB_NAME:
                    continue

                term = item["term"]["value"]
                tag = {
                    'name': term,
                    'vocabulary_id': vocab['id']
                }
                try:
                    logic.get_action('tag_create')(context, tag)
                except logic.ValidationError, ve:
                    # ignore errors about the tag already belong to the vocab
                    # if it's a different error, reraise
                    if not 'already belongs to vocabulary' in str(ve.error_dict):
                        raise ve
                    log.info('Tag "%s" already belongs to vocab "%s"' %
                             (term, vocab_name))

        for item in full_json['results']['bindings']:
            term = item["term"]["value"]
            translation = item["label"]["value"]
            if translation == "Multilingual Code" and vocab_name == forms.LANGUAGE_VOCAB_NAME:
                continue
            if not translation:
                continue

            translations.append({"term": term,
                                "term_translation": translation,
                                "lang_code": item["language"]["value"]
                                })

        logic.get_action('term_translation_update_many')(
            context, {'data': translations}
        )

    def create_geo_vocab(self):
        file_name = os.path.dirname(os.path.abspath(__file__)) + '/../../data/po-countries.json'
        self.create_vocab_from_file(forms.GEO_VOCAB_NAME, file_name)

    def delete_geo_vocab(self):
        self._delete_vocab(forms.GEO_VOCAB_NAME)

    def create_dataset_type_vocab(self):
        file_name = os.path.dirname(os.path.abspath(__file__)) + '/../../data/odp-dataset-type.json'
        self.create_vocab_from_file(forms.DATASET_TYPE_VOCAB_NAME, file_name)

    def delete_dataset_type_vocab(self):
        self._delete_vocab(forms.DATASET_TYPE_VOCAB_NAME)

    def create_language_vocab(self):
        file_name = os.path.dirname(os.path.abspath(__file__)) + '/../../data/po-languages.json'
        self.create_vocab_from_file(forms.LANGUAGE_VOCAB_NAME, file_name)

    def delete_language_vocab(self):
        self._delete_vocab(forms.LANGUAGE_VOCAB_NAME)

    def create_status_vocab(self):
        file_name = os.path.dirname(os.path.abspath(__file__)) + '/../../data/odp-dataset-status.json'
        self.create_vocab_from_file(forms.STATUS_VOCAB_NAME, file_name)

    def delete_status_vocab(self):
        self._delete_vocab(forms.STATUS_VOCAB_NAME)

    def create_interop_vocab(self):
        file_name = os.path.dirname(os.path.abspath(__file__)) + '/../../data/odp-interoperability-level.json'
        self.create_vocab_from_file(forms.INTEROP_VOCAB_NAME, file_name)

    def delete_interop_vocab(self):
        self._delete_vocab(forms.INTEROP_VOCAB_NAME)

    def create_temporal_vocab(self):
        file_name = os.path.dirname(os.path.abspath(__file__)) + '/../../data/odp-temporal-granularity.json'
        self.create_vocab_from_file(forms.TEMPORAL_VOCAB_NAME, file_name)

    def delete_temporal_vocab(self):
        self._delete_vocab(forms.TEMPORAL_VOCAB_NAME)

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
        file_name = os.path.dirname(os.path.abspath(__file__)) + '/../../data/odp-vocabulary-translate.csv'
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

        logic.get_action('term_translation_update_many')(
            context, {'data': translations}
        )

    def create_all_vocabs(self):
        self.import_publishers()
        self.create_geo_vocab()
        self.create_dataset_type_vocab()
        self.create_language_vocab()
        self.create_status_vocab()
        self.create_interop_vocab()
        self.create_temporal_vocab()
        self.import_csv_translation()

    def delete_all_vocabs(self):
        log.warn('Not deleting publisher info (not yet implemented)')
        self.delete_geo_vocab()
        self.delete_dataset_type_vocab()
        self.delete_language_vocab()
        self.delete_status_vocab()
        self.delete_interop_vocab()
        self.delete_temporal_vocab()

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
