import ckan.plugins as p


class ECPortalPlugin(p.SingletonPlugin):
    p.implements(p.IConfigurable)
    p.implements(p.IConfigurer)

    def configure(self, config):
        self.site_url = config.get('ckan.site_url')

    def update_config(self, config):
        p.toolkit.add_template_directory(config, 'templates')
        p.toolkit.add_public_directory(config, 'public')

        # ECPortal should use group auth
        config['ckan.auth.profile'] = 'publisher'
