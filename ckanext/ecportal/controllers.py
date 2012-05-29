import ckan.model as model
import ckan.plugins as p


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
        context = {'model': model, 'user': p.toolkit.c.user}
        validated_results = []

        for result in search_results['results']:
            data = {'id': result['id']}
            pkg = p.toolkit.get_action('package_show')(context, data)
            validated_results.append(pkg)

        search_results['results'] = validated_results
        return search_results

    def before_index(self, pkg_dict):
        return pkg_dict

    def before_view(self, pkg_dict):
        return pkg_dict
