import itertools
import re
import types
from pylons.i18n import _
import ckan.logic as logic
import ckan.lib.field_types as field_types
import ckan.lib.navl.dictization_functions as df
import ckan.logic.validators as val
import ckan.model as model
import rdfutil

try:
    import json
except ImportError:
    import simplejson as json

name_match = re.compile('[a-zA-Z0-9_\-]*$')


# parse_timedate function is similar to the one in
# ckan.lib.field_types.DateType
#
# changes:
# - doesn't accept a time value
# - different message passed to DateConvertError exception
class ECPortalDateType(field_types.DateType):
    @classmethod
    def parse_timedate(cls, timedate_str, format_type):
        '''
        Takes a timedate and returns a dictionary of the fields.
        * Little validation is done.
        * If it can't understand the layout it raises DateConvertError
        '''
        assert format_type in cls.format_types
        if not hasattr(cls, 'matchers'):
            # build up a list of re matches for the different
            # acceptable ways of expressing the time and date
            cls.matchers = {}
            cls.readable_formats = {}

            for format_type_ in cls.format_types:
                finished_regexps = []
                readable_formats = []
                year_re = '(?P<%s>\d{2,4})'
                month_re = '(?P<%s>\w+)'
                two_digit_decimal_re = '(?P<%s>\d{1,2})'
                date_field_re = {'year': year_re % 'year',
                                 'month': month_re % 'month',
                                 'day': two_digit_decimal_re % 'day'}
                date_fields = list(cls.date_fields_order[format_type_])

                for how_specific in ('day', 'month', 'year'):
                    date_sep_re = '[%s]' % cls.parsing_separators['date']
                    date_sep_readable = \
                        cls.default_separators[format_type_]['date']
                    date_field_regexps = \
                        [date_field_re[field] for field in date_fields]
                    date_field_readable = \
                        [cls.datetime_fields[field]
                         [cls.datetime_fields_indexes['format_code']]
                         for field in date_fields]
                    date_re = date_sep_re.join(date_field_regexps)
                    date_readable = date_sep_readable.join(date_field_readable)
                    finished_regexps.append(date_re)
                    readable_formats.append(date_readable)
                    date_fields.remove(how_specific)

                cls.matchers[format_type_] = [re.compile('^%s$' % regexp)
                                              for regexp in finished_regexps]
                cls.readable_formats[format_type_] = readable_formats

        for index, matcher in enumerate(cls.matchers[format_type]):
            match = matcher.match(timedate_str)
            if match:
                timedate_dict = match.groupdict()
                timedate_dict = cls.int_timedate(timedate_dict)
                timedate_dict['readable_format'] = \
                    cls.readable_formats[format_type][index]
                return timedate_dict
        else:
            acceptable_formats = ', '.join(
                ["'%s'" % format_
                 for format_ in cls.readable_formats[format_type]]
            )
            raise field_types.DateConvertError(
                "Unknown date format: '%s'. Acceptable formats: %s" % (
                    timedate_str, acceptable_formats
                )
            )


def ecportal_date_to_db(value, context):
    if not value:
        return
    try:
        timedate_dict = ECPortalDateType.parse_timedate(value, 'db')
    except field_types.DateConvertError, e:
        # Cannot parse
        raise df.Invalid(str(e))
    try:
        value = ECPortalDateType.format(timedate_dict, 'db')
    except field_types.DateConvertError, e:
        # Values out of range
        raise df.Invalid(str(e))
    return value


def valid_xsd_datetime(key, data, errors, context):
    '''
    If viewing RDF, this validator will update output of date fields so that
    they meet the XSD:dateTime spec.

    See: books.xmlschemata.org/relaxng/ch19-77049.html

    Output must be: YYYY-MM-DDThh-mm-ss

    This data is not all available as a day is the lowest level of
    granularity that will be deemed valid by CKAN. Days and months may also
    be omitted.

    As time is not availble, hh-mm-ss will be set to 00:00:00.
    Missing months and days will be set to 01.
    '''
    timedate_dict = ECPortalDateType.parse_timedate(data[key], 'db')
    year = str(timedate_dict.get('year'))
    month = str(timedate_dict.get('month', 1)).zfill(2)
    day = str(timedate_dict.get('day', 1)).zfill(2)
    data[key] = '{0}-{1}-{2}T{3}'.format(year, month, day, '00:00:00')


def convert_to_extras(key, data, errors, context):
    # get current number of extras
    extra_number = 0
    for k in data.keys():
        if k[0] == 'extras':
            extra_number = max(extra_number, k[1] + 1)
    # add a new extra
    data[('extras', extra_number, 'key')] = key[0]
    if not context.get('extras_as_string'):
        data[('extras', extra_number, 'value')] = json.dumps(data[key])
    else:
        data[('extras', extra_number, 'value')] = data[key]


def convert_from_extras(key, data, errors, context):
    for k in data.keys():
        if k[0] == 'extras' and k[-1] == 'key' and data[k] == key[-1]:
            # add to top level
            data[key] = data[('extras', k[1], 'value')]
            # remove from extras
            for to_remove in data.keys():
                if to_remove[0] == 'extras' and to_remove[1] == k[1]:
                    del data[to_remove]


def convert_to_groups(field):
    '''
    Add data[key] as the first group name in data.
    '''
    def convert(key, data, errors, context):
        data[('groups', 0, field)] = data[key]
    return convert


def convert_from_groups(field):
    '''
    Set data[key] to the first group name in data (if any exist).
    '''
    def convert(key, data, errors, context):
        data[key] = data.get(('groups', 0, field), None)
    return convert


def convert_resource_type(key, data, errors, context):
    '''
       convert type to resource_type
    '''
    new_key = key[:-1] + ('resource_type',)
    data[new_key] = data[key]
    data.pop(key)


def duplicate_extras_key(key, data, errors, context):
    '''
    Test for a custom extra key being a duplicate of an existing (schema) key.
    '''
    unflattened = df.unflatten(data)
    extras = unflattened.get('extras', [])
    extras_keys = []
    for extra in extras:
        if not extra.get('deleted'):
            extras_keys.append(extra['key'])

    for extra_key in set(extras_keys):
        extras_keys.remove(extra_key)

    if extras_keys:
        for extra_key in extras_keys:
            errors[(extra_key,)] = [_('Duplicate key for "%s" given')
                                    % extra_key]


def group_name_unchanged(key, data, errors, context):
    '''Ensures that a group's name cannot be changed once set.'''
    model = context['model']
    group = context.get('group')
    new_group_name = data[key]

    if not group:
        group_id = data.get(key[:-1] + ('id',))
        if group_id and group_id is not df.missing:
            group = model.Group.get(group_id)

    if group and group.name != new_group_name:
        errors[key].append(_('Group name cannot be changed'))


def publisher_exists(publisher_name, context):
    '''
    Raises Invalid if the given publisher_name does not exist in the model
    given in the context, otherwise returns the given publisher_name.
    '''
    try:
        logic.get_action('group_show')(context, {'id': publisher_name})
    except logic.NotFound:
        raise df.Invalid('%s: %s' % (_('Publisher not found'), publisher_name))
    return publisher_name


def keyword_string_convert(key, data, errors, context):
    '''
    Takes a list of tags that is a comma-separated string (in data[key])
    and parses tag names. These are added to the data dict, enumerated. They
    are also validated.
    '''
    if isinstance(data[key], basestring):
        tags = [tag.strip()
                for tag in data[key].split(',')
                if tag.strip()]
    else:
        tags = data[key]

    current_index = max([int(k[1]) for k in data.keys()
                         if len(k) == 3 and k[0] == 'keywords'] + [-1])

    for num, tag in zip(itertools.count(current_index + 1), tags):
        data[('keywords', num, 'name')] = tag

    for tag in tags:
        val.tag_length_validator(tag, context)
        val.tag_name_validator(tag, context)


def rename(old, new):
    '''
    Rename a schema field from old to new.
    Should be used in __after.
    '''
    def rename_field(key, data, errors, context):
        index = max([int(k[1]) for k in data.keys()
                     if len(k) == 3 and k[0] == new] + [-1])

        for field_name in data.keys():
            if field_name[0] == old:
                new_field_name = list(field_name)
                new_field_name[0] = new

                if len(new_field_name) > 1:
                    new_field_name[1] = int(new_field_name[1]) + index + 1

                data[tuple(new_field_name)] = data[field_name]
                data.pop(field_name)

    return rename_field


def update_rdf(key, data, errors, context):
    '''
    Determines if there is any XML in the rdf field and ensures that it
    matches expectations. This data will be returned on requests for .rdf
    As this data is saved we first need to add our fields.
    '''
    rdf = data.get(key, '')
    name = data.get((u'name',), '')
    if not rdf:
        return

    origin_url, xml = rdfutil.update_rdf(rdf, name)
    data[key] = xml

    if origin_url:
        data[('url',)] = origin_url


def ecportal_name_validator(val, context):
    '''
    Names must be alphanumeric characters or the symbols '-' and '_'.
    Unlike CKAN core, names in the EC Portal can contain capital letters.
    '''
    if val in ['new', 'edit', 'search']:
        raise df.Invalid(_('That name cannot be used'))
    if len(val) < 2:
        raise df.Invalid(_('Name must be at least %s characters long') % 2)
    if len(val) > model.PACKAGE_NAME_MAX_LENGTH:
        raise df.Invalid(_('Name must be a maximum of %i characters long') %
                         model.PACKAGE_NAME_MAX_LENGTH)
    if not name_match.match(val):
        raise df.Invalid(_('Url must be alphanumeric '
                           '(ascii) characters and these symbols: -_'))
    return val


def requires_field(field_name):
    '''
    If data[key] exists, check that the top-level field field_name is also
    present (and not empty).
    '''
    def check(key, data, errors, context):
        if data[key] and not data[(field_name,)]:
            raise df.Invalid(_('Additional field required: %s' % field_name))
    return check


def member_of_vocab(vocab):
    ''' Returns a validator that checks values are members of the given vocab.

    Unlike the `convert_to_tag` function found in `ckan.logic.converters`,
    this does not convert the values into tags.  It's only purpose is
    validation, not conversion.
    '''
    def validator(key, data, errors, context):
        tags = data.get(key)
        if not tags:
            return
        if isinstance(tags, basestring):
            tags = [tags]

        v = model.Vocabulary.get(vocab)
        if not v:
            raise df.Invalid(_('Tag vocabulary "%s" does not exist') % vocab)
        context['vocabulary'] = v

        for tag in tags:
            val.tag_in_vocabulary_validator(tag, context)
        return tags
    return validator


_cc_by_re = re.compile(r'http://creativecommons.org/licenses/by/2.5/[^/]+/?',
                       re.IGNORECASE)
_cc_by_sa_re = re.compile(r'http://creativecommons.org/licenses/by-sa/3.0/[^/]+/?',
                          re.IGNORECASE)


def map_licenses(val, context):
    ''' Maps fixed set of license_ids to others.

    Specifically, it maps licenses with a country code, as specified in the
    Creative Commons RDF Specification, to cc-by and cc-by-sa licenses.

    http://creativecommons.org/licenses/by/2.5/{countrycode}/
    maps to
    http://www.opendefinition.org/licenses/cc-by

    http://creativecommons.org/licenses/by-sa/3.0/{countrycode}/
    maps to
    http://www.opendefinition.org/licenses/cc-by-sa
    '''
    if not val:
        # val could be an empty list, which throws an error in re.match
        return val
    if re.match(_cc_by_re, val):
        return 'http://www.opendefinition.org/licenses/cc-by'
    if re.match(_cc_by_sa_re, val):
        return 'http://www.opendefinition.org/licenses/cc-by-sa'
    return val


def reduce_list(val, context):
    ''' Converts a list to the value at the head of the list.

    If the value isn't a list, then it is left alone.
    '''
    if isinstance(val, types.ListType) and len(val) > 0:
        return val[0]
    return val
