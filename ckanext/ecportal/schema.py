import ckan.lib.navl.validators as navl_validators
import ckan.logic.validators as core_validators

# changes from core:
# - username can be uppercase
# - email is not required


def default_user_schema(schema):
    schema.update({
        'name': [navl_validators.not_empty,
                 core_validators.user_name_validator,
                 unicode],
        'email': [navl_validators.default(u''),
                  unicode]
    })
    return schema


def default_update_user_schema(schema):
    schema.update({
        'name': [navl_validators.ignore_missing,
                 core_validators.user_name_validator,
                 unicode]
    })
    return schema
