import os
from genshi.input import HTML
from genshi.filters import Transformer
from ckan.plugins import implements, SingletonPlugin, IConfigurable,\
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
    implements(IConfigurable)
    implements(IConfigurer)
    # implements(IGenshiStreamFilter)

    def configure(self, config):
        self.site_url = config.get('ckan.site_url')

    def update_config(self, config):
        configure_template_directory(config, 'templates')
        configure_public_directory(config, 'public')

        # ECPortal should use group auth
        config['ckan.auth.profile'] = 'publisher'

    # def filter(self, stream):
    #     from pylons import request
    #     routes = request.environ.get('pylons.routes_dict')

    #     if routes and routes.get('controller') == 'package' and \
    #         routes.get('action') in ['new', 'edit']:
    #             data = {'site_url': self.site_url}
    #             stream = stream | Transformer('head').append(HTML(html.CSS % data))

    #     return stream

