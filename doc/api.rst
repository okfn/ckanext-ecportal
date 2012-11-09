==========
CKAN's API
==========

This document outlines CKAN's action API.  For the most part, the API is the
standard CKAN action API, but it has been customised for the ECODP project.
Where there are differences, the customised behaviour is documented here.

.. _action-api:

Action API
~~~~~~~~~~

This section describes the parts of the CKAN API that are relevant to the ECODP
project, and is intended as a resource for operations/developers.  For an
overview of the whole of the API on offer, see the `Other Exposed APIs`_
section.

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

ECODP Actions
=============

This is a list of actions relevant or particular to the ECODP peoject.  There
are other actions exposed throught Action API, which are documented in the
`Action API -- the remaining exposed actions`_ section.

.. automodule:: ckanext.ecportal.plugin
   :members: group_list, group_update, purge_revision_history

.. automodule:: ckan.logic.action.get
   :members: site_read, package_list, current_package_list_with_resources, member_list, group_list_authz, licence_list, tag_list, user_list, package_show, resource_show, group_show, group_package_show, tag_show, user_show, package_search, resource_search, tag_search, term_translation_show, status_show, vocabulary_list, vocabulary_show

.. automodule:: ckan.logic.action.create
   :members: package_create, resource_create, member_create, group_create, user_create, vocabulary_create, tag_create

.. automodule:: ckan.logic.action.update
   :members: resource_update, package_update, user_update, term_translation_update, term_translation_update_many, vocabulary_update

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

Status Codes
------------

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

Other Exposed APIs
~~~~~~~~~~~~~~~~~~

The *action API* described above is version 3 of CKAN's API.  Versions 1 and 2
are also, by default, enabled.  Further to this, the above section is not an
exhaustive list of the actions available through the Action API.  This section
will give an overview of the remaining actions exposed through the Action API.

Action API -- the remaining exposed actions
-------------------------------------------

See `here <http://docs.ckan.org/en/ckan-1.8/apiv3.html#module-ckan.logic.action.get>`_
for the exhaustive list of actions exposed through the Action API.

.. note:: The link above is the standard CKAN docs for the Action API, and does
          not take ECODP customizations into account.  However, any differences are
          already documented in this document.

Outlined below is a synopsis of the other actions exposed by CKAN:

Read-only actions
=================

There are a set of actions related to **reading** parts of the CKAN system.
They have no side-effects on the system, and can be safely exposed via ``GET``
requests if necessary.

.. note:: Currently, the action API is only exposed through ``POST`` requests.
          But it is possible to expose the read-only actions via ``GET``
          requests **in addition** to the usual ``POST`` method.  This would
          require a code-change: namely, backporting a feature of CKAN 1.8 to
          the version of CKAN used by ecportal (1.7.1).

.. note:: If operating two CKAN instances side-by-side (a read-only http site,
          and a read-write https site) then we would prevent all non-``GET``
          requests on the read-only site, but still be able to leave these
          actions available via ``GET`` requests.

For notes on what information is made available, see the `Security`_ section.

Reference
.........

.. automodule:: ckan.logic.action.get
   :members:
   :undoc-members:

Actions with side-effects
=========================

The rest of the actions all have some sort of side-effect on the system.  That
is, *creating*, *updating* or *deleting*.

All updates, creating and deleting via *actions* need to go through CKAN's
authorization layer.  This means that if the action requires a user to belong
to a particular group, then that is checked.  It also means if it's a CKAN
admin task, then only CKAN admins can successfully run the action.

Reference
.........

.. automodule:: ckan.logic.action.create
   :members:
   :undoc-members:

.. automodule:: ckan.logic.action.delete
   :members:
   :undoc-members:

.. automodule:: ckan.logic.action.update
   :members:
   :undoc-members:



Versions 1 & 2
--------------

See `here <http://docs.ckan.org/en/ckan-1.7.1/api-v2.html#versions-1-2>`_ for
full details of the other APIs.  Outlined below are the important features...

Versions 1 & 2 are rooted at the following urls:

* ``/api``   (version 1)
* ``/api/1``
* ``/api/2``

The following resources are available thorugh the API:

* dataset index `eg <http://odp.tenforce.com/open-data/data/api/1/rest/dataset>`_
* dataset `eg <http://odp.tenforce.com/open-data/data/api/1/rest/dataset/cRxWsFFLnZLQSYHriioxtA>`_
* group index `eg <http://odp.tenforce.com/open-data/data/api/1/rest/group>`_   [times-out on odp.tenforce.com]
* group `eg <http://odp.tenforce.com/open-data/data/api/1/rest/group/17fb6891-6cc0-4626-992f-c9df802a28cb>`_
* tag index `eg <http://odp.tenforce.com/open-data/data/api/1/rest/tag>`_
* tag `eg <http://odp.tenforce.com/open-data/data/api/1/rest/tag/account>`_
* various forms of dataset relationships. `eg <http://odp.tenforce.com/open-data/data/api/1/rest/dataset/cRxWsFFLnZLQSYHriioxtA/relationships>`_, [Not relevant to ECODP]
* dataset revisions `eg <http://odp.tenforce.com/open-data/data/api/1/rest/dataset/cRxWsFFLnZLQSYHriioxtA/revisions>`_
* revision list `eg <http://odp.tenforce.com/open-data/data/api/1/rest/revision>`_
* revision `eg <http://odp.tenforce.com/open-data/data/api/1/rest/revision/84b526d3-b235-4e0d-b26e-02ef51d0f03b>`_  
* license index `eg <http://odp.tenforce.com/open-data/data/api/1/rest/licenses>`_

As you would expect with a RESTful API:

* ``GET``-ing any of the above resources will return the representation as json.
* ``PUT``-ing to some (*) of the resources above will update the resource.
* ``POST``-ing to some (*) of the resources above will create a new resource.
* ``DELETE``-ing to some (*) of the resources above will delete the resource.

.. note:: The following resources are updatable (ie respond to one of PUT, POST or DELETE):

            * dataset
            * group
            * tag
            * dataset relationships

When viewing, creating, updating and deleting resources, **calls to the RESTful
API are mapped to actions (as used in the action API).**  This means that all
calls to the REST API go through CKAN's action layer.  This is important
because the action layer centralizes `authorization`_.  The following actions are
used in the REST API:

* Creation

  * group_create_rest
  * package_create_rest
  * rating_create
  * related_create
  * package_relationship_create_rest

* Deletion

  * group_delete
  * package_delete
  * related_delete
  * package_relationship_delete_rest

* Updating

  * package_update_rest
  * group_update_rest
  * package_relationship_update_rest

* List/Index

  * revision_list
  * group_list
  * package_list
  * tag_list
  * related_list
  * licence_list
  * package_relationships_list
  * package_revision_list
  * package_activity_list
  * group_activity_list
  * user_activity_list
  * activity_detail_list

* Get/Show

  * revision_show
  * group_show_rest
  * tag_show_rest
  * related_show
  * package_show_rest
  * package_relationships_list

Each action above has an authorization rule attached to it, which determines
who can perform them.  More details of this are in the `authorization`_
section.

Search API
----------

See `here <http://docs.ckan.org/en/ckan-1.7.1/api-v2.html#search-api>`_ for
full details of CKAN's search API.

The search API is a read-only API which exposes search over *datasets*,
*resources* and *revisions*.

Authorization
~~~~~~~~~~~~~

CKAN is architectured in such a way that all interfaces to the system, be it
the http API(s), the web interface or paster commands (*) all access the system
through the **action layer**.  The **action layer** is a list of *actions*,
such as ``package_update``, each of which has an authorization function
attached to it.  As such, any customization of the authorization will affect
the authorization at the Web interface level as well the API.

.. note:: (*) CKAN hasn't always been architectured this way, and there are
          some places in the paster commands that don't go through the action
          layer.  The corollory of this is there are a few potential places in
          the paster interface where the authorization and validation of
          actions diverge.  This however is not generally considered a security
          concern as the paster interface requires access to the machine
          running CKAN, and always assumes admin rights.

Out of the box, CKAN's publisher authorization layer behaves as one would expect:

* Group editors and admins can publish datasets only through their Group (publisher).
* Non-group members are unable to view datasets private to that Group.
* Group admins have the rights to manage users of a Group.

The ECODP project has **further customizations** to the authorization layer:

* ``group_create`` : Only CKAN admins can create new Groups (publishers).
* ``package_update`` : Imported datasets are only updateable through the API.
* ``purge_revision_history`` : Only CKAN administrators can run this action.
* ``user_create`` : Only CKAN administrators can create new users.

Just to emphasize the point, due to the way that CKAN is architectured, the
customization of those 4 authorization functions affects the web interface as
well as any exposure through the API (versions 1,2 and 3).

Security
~~~~~~~~

By default CKAN does not expose information it would regard as compromising
security, but it is acknowledged that different CKAN instances may have
different needs.  The following is a outline of the information that would
ordinarily be readable on a CKAN instance:

* dataset information
  
  * the list of packages available on the system
  * the meta-data attached to the dataset (title, license, name etc)
  * the name of the publisher it belongs to
  * source rdf (in the case of imported datasets)
  * resource information: urls of linked-to resources etc.
  * old revisions of the dataset.

* group information

  * group information: name, description etc.
  * members of the group (inlcuding username and capacity of membership)
  * datasets published through the group

* user information
  
  * username and fullname
  * datasets they've authored
  * activity list (ie edits/creations/deletions performed)
  * takes authentication into account:

    * a ckan administrator will see, in addition to the above: email address
      and apikey
    * a user requesting themselves will see, in addition to the above: email
      address and apikey

.. note:: Controlling what information is made available is not customizable,
          but it can be achieved.  For example, say an aspect of the User
          information is deemed as not necessary to display, then since User
          information appears not only in ``user_show`` or ``user_list``, but
          also embedded within other results, eg. ``group_show``; then this
          change would require a degree of work.  Saying that, it's quite
          centralized in the codebase, so it shouldn't be a case of changing
          the user information for **every** action: changing it in one place
          would be sufficient.

In addition to the above, there are a few features which are not used.  Since
they are not used, any related read-only actions will return empty or
meaningless results.

