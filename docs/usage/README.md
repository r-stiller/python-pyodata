The User Guide
--------------

The examples in this guide default to OData V2 unless a section says
otherwise. To use the current OData V3 implementation, pass
``odata_version=3`` when creating the client. The initial V3 milestone is
explicitly scoped; it defaults to Verbose JSON and also supports opt-in JSON
Light via ``pyodata.v3.model.Config(json_format='light', json_metadata=...)``,
using the standard V3 ``Accept: application/json;odata=light`` negotiation.

* [Initialization](initialization.rst)
* [Querying](querying.rst)
* [Creating](creating.rst)
* [Updating](updating.rst)  
* [Deleting](deleting.rst)
* [Function Imports](function_imports.rst)
* [Metadata](metadata.rst)
* [Advanced](advanced.rst)
* [URLs](urls.rst)
