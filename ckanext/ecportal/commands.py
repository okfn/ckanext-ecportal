import os
import re
import json
import urllib
import lxml.etree
from ckan import model
from ckan.logic import get_action, NotFound, ValidationError
from ckan.lib.cli import CkanCommand
import forms

import logging
log = logging.getLogger()


class InvalidDateFormat(Exception):
    pass


class ECPortalCommand(CkanCommand):
    '''
    Commands:

        paster ecportal import-data <data> <user> -c <config>
        paster ecportal import-publishers <translations> <structure> -c <config>
        paster ecportal create-geo-vocab <ntu translations> <ntu types> -c <config>
        paster ecportal delete-geo-vocab -c <config>

    Where:
        <data> = path to XML file (format of the Eurostat bulk import metadata file)
        <user> = perform actions as this CKAN user (name)
        <translations> = path to translations.json
        <structure> = path to structure.json
        <ntu translations> = path to ntu_translations.json
        <ntu types> = path to ntu_types.json
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

        user = get_action('get_site_user')(
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
            if not len(self.args) == 3:
                print ECPortalCommand.__doc__
                return

            translations_path = self.args[1]
            types_path = self.args[2]

            if os.path.isfile(translations_path) and \
               os.path.isfile(types_path):
                with open(translations_path, 'r') as tr:
                    with open(types_path, 'r') as ty:
                        self.create_geo_vocab(json.loads(tr.read()),
                                              json.loads(ty.read()))
            else:
                log.error('Could not open files %s and %s' %
                    (translations_path, types_path)
                )

        elif cmd == 'delete-geo-vocab':
            self.delete_geo_vocab()

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
            get_action('package_create')(context, dataset)
        except ValidationError, ve:
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
            get_action('term_translation_update_many')(
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
                    get_action('term_translation_update_many')(
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

    def _import_dataset_json(self, path):
        '''
        Import JSON datasets from the proof-of-concept site.
        '''
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

            log.info('Adding dataset: %s' % dataset['name'])
            user = get_action('get_site_user')({'model': model, 'ignore_auth': True}, {})
            context = {'model': model, 'session': model.Session, 'user': user['name']}
            get_action('package_create')(context, dataset)

    def import_publishers(self, translations, structure):
        '''
        Create publisher groups based on translations and structure JSON objects.
        '''
        # get group names and title translations
        log.info('Reading group structure and names/translations')
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
        log.info('Creating CKAN group objects')
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
        log.info('Updating group hierarchy')
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
        log.info('Updating French translations')
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

    def _get_countries(self, translations):
        '''
        Return a list of the JSON dicts in the translations dict that refer
        to countries.
        '''
        bindings = translations['results']['bindings']
        type1 = 'http://publications.europa.eu/resource/authority/ntu/type/1'
        return [b for b in bindings if b['t']['value'] == type1]

    def _get_country_codes(self, countries):
        codes = set([u'EU27'])
        for c in countries:
            codes.add(c['s']['value'].split('/')[-1].upper())
        return list(codes)

    def _get_name_translations(self, country_code, countries):
        '''
        Return all translations of the full name of country_code.
        '''
        name_translations = {}
        for c in countries:
            if c['s']['value'].split('/')[-1].upper() == country_code:
                lang = c['lang']['value'].split('/')[-1].lower()
                name_translations[lang] = c['f']['value']
        return name_translations

    def _lang_code_convert(self, lang):
        '''
        Convert 3 letter language codes (ISO 639-2) from URIs in ntu_translations.json
        to 2 letter language codes (ISO 639-1).
        '''
        language_codes = {
            'eng': u'en',
            'fra': u'fr',
            'deu': u'de',
            'spa': u'es',
            'ita': u'it',
            'roh': u'rm',
            'dan': u'da',
            'ron': u'ro',
            'por': u'pt',
            'gle': u'ga',
            'pol': u'pl',
            'nld': u'nl',
            'cat': u'ca',
            'mkd': u'mk',
            'ell': u'el',
            'hrv': u'hr',
            'swe': u'sv',
            'ukr': u'uk',
            'lit': u'lt',
            'fin': u'fi',
            'tur': u'tr',
            'eus': u'eu',
            'hun': u'hu',
            'isl': u'is',
            'sqi': u'sq',
            'est': u'et',
            'ces': u'cs',
            'fao': u'fo',
            'bul': u'bg',
            'rus': u'ru',
            'lav': u'lv',
            'nor': u'no',
            'bel': u'be',
            'slv': u'sl',
            'bos': u'bs',
            'glg': u'gl',
            'srp': u'sr',
            'mlt': u'mt',
            'slk': u'sk',
            'ltz': u'lb',
        }
        return language_codes[lang]

    def create_geo_vocab(self, ntu_translations, ntu_types):
        context = {'model': model, 'session': model.Session,
                   'user': self.user_name}
        try:
            log.info('Creating vocabulary "%s"' % forms.GEO_VOCAB_NAME)
            vocab = get_action('vocabulary_create')(
                context, {'name': forms.GEO_VOCAB_NAME}
            )
        except ValidationError, ve:
            # ignore errors about the vocab already existing
            # if it's a different error, reraise
            if not 'name is already in use' in str(ve.error_dict):
                raise ve
            log.info('Vocabulary "%s" already exists' % forms.GEO_VOCAB_NAME)
            vocab = get_action('vocabulary_show')(
                context, {'id': forms.GEO_VOCAB_NAME}
            )

        countries = self._get_countries(ntu_translations)
        term_translations = []

        for country_code in self._get_country_codes(countries):
            # add tag
            try:
                log.info('Adding tag "%s" to vocab "%s"' %
                         (country_code, forms.GEO_VOCAB_NAME))
                tag_data = {'name': country_code, 'vocabulary_id': vocab['id']}
                get_action('tag_create')(context, tag_data)
            except ValidationError, ve:
                # ignore errors about the tag already belong to the vocab
                # if it's a different error, reraise
                if not 'already belongs to vocabulary' in str(ve.error_dict):
                    raise ve
                log.info('Tag "%s" already belongs to vocab "%s"' %
                         (country_code, forms.GEO_VOCAB_NAME))

            # no translations for 'EU27'
            if country_code == 'EU27':
                continue

            # get all translations of the country name
            name_translations = self._get_name_translations(country_code, countries)
            for name in name_translations:
                try:
                    term_translations.append({
                        'term': country_code,
                        'term_translation': name_translations[name],
                        'lang_code': self._lang_code_convert(name)
                    })
                except KeyError:
                    log.info('No language code found for lang "%s"' % name)

        # add additional translations from ntu_types dict
        type_translations = self._get_countries(ntu_types)
        # en_tt is just 'Country' for now, but this is here in case we want
        # to import additional types and translations later
        en_tt = [tt['label']['value'] for tt in type_translations
                 if tt['label']['xml:lang'] == 'en'][0]
        for tt in type_translations:
            if not tt['label']['xml:lang'] == 'en':
                term_translations.append({
                    'term': unicode(en_tt),
                    'term_translation': unicode(tt['label']['value']),
                    'lang_code': unicode(tt['label']['xml:lang'])
                })

        # save translations
        log.info('Adding translations')
        get_action('term_translation_update_many')(
            context, {'data': term_translations}
        )

    def delete_geo_vocab(self):
        log.info('Deleting vocabulary "%s"' % forms.GEO_VOCAB_NAME)

        context = {'model': model, 'session': model.Session, 'user': self.user_name}
        vocab = get_action('vocabulary_show')(context, {'id': forms.GEO_VOCAB_NAME})
        for tag in vocab.get('tags'):
            get_action('tag_delete')(context, {'id': tag['id']})
        get_action('vocabulary_delete')(context, {'id': vocab['id']})
