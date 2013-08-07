import logging
import datetime
import lxml.etree
import pylons.config
import ckan.lib.helpers as h
import ckanext.ecportal.helpers as ecportal_helpers
try:
    import json
except:
    import simplejson as json

log = logging.getLogger(__name__)
Element = lxml.etree.Element


def update_rdf(source_rdf, name):
    '''
    Checks that the source_rdf is valid and whether it contains the local
    triples we want, and if not adds them.  The adding of the triples will
    depend on the namespaces already present.
    '''
    rdf = source_rdf.replace('\\"', '"').strip()  # cleanup json junk
    try:
        root = lxml.etree.fromstring(rdf)
    except lxml.etree.XMLSyntaxError, xmlerr:
        log.error(xmlerr)
        return '', ''

    local_namespaces = {
        'http://purl.org/dc/terms/#': 'dct',
        'http://www.w3.org/1999/02/22-rdf-syntax-ns#': 'rdf',
        'http://www.w3.org/ns/dcat#': 'dcat',
        'http://ec.europa.eu/open-data/ontologies/ec-odp#': 'ecodp',
        'http://xmlns.com/foaf/0.1/#': 'foaf'
    }

    local_ns = dict((v, k) for k, v in local_namespaces.iteritems())
    for k, v in root.nsmap.iteritems():
        if v in local_namespaces:
            local_namespaces[v] = k

    modified_text = datetime.datetime.now().date().isoformat()

    origin_url = ''
    new_root = None
    node = root.xpath('//dcat:Dataset', namespaces=local_ns)
    if len(node) == 1:
        new_root = node[0]
        origin_url = new_root.get(
            '{http://www.w3.org/1999/02/22-rdf-syntax-ns#}about',
            default=''
        )
    else:
        node = root.xpath('/rdf:RDF/rdf:Description', namespaces=local_ns)
        for n in node:
            # Find rdf:type rdf:resource="http://www.w3.org/ns/dcat#Dataset"
            test = n.xpath(
                "rdf:type[@rdf:resource='http://www.w3.org/ns/dcat#Dataset']",
                namespaces=local_ns
            )
            if len(test) > 0:
                new_root = n
                origin_url = new_root.get(
                    '{http://www.w3.org/1999/02/22-rdf-syntax-ns#}about'
                )
                break

    root_path = h.url_for('/', qualified=False)
    site_url = pylons.config['ckan.site_url'].rstrip('/') + root_path
    local_url = site_url.rstrip('/') + '/dataset/{0}'.format(name)

    catalog = Element('{http://www.w3.org/ns/dcat#}Catalog',
                       nsmap=local_ns)
    catalog.set('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}about', ecportal_helpers.catalog_url())
    record = Element('{http://www.w3.org/ns/dcat#}record',
                     nsmap=local_ns)
    catalog_record = Element('{http://www.w3.org/ns/dcat#}CatalogRecord',
                             nsmap=local_ns)
    catalog_record.set('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}about', local_url)

    primary_topic = Element(
        '{http://xmlns.com/foaf/0.1/#}primaryTopic',
        nsmap=local_ns
    )
    primary_topic.text = origin_url

    modified = Element('{http://purl.org/dc/terms/#}modified',
                       nsmap=local_ns)
    modified.text = modified_text

    issued = Element('{http://purl.org/dc/terms/#}issued',
                     nsmap=local_ns)
    issued.text = modified_text

    catalog_record.append(primary_topic)
    catalog_record.append(modified)
    catalog_record.append(issued)
    record.append(catalog_record)
    catalog.append(record)
    root.append(catalog)
    return origin_url, lxml.etree.tostring(root)
