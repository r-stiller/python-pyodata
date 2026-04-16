"""Optional live smoke tests against public OData V3 reference services."""

import os

import pytest
import requests

import pyodata


PYODATA_RUN_REFERENCE_SERVICE_LIVE = 'PYODATA_RUN_REFERENCE_SERVICE_LIVE'
REFERENCE_ODATA_URL_ROOT = 'https://services.odata.org/V3/OData/OData.svc/'
REFERENCE_NORTHWIND_URL_ROOT = 'https://services.odata.org/V3/Northwind/Northwind.svc/'

pytestmark = pytest.mark.skipif(
    os.getenv(PYODATA_RUN_REFERENCE_SERVICE_LIVE) != '1',
    reason=f'Set {PYODATA_RUN_REFERENCE_SERVICE_LIVE}=1 to run live reference-service smoke tests.')


def test_live_reference_v3_odata_reads_open_type_spatial_named_stream_and_function():
    with requests.Session() as session:
        service = pyodata.Client(
            REFERENCE_ODATA_URL_ROOT,
            session,
            odata_version=pyodata.Client.ODATA_VERSION_3)

        category = service.entity_sets.Categories.get_entity(0, encode_path=False).execute()
        supplier = service.entity_sets.Suppliers.get_entity(0, encode_path=False).execute()
        stream_response = service.entity_sets.PersonDetails.get_entity(1, encode_path=False).named_stream('Photo').execute()
        products = service.functions.GetProductsByRating.parameter('rating', 5).execute()

    assert category.ID == 0
    assert category.Name == 'Food'
    assert supplier.Location['type'] == 'Point'
    assert stream_response.content == b'Test named stream data 3'
    assert products[0].Name == 'DVD Player'


def test_live_reference_v3_northwind_reads_entity_and_query():
    with requests.Session() as session:
        service = pyodata.Client(
            REFERENCE_NORTHWIND_URL_ROOT,
            session,
            odata_version=pyodata.Client.ODATA_VERSION_3)

        product = service.entity_sets.Products.get_entity(1, encode_path=False).execute()
        products = service.entity_sets.Products.get_entities().top(2).execute()

    assert product.ProductID == 1
    assert product.ProductName == 'Chai'
    assert [entity.ProductID for entity in products] == [1, 2]
