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



def update_rdf( source_rdf, name ):
    """
    Checks that the source_rdf is valid and whether it contains the local
    triples we want, and if not adds them.  The adding of the triples will
    depend on the namespaces already present.
    """
    rdf = source_rdf[1:-1].replace('\\"', '"') # cleanup json junk
    try:
        root = lxml.etree.fromstring( rdf )
    except lxml.etree.XMLSyntaxError:
        return ""

    local_namespaces = {
        "http://purl.org/dc/terms/#" : "dct",
        "http://www.w3.org/1999/02/22-rdf-syntax-ns" : "rdf",
        "http://www.w3.org/ns/dcat#" : "dcat"
    }
    local_ns = dict( (v,k) for k,v in local_namespaces.iteritems() )
    for k,v in root.nsmap.iteritems():
        if v in local_namespaces:
            local_namespaces[v] = k

    modified_text = datetime.datetime.now().date().isoformat()
    origin_url    = ""

    node = root.xpath('//Dataset', namespaces=local_namespaces)
    if len(node) == 1:
        original_url = node[0].get("http://www.w3.org/1999/02/22-rdf-syntax-ns}about",
                                   default="")

    # Pull out URL from
    # <dcat:Dataset rdf:about="{0}">

    # We can add elements like this knowing it will look up the uri in the
    # root nsmap before this element's map.
    local_url = g.site_url + h.url_for(controller='package', action='read',
                                       id=name)

    # Outer dcat:record
    record = lxml.etree.Element("{http://www.w3.org/ns/dcat#}record",
                                 nsmap=local_ns)
    record.set("{http://www.w3.org/1999/02/22-rdf-syntax-ns}parseType",
                "Resource")

    # dcat:accessUrl inside the record
    accessUrl = lxml.etree.Element("{http://www.w3.org/ns/dcat#}accessUrl",
                                    nsmap=local_ns)
    accessUrl.set("{http://www.w3.org/1999/02/22-rdf-syntax-ns}datatype",
                  "http://www.w3.org/2001/XMLSchema#anyURI")
    accessUrl.text = local_url


    modified = lxml.etree.Element("{http://purl.org/dc/terms/#}modified",
                                    nsmap=local_ns)
    modified.set("{http://www.w3.org/1999/02/22-rdf-syntax-ns}datatype",
                  "http://www.w3.org/2001/XMLSchema#dateTime")
    modified.text = modified_text

    issued = lxml.etree.Element("{http://purl.org/dc/terms/#}issued",
                                    nsmap=local_ns)
    issued.set("{http://www.w3.org/1999/02/22-rdf-syntax-ns}datatype",
                  "http://www.w3.org/2001/XMLSchema#dateTime")
    issued.text = modified_text

    record.append(accessUrl)
    record.append(modified)
    record.append(issued)
    root.append( record )

    return origin_url, lxml.etree.tostring( root )
