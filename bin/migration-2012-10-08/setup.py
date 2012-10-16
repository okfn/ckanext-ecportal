from setuptools import setup

setup(
    name = "ecodp-migrate",
    version = "0.1",
    author = "Ian Murray",
    author_email = "ian.murray@okfn.org",
    description = "Quick migration script for copying datasets between CKAN instances",
    scripts=['migrate.py'],
)
