import os
from genshi.input import HTML
from genshi.filters import Transformer
from ckan.plugins import implements, SingletonPlugin, IRoutes, IConfigurable,\
    IConfigurer, IGenshiStreamFilter
import ckanext.ecportal
import html

from logging import getLogger
log = getLogger(__name__)

def configure_template_directory(config, relative_path):
    configure_served_directory(config, relative_path, 'extra_template_paths')

def configure_public_directory(config, relative_path):
    configure_served_directory(config, relative_path, 'extra_public_paths')

def configure_served_directory(config, relative_path, config_var):
    'Configure serving of public/template directories.'
    assert config_var in ('extra_template_paths', 'extra_public_paths')
    this_dir = os.path.dirname(ckanext.ecportal.__file__)
    absolute_path = os.path.join(this_dir, relative_path)
    if absolute_path not in config.get(config_var, ''):
        if config.get(config_var):
            config[config_var] += ',' + absolute_path
        else:
            config[config_var] = absolute_path

class ECPortalPlugin(SingletonPlugin):
    implements(IRoutes)
    implements(IConfigurable)
    implements(IConfigurer)
    implements(IGenshiStreamFilter)

    def before_map(self, map):
        map.connect('/dataset/new', controller='ckanext.ecportal.controller:ECPortalController', action='new')
        map.connect('/dataset/edit/{id}', controller='ckanext.ecportal.controller:ECPortalController', action='edit')
        return map

    def after_map(self, map):
        return map

    def configure(self, config):
        self.site_url = config.get('ckan.site_url')

    def update_config(self, config):
        configure_template_directory(config, 'templates')
        configure_public_directory(config, 'public')

    def filter(self, stream):
        from pylons import request
        routes = request.environ.get('pylons.routes_dict')

        # add javascript file to new dataset form so slug is generated correctly
        # add css file so description field is displayed
        if routes and 'ECPortalController' in routes.get('controller') and \
            routes.get('action') == 'new':
                data = {'site_url': self.site_url}
                stream = stream | Transformer('head').append(HTML(html.CSS % data))
                stream = stream | Transformer('body').append(HTML(html.JS % data))

        return stream

