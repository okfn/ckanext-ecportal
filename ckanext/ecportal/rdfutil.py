import os
import sys
import datetime
import lxml.etree
from pylons import g
import ckan.lib.helpers as h
try:
    import json
except:
    import simplejson as json

import logging
log = logging.getLogger(__name__)


def update_rdf( source_rdf, name ):
    """
    Checks that the source_rdf is valid and whether it contains the local
    triples we want, and if not adds them.  The adding of the triples will
    depend on the namespaces already present.
    """
    rdf = source_rdf.replace('\\"', '"').strip() # cleanup json junk
    try:
        root = lxml.etree.fromstring( rdf )
    except lxml.etree.XMLSyntaxError, xmlerr:
        log.error( xmlerr)
        return "", ""

    local_namespaces = {
        "http://purl.org/dc/terms/#" : "dct",
        "http://www.w3.org/1999/02/22-rdf-syntax-ns#" : "rdf",
        "http://www.w3.org/ns/dcat#" : "dcat",
        "http://ec.europa.eu/open-data/ontologies/ec-odp#" : "ecodp"
    }
    local_ns = dict( (v,k) for k,v in local_namespaces.iteritems() )
    for k,v in root.nsmap.iteritems():
        if v in local_namespaces:
            local_namespaces[v] = k

    modified_text = datetime.datetime.now().date().isoformat()
    origin_url    = ""

    new_root = None
    node = root.xpath('//dcat:Dataset', namespaces=local_ns)
    if len(node) == 1:
        new_root = node[0]
        origin_url = new_root.get("http://www.w3.org/1999/02/22-rdf-syntax-ns#}about",
                                   default="")
    else:
        node = root.xpath('/rdf:RDF/rdf:Description', namespaces=local_ns)
        for n in node:
            # Find the one with a rdf:type rdf:resource="http://www.w3.org/ns/dcat#Dataset"
            test = n.xpath("rdf:type[@rdf:resource='http://www.w3.org/ns/dcat#Dataset']", namespaces=local_ns)
            if len(test) > 0:
                new_root = n
                origin_url = new_root.get("{http://www.w3.org/1999/02/22-rdf-syntax-ns#}about")
                break



    # We can add elements like this knowing it will look up the uri in the
    # root nsmap before this element's map.
    local_url = g.site_url + h.url_for(controller='package', action='read',
                                       id=name)

    # Outer dcat:record
    record = lxml.etree.Element("{http://www.w3.org/ns/dcat#}record",
                                 nsmap=local_ns)
    record.set("{http://www.w3.org/1999/02/22-rdf-syntax-ns#}parseType",
                "Resource")

    desc = lxml.etree.Element("{http://www.w3.org/1999/02/22-rdf-syntax-ns#}Description",
                                 nsmap=local_ns)
    desc.set("{http://www.w3.org/1999/02/22-rdf-syntax-ns#}about", origin_url)

    innerdesc = lxml.etree.Element("{http://www.w3.org/1999/02/22-rdf-syntax-ns#}Description",
                                 nsmap=local_ns)
    innerdesc.set("{http://www.w3.org/1999/02/22-rdf-syntax-ns#}about", local_url)

    # dcat:accessUrl inside the record
    accessUrl = lxml.etree.Element("{http://ec.europa.eu/open-data/ontologies/ec-odp#}accessUrl",
                                    nsmap=local_ns)
    accessUrl.set("{http://www.w3.org/1999/02/22-rdf-syntax-ns#}datatype",
                  "http://www.w3.org/2001/XMLSchema#anyURI")
    accessUrl.text = local_url


    modified = lxml.etree.Element("{http://purl.org/dc/terms/#}modified",
                                    nsmap=local_ns)
    modified.set("{http://www.w3.org/1999/02/22-rdf-syntax-ns#}datatype",
                  "http://www.w3.org/2001/XMLSchema#dateTime")
    modified.text = modified_text

    issued = lxml.etree.Element("{http://purl.org/dc/terms/#}issued",
                                    nsmap=local_ns)
    issued.set("{http://www.w3.org/1999/02/22-rdf-syntax-ns#}datatype",
                  "http://www.w3.org/2001/XMLSchema#dateTime")
    issued.text = modified_text

    innerdesc.append(accessUrl)
    innerdesc.append(modified)
    innerdesc.append(issued)
    record.append(innerdesc)
    desc.append(record)
    root.append( desc )

    return origin_url, lxml.etree.tostring( root )
