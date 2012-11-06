========================
EC ODP API Documentation
========================

This document outlines the API offered up by CKAN.  For the most part, the API
is the standard CKAN action API, but it has been customised for the ECODP
project.  Both the standard API and its customisations are outlined in this
document.

.. _action-api:

CKAN Standard Action API
~~~~~~~~~~~~~~~~~~~~~~~~

Overview
--------

The Action API is a powerful RPC-style way of accessing CKAN data. Its
intention is to have access to all the core logic in ckan. It calls exactly the
same functions that are used internally which all the other CKAN interfaces
(Web interface / Model API) go through. Therefore it provides the full gamut of
read and write operations, with all possible parameters.

A client supplies parameters to the Action API via a JSON dictionary of a POST
request, and returns results, help information and any error diagnostics in a
JSON dictionary too.

URL
===

The basic URL for the Action API is::

 /open-data/data/api/3/action/{logic_action}

Examples::

 /open-data/data/api/3/action/package_list
 /open-data/data/api/3/action/package_show
 /open-data/data/api/3/action/user_create

Parameters
==========

All actions accept POST request including parameters in a JSON dictionary. If
there are no parameters required, then an empty dictionary is still required
(or you get a 400 error).

Examples::

 curl http://odp.tenforce.com/open-data/data/api/3/action/package_list -d '{}'
 curl http://odp.tenforce.com/open-data/data/api/3/action/package_show -d '{"id": "fd788e57-dce4-481c-832d-497235bf9f78"}'

Actions
=======

.. automodule:: ckan.logic.action.get
   :members: site_read, package_list, current_package_list_with_resources, member_list, group_list, group_list_authz, licence_list, tag_list, user_list, package_show, resource_show, group_show, group_package_show, tag_show, user_show, package_search, resource_search, tag_search, term_translation_show, status_show, vocabulary_list, vocabulary_show

.. automodule:: ckan.logic.action.create
   :members: package_create, resource_create, member_create, group_create, user_create, vocabulary_create, tag_create

.. automodule:: ckan.logic.action.update
   :members: resource_update, package_update, group_update, user_update, term_translation_update, term_translation_update_many, vocabulary_update

.. automodule:: ckan.logic.action.delete
   :members: package_delete, member_delete, group_delete, vocabulary_delete, tag_delete

Responses
=========

The response is wholly contained in the form of a JSON dictionary. Here is the basic format of a successful request::

 {"help": "Creates a package", "success": true, "result": ...}

And here is one that incurred an error::

 {"help": "Creates a package", "success": false, "error": {"message": "Access denied", "__type": "Authorization Error"}}

Where:

* ``help`` is the 'doc string' (or ``null``)
* ``success`` is ``true`` or ``false`` depending on whether the request was successful. The response is always status 200, so it is important to check this value.
* ``result`` is the main payload that results from a successful request. This might be a list of the domain object names or a dictionary with the particular domain object.
* ``error`` is supplied if the request was not successful and provides a message and __type. See the section on errors.

Errors
======

The message types include:
  * Authorization Error - an API key is required for this operation, and the corresponding user needs the correct credentials
  * Validation Error - the object supplied does not meet with the standards described in the schema.
  * (TBC) JSON Error - the request could not be parsed / decoded as JSON format, according to the Content-Type (default is ``application/x-www-form-urlencoded;utf-8``).

Examples
========

::

 $ curl http://ckan.net/open-data/data/api/3/action/package_show -d '{"id": "fd788e57-dce4-481c-832d-497235bf9f78"}'
 {"help": null, "success": true, "result": <dataset-representation>}

Status Codes
~~~~~~~~~~~~

The Action API aims to return status ``200 OK``, whether there are errors or
not. The response body contains the `success` field indicating whether an error
occurred or not. When ``"success": false`` then you will receive details of the
error in the `error` field. For example requesting a dataset that doesn't
exist::

 curl http://odp.tenforce.com/open-data/data/api/3/action/package_show -d '{"id": "unknown_id"}'

gives::

 {"help": null, "success": false, "error": {"message": "Not found", "__type": "Not Found Error"}}

Alternatively, requests to the Action API that have major formatting problems
may result in a 409, 400, or 500 error (in order of increasing severity).

