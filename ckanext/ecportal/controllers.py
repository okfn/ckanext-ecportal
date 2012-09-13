try:
    import json
except ImportError:
    import simplejson as json

import ckan.model as model
import ckan.plugins as p
import ckan.lib.navl.dictization_functions
import forms

_validate = ckan.lib.navl.dictization_functions.validate
_f = forms.ECPortalDatasetForm()


def _vocabularies(tag_name):
    '''
    Return a list containing the names of each vocabulary that
    contains the tag tag_name.

    Returns an empty list if tag_name does not belong to any vocabulary.

    If no such tag exists, throws a ckan.plugins.toolkit.ObjectNotFound
    exception.
    '''
    query = model.Session.query(model.tag.Tag.name, model.vocabulary.Vocabulary.name)\
        .filter(model.tag.Tag.name == tag_name).filter(model.tag.Tag.vocabulary_id == model.vocabulary.Vocabulary.id)

    return [t[1] for t in query]


class ECPortalDatasetController(p.SingletonPlugin):
    p.implements(p.IPackageController)

    def read(self, entity):
        pass

    def create(self, entity):
        pass

    def edit(self, entity):
        pass

    def authz_add_role(self, object_role):
        pass

    def authz_remove_role(self, object_role):
        pass

    def delete(self, entity):
        pass

    def before_search(self, search_params):
        return search_params

    def after_search(self, search_results, search_params):
        return search_results

    def before_index(self, pkg_dict):
        # save a validated version of the package dict in the search index
        context = {'model': model,
                   'session': model.Session,
                   'user': u''}
        schema = _f.db_to_form_schema({})

        validated_pkg, errors = _validate(json.loads(pkg_dict['data_dict']),
                                          schema,
                                          context=context)
        pkg_dict['data_dict'] = json.dumps(validated_pkg)

        # remove vocab tags from 'tags' list and add them as vocab_<tag name>
        # so that they can be used in facets
        free_tags = []

        for tag in pkg_dict.get('tags'):
            vocabs = _vocabularies(tag)
            if vocabs:
                for vocab in vocabs:
                    key = u'vocab_%s' % vocab
                    if key in pkg_dict:
                        pkg_dict[key].append(tag)
                    else:
                        pkg_dict[key] = [tag]
            else:
                free_tags.append(tag)

        pkg_dict['tags'] = free_tags

        return pkg_dict

    def before_view(self, pkg_dict):
        return pkg_dict
