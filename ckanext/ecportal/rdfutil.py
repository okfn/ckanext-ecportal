import os
import sys
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
        "http://www.w3.org/2002/07/owl" : "owl",
        "http://www.w3.org/1999/02/22-rdf-syntax-ns" : "rdf"
    }
    local_ns = dict( (v,k) for k,v in local_namespaces.iteritems() )
    for k,v in root.nsmap.iteritems():
        if v in local_namespaces:
            # TODO: Compare URI's not strings
            local_namespaces[v] = k

    # We can add elements like this knowing it will look up the uri in the root nsmap before
    # this element's map.
    nodes = root.xpath('//owl:sameAs',
                        namespaces={"owl": local_ns['owl']})
    if not len(nodes):
        local_url = g.site_url + h.url_for(controller='package', action='read', id=name)
        sameAs = lxml.etree.Element("{http://www.w3.org/2002/07/owl}sameAs", nsmap=local_ns)
        sameAs.set("{http://www.w3.org/1999/02/22-rdf-syntax-ns}resource", local_url)
        root.append( sameAs )

    return lxml.etree.tostring( root )
