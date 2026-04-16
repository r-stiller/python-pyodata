# OData V3 Reference Service Fixtures

These files are captured fixtures for offline V3 regression tests.

Capture date: `2026-04-16`

Sources:

- `odata_service_metadata.xml`
  - `https://services.odata.org/V3/OData/OData.svc/$metadata`
- `odata_service_readwrite_metadata.xml`
  - `https://services.odata.org/V3/(S(readwrite))/OData/OData.svc/$metadata`
- `northwind_metadata.xml`
  - `https://services.odata.org/V3/Northwind/Northwind.svc/$metadata`
- `odata_product_1.json`
  - `https://services.odata.org/V3/OData/OData.svc/Products(1)`
- `odata_category_0.json`
  - `https://services.odata.org/V3/OData/OData.svc/Categories(0)`
- `odata_supplier_0.json`
  - `https://services.odata.org/V3/OData/OData.svc/Suppliers(0)`
- `odata_get_products_by_rating_rating_5.json`
  - `https://services.odata.org/V3/OData/OData.svc/GetProductsByRating?rating=5`
- `odata_persondetail_1_photo.bin`
  - `https://services.odata.org/V3/OData/OData.svc/PersonDetails(1)/Photo`
- `northwind_product_1.json`
  - `https://services.odata.org/V3/Northwind/Northwind.svc/Products(1)`
- `northwind_products_top_2.json`
  - `https://services.odata.org/V3/Northwind/Northwind.svc/Products?$top=2`

Notes:

- These fixtures are intentionally checked in so default CI does not depend on outbound network access.
- Live smoke coverage lives separately behind `PYODATA_RUN_REFERENCE_SERVICE_LIVE=1`.
- The read-write service is referenced only via the canonical `(S(readwrite))` URL. Tests must not hardcode redirected session-specific URLs.
