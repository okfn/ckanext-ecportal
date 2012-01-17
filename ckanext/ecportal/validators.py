from ckan.lib.field_types import DateType, DateConvertError
from ckan.lib.navl.dictization_functions import Invalid
from ckan.lib.navl.dictization_functions import missing
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

