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


def user_new_form_schema():
    schema = default_user_schema()

    schema['password1'] = [unicode,
                           core_validators.user_both_passwords_entered,
                           core_validators.user_password_validator,
                           core_validators.user_passwords_match]

    schema['password2'] = [unicode]

    return schema


def user_edit_form_schema():
    schema = default_user_schema()

    ## Same modifications to the schema as made in core.
    schema['password'] = [navl_validators.ignore_missing]

    schema['password1'] = [navl_validators.ignore_missing,
                           unicode,
                           core_validators.user_password_validator,
                           core_validators.user_passwords_match]

    schema['password2'] = [navl_validators.ignore_missing, unicode]

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
