from pylons.i18n import _
from ckan.lib.field_types import DateType, DateConvertError
from ckan.lib.navl.dictization_functions import Invalid, missing, unflatten
from field_types import GeoCoverageType

def ecportal_date_to_db(value, context):
    if not value:
        return
    try:
        timedate_dict = DateType.parse_timedate(value, 'db')
    except DateConvertError, e:
        # Cannot parse
        raise Invalid(str(e))
    try:
        value = DateType.format(timedate_dict, 'db')
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
            
def convert_geographic_to_db(value, context):
    if isinstance(value, list):
        regions = value
    elif value:
        regions = [value]
    else:
        regions = []
    return GeoCoverageType.get_instance().form_to_db(regions)

def convert_geographic_to_form(value, context):
    return GeoCoverageType.get_instance().db_to_form(value)

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
    '''Hardcode errors dict key for nicer messages'''
    unflattened = unflatten(data)
    extras = unflattened.get('extras', [])
    extras_keys = []
    for extra in extras:
        if not extra.get('deleted'):
            extras_keys.append(extra['key'])

    for extra_key in set(extras_keys):
        extras_keys.remove(extra_key)
    if extras_keys:
        errors['duplicate_extras_key'].append(_('Duplicate key "%s"') % extras_keys[0])

