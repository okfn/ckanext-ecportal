import json
import ckan.model as model
import ckan.plugins as p
import ckan.lib.navl.dictization_functions
import forms

_validate = ckan.lib.navl.dictization_functions.validate
_f = forms.ECPortalDatasetForm()


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
        # remove vocab tags from facets
        free_tags = {}

        for tag, count in search_results['facets'].get('tags', {}).iteritems():
            # as we don't specify a vocab here, only tags with no vocab
            # will be found
            if model.Tag.get(tag):
                free_tags[tag] = count

        if free_tags:
            search_results['facets']['tags'] = free_tags

        if search_results['search_facets'].get('tags'):
            items = search_results['search_facets']['tags']['items']
            items = filter(lambda x: x.get('name') in free_tags.keys(), items)
            search_results['search_facets']['tags']['items'] = items

        return search_results

    def before_index(self, pkg_dict):
        context = {'model': model,
                   'session': model.Session,
                   'user': u''}
        schema = _f.db_to_form_schema({})

        validated_pkg, errors = _validate(json.loads(pkg_dict['data_dict']),
                                          schema,
                                          context=context)
        pkg_dict['data_dict'] = json.dumps(validated_pkg)

        return pkg_dict

    def before_view(self, pkg_dict):
        return pkg_dict
