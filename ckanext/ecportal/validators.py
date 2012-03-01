import re
from pylons.i18n import _
from ckan.lib.field_types import DateType, DateConvertError
from ckan.lib.navl.dictization_functions import Invalid, missing, unflatten
from ckan.logic import get_action, NotFound

# parse_timedate function is similar to the one in ckan.lib.field_types.DateType
# changes:
# - doesn't accept a time value
# - different message passed to DateConvertError exception 
class ECPortalDateType(DateType):
    @classmethod
    def parse_timedate(cls, timedate_str, format_type):
        '''Takes a timedate and returns a dictionary of the fields.
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
                readable_formats = [] # analogous to the regexps, but human readable
                year_re = '(?P<%s>\d{2,4})'
                month_re = '(?P<%s>\w+)'
                two_digit_decimal_re = '(?P<%s>\d{1,2})'
                date_field_re = {'year':year_re % 'year',
                                 'month':month_re % 'month',
                                 'day':two_digit_decimal_re % 'day'}
                date_fields = list(cls.date_fields_order[format_type_])
                for how_specific in ('day', 'month', 'year'):
                    date_sep_re = '[%s]' % cls.parsing_separators['date']
                    date_sep_readable = cls.default_separators[format_type_]['date']
                    date_field_regexps = [date_field_re[field] for field in date_fields]
                    date_field_readable = [cls.datetime_fields[field][cls.datetime_fields_indexes['format_code']] for field in date_fields]
                    date_re = date_sep_re.join(date_field_regexps)
                    date_readable = date_sep_readable.join(date_field_readable)
                    finished_regexps.append(date_re)
                    readable_formats.append(date_readable)
                    date_fields.remove(how_specific)
                full_date_re = finished_regexps[0]
                full_date_readable = readable_formats[0]
                cls.matchers[format_type_] = [re.compile('^%s$' % regexp) for regexp in finished_regexps]
                cls.readable_formats[format_type_] = readable_formats
        for index, matcher in enumerate(cls.matchers[format_type]):
            match = matcher.match(timedate_str)
            if match:
                timedate_dict = match.groupdict()
                timedate_dict = cls.int_timedate(timedate_dict)
                timedate_dict['readable_format'] = cls.readable_formats[format_type][index]
                return timedate_dict
        else:
            acceptable_formats = ', '.join(["'%s'" % format_ for format_ in cls.readable_formats[format_type]])
            raise DateConvertError("Unknown date format: '%s'. Acceptable formats: %s" % (timedate_str, acceptable_formats))

def ecportal_date_to_db(value, context):
    if not value:
        return
    try:
        timedate_dict = ECPortalDateType.parse_timedate(value, 'db')
    except DateConvertError, e:
        # Cannot parse
        raise Invalid(str(e))
    try:
        value = ECPortalDateType.format(timedate_dict, 'db')
    except DateConvertError, e:
        # Values out of range
        raise Invalid(str(e))
    return value

def use_other(key, data, errors, context):
    other_key = key[-1] + '-other'
    other_value = data.get((other_key,), '').strip()
    if other_value:
        data[key] = other_value

def extract_other(option_list):
    def other(key, data, errors, context):
        value = data[key]
        if value in dict(option_list).keys():
            return
        elif value is missing:
            data[key] = ''
            return
        else:
            data[key] = 'other'
            other_key = key[-1] + '-other'
            data[(other_key,)] = value
    return other
            
def convert_to_extras(key, data, errors, context):
    # get current number of extras
    extra_number = 0
    for k in data.keys():
        if k[0] == 'extras':
            extra_number = max(extra_number, k[1] + 1)
    # add a new extra
    data[('extras', extra_number, 'key')] = key[0]
    data[('extras', extra_number, 'value')] = data[key]

def duplicate_extras_key(key, data, errors, context):
    '''Test for a custom extra key being a duplicate of an existing (schema) key.'''
    unflattened = unflatten(data)
    extras = unflattened.get('extras', [])
    extras_keys = []
    for extra in extras:
        if not extra.get('deleted'):
            extras_keys.append(extra['key'])

    for extra_key in set(extras_keys):
        extras_keys.remove(extra_key)

    if extras_keys:
        for extra_key in extras_keys:
            errors[(extra_key,)] = [_('Duplicate key for "%s" given') % extra_key]

def publisher_exists(publisher_name, context):
    """Raises Invalid if the given publisher_name does not exist in the model given
    in the context, otherwise returns the given publisher_name.

    """
    try:
        get_action('group_show')(context, {'id': publisher_name})
    except NotFound:
        raise Invalid('%s: %s' % (_('Publisher not found'), publisher_name))
    return publisher_name
