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

        # get search results with package_show so that they go through
        # schema validators/converters
        validated_results = []

        for result in search_results['results']:
            data = {'id': result['id']}
            pkg = p.toolkit.get_action('package_show')(context, data)
            validated_results.append(pkg)

        search_results['results'] = validated_results

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
        return pkg_dict

    def before_view(self, pkg_dict):
        return pkg_dict
