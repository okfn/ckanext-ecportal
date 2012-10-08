A quick migration script required by TF to migrate some manually entered datasets from odp to prod.

# Installation

Requirements are found in pip-requirements.txt.  They can be installed by running:

    !bash
    pip install -r pip-requirements.txt

# Running

The script is runnable from any machine with access to the APIs of the source and target CKAN instances.  You will need to provide your api key for writing to the target machine.

Run `python migrate.py --help` for help with the command:

    Migrate CKAN datasets
    
    Usage:
        migrate.py from <source> to <target> [options] <dataset-ids>...
    
    Options:
        -h --help                     Show this screen
        --dry-run                     Don't perform writes on the target machine.
        --source-api-key=<api-key>    API key on the source instance.
        --target-api-key=<api-key>    API key on the target instance.
        --overwrite                   Overwrite existing datasets on the target.
   
