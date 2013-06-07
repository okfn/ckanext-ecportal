from setuptools import setup, find_packages

from ckanext.ecportal import __version__

setup(
    name='ckanext-ecportal',
    version=__version__,
    long_description='CKAN EC Portal Extension',
    classifiers=[],
    namespace_packages=['ckanext', 'ckanext.ecportal'],
    zip_safe=False,
    author='Open Knowledge Foundation',
    author_email='info@okfn.org',
    license='AGPL',
    url='http://ckan.org/',
    description='CKAN EC Portal extension',
    keywords='data packaging component tool server',
    install_requires=[],
    packages=find_packages(exclude=['ez_setup']),
    include_package_data=True,
    package_data={'ckan': ['i18n/*/LC_MESSAGES/*.mo']},
    entry_points='''
        [ckan.plugins]
        ecportal = ckanext.ecportal.plugin:ECPortalPlugin
        ecportal_form = ckanext.ecportal.forms:ECPortalDatasetForm
        ecportal_publisher_form = ckanext.ecportal.forms:ECPortalPublisherForm
        ecportal_controller = ckanext.ecportal.controllers:ECPortalDatasetController
        ecportal_multilingual_dataset = ckanext.ecportal.plugin:MulitlingualDataset

        [paste.paster_command]
        ecportal=ckanext.ecportal.commands:ECPortalCommand
    ''',
    test_suite='nose.collector'
)
