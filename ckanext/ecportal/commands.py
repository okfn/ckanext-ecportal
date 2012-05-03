import os
import sys
import re
import json
import urllib
import lxml.etree
import ckan
import ckan.model as model
import ckan.logic as logic
import ckan.lib.cli as cli
import requests
import forms


import logging
log = logging.getLogger()


class InvalidDateFormat(Exception):
    pass


class ECPortalCommand(cli.CkanCommand):
    '''
    Commands:

        paster ecportal import-data <data> <user> -c <config>
        paster ecportal import-publishers -c <config>
        paster ecportal export-datasets <folder> -c <config>

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

    Where:
        <data> = path to XML file (format of the Eurostat bulk import metadata file)
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

        file_name = os.path.dirname(os.path.abspath(__file__)) + '/../../data/po-corporate-bodies.json'
        with open(file_name) as json_file:
            full_json = json.loads(json_file.read())

        ### get out english 

        groups_title_lookup = {}
        translations = []

        log.info('Creating CKAN group objects')
        user = logic.get_action('get_site_user')({'model': model, 'ignore_auth': True}, {})

        for item in full_json['results']['bindings']:
            if item["language"]["value"] == "en":
                context = {'model': model, 'session': model.Session, 'user': user['name']}
                short_term = item["term"]["value"].split('/')[-1].lower()
                label = item["label"]["value"]
                if not label:
                    label = short_term
                groups_title_lookup[short_term] = label
                group = {
                    'name': short_term,
                    'title': item["label"]["value"],
                    'type': u'organization'
                }
                logic.get_action('group_create')(context, group)

        for item in full_json['results']['bindings']:
            if item["language"]["value"] == "en":
                continue
            short_term = item["term"]["value"].split('/')[-1].lower()
            translation = item["label"]["value"]
            if not translation:
                continue
            translations.append({"term": groups_title_lookup[short_term],
                                "term_translation": translation,
                                "lang_code": item["language"]["value"]
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

    def create_all_vocabs(self):
        self.import_publishers()
        self.create_geo_vocab()
        self.create_dataset_type_vocab()
        self.create_language_vocab()
        self.create_status_vocab()
        self.create_interop_vocab()
        self.create_temporal_vocab()

    def delete_all_vocabs(self):
        log.warn('Not deleting publisher info (not yet implemented)')
        self.delete_geo_vocab()
        self.delete_dataset_type_vocab()
        self.delete_language_vocab()
        self.delete_status_vocab()
        self.delete_interop_vocab()
        self.delete_temporal_vocab()
