import ckan.lib.navl.validators as navl_validators
import ckan.logic.schema as core_schema
import ckan.logic.validators as core_validators


def default_user_schema():
    schema = core_schema.default_user_schema()

    # username can be uppercase
    schema['name'] = [navl_validators.not_empty,
                      core_validators.user_name_validator,
                      unicode]

    # email is not required
    schema['email'] = [navl_validators.default(u''),
                       unicode]

    return schema


def default_update_user_schema():
    schema = default_user_schema()

    schema['name'] = [navl_validators.ignore_missing,
                      core_validators.user_name_validator,
                      unicode]

    schema['password'] = [core_validators.user_password_validator,
                          navl_validators.ignore_missing,
                          unicode]

    return schema
