""" Test the pyodata integration with aiohttp client, based on asyncio

https://docs.aiohttp.org/en/stable/
"""
import aiohttp
from aiohttp import web
import pytest

import pyodata
import pyodata.v2.service
import pyodata.v3.service
from pyodata import Client
from pyodata.exceptions import PyODataException, HttpError
from pyodata.v2.model import ParserError, PolicyWarning, PolicyFatal, PolicyIgnore, Config
from tests.conftest import contents_of_fixtures_file

SERVICE_URL = ''


@pytest.fixture
def metadata_v3():
    return contents_of_fixtures_file('metadata_v3.xml')


@pytest.mark.asyncio
async def test_invalid_odata_version():
    """Check handling of request for invalid OData version implementation"""

    with pytest.raises(PyODataException) as e_info:
        async with aiohttp.ClientSession() as client:
            await Client.build_async_client(SERVICE_URL, client, 'INVALID VERSION')

    assert str(e_info.value).startswith('No implementation for selected odata version')

@pytest.mark.asyncio
async def test_create_client_for_local_metadata(metadata):
    """Check client creation for valid use case with local metadata"""

    async with aiohttp.ClientSession() as client:
        service_client = await Client.build_async_client(SERVICE_URL, client, metadata=metadata)

        assert isinstance(service_client, pyodata.v2.service.Service)
        assert service_client.schema.is_valid == True

        assert len(service_client.schema.entity_sets) != 0


@pytest.mark.asyncio
async def test_create_v3_client_for_local_metadata(metadata_v3):
    """Check V3 async client creation for valid use case with local metadata."""

    async with aiohttp.ClientSession() as client:
        service_client = await Client.build_async_client(
            SERVICE_URL,
            client,
            odata_version=Client.ODATA_VERSION_3,
            metadata=metadata_v3)

        assert isinstance(service_client, pyodata.v3.service.Service)
        assert service_client.schema.entity_type('Document').name == 'Document'


@pytest.mark.asyncio
def generate_metadata_response(headers=None, body=None, status=200):

    async def metadata_response(request):
        return web.Response(status=status, headers=headers, body=body)

    return metadata_response


@pytest.mark.parametrize("content_type", ['application/xml', 'application/atom+xml', 'text/xml'])
@pytest.mark.asyncio
async def test_create_service_application(aiohttp_client, metadata, content_type):
    """Check client creation for valid MIME types"""

    app = web.Application()
    app.router.add_get('/$metadata', generate_metadata_response(headers={'content-type': content_type}, body=metadata))
    client = await aiohttp_client(app)

    service_client = await Client.build_async_client(SERVICE_URL, client)

    assert isinstance(service_client, pyodata.v2.service.Service)

    # one more test for '/' terminated url

    service_client = await Client.build_async_client(SERVICE_URL + '/', client)

    assert isinstance(service_client, pyodata.v2.service.Service)
    assert service_client.schema.is_valid


@pytest.mark.asyncio
async def test_create_v3_service_application(aiohttp_client, metadata_v3):
    """Check V3 async client creation when metadata is fetched over aiohttp."""

    app = web.Application()
    app.router.add_get('/$metadata',
                       generate_metadata_response(headers={'content-type': 'application/xml'}, body=metadata_v3))
    client = await aiohttp_client(app)

    service_client = await Client.build_async_client(SERVICE_URL, client, odata_version=Client.ODATA_VERSION_3)

    assert isinstance(service_client, pyodata.v3.service.Service)
    assert service_client.schema.entity_type('Document').name == 'Document'


@pytest.mark.asyncio
async def test_v3_async_get_entity_uses_verbose_json_headers(aiohttp_client, metadata_v3):
    """Check a representative V3 request path and header policy for aiohttp."""

    seen_headers = {}

    async def document_response(request):
        seen_headers['Accept'] = request.headers.get('Accept')
        seen_headers['MaxDataServiceVersion'] = request.headers.get('MaxDataServiceVersion')
        return web.Response(
            status=200,
            headers={'content-type': 'application/json'},
            body=b'{"d": {"Id": 1, "Title": "Spec draft"}}')

    app = web.Application()
    app.router.add_get('/Documents(1)', document_response)
    client = await aiohttp_client(app)

    service_client = await Client.build_async_client(
        SERVICE_URL,
        client,
        odata_version=Client.ODATA_VERSION_3,
        metadata=metadata_v3)

    entity = await service_client.entity_sets.Documents.get_entity(1, encode_path=False).async_execute()

    assert entity.Id == 1
    assert entity.Title == 'Spec draft'
    assert seen_headers == {
        'Accept': 'application/json;odata=verbose',
        'MaxDataServiceVersion': '3.0',
    }


@pytest.mark.asyncio
async def test_metadata_not_reachable(aiohttp_client):
    """Check handling of not reachable service metadata"""

    app = web.Application()
    app.router.add_get('/$metadata', generate_metadata_response(headers={'content-type': 'text/html'}, status=404))
    client = await aiohttp_client(app)

    with pytest.raises(HttpError) as e_info:
        await Client.build_async_client(SERVICE_URL, client)

    assert str(e_info.value).startswith('Metadata request failed')

@pytest.mark.asyncio
async def test_metadata_saml_not_authorized(aiohttp_client):
    """Check handling of not SAML / OAuth unauthorized response"""

    app = web.Application()
    app.router.add_get('/$metadata', generate_metadata_response(headers={'content-type': 'text/html; charset=utf-8'}))
    client = await aiohttp_client(app)

    with pytest.raises(HttpError) as e_info:
        await Client.build_async_client(SERVICE_URL, client)

    assert str(e_info.value).startswith('Metadata request did not return XML, MIME type:')


@pytest.mark.asyncio
async def test_client_custom_configuration(aiohttp_client, metadata):
    """Check client creation for custom configuration"""

    namespaces = {
        'edmx': "customEdmxUrl.com",
        'edm': 'customEdmUrl.com'
    }

    custom_config = Config(
        xml_namespaces=namespaces,
        default_error_policy=PolicyFatal(),
        custom_error_policies={
            ParserError.ANNOTATION: PolicyWarning(),
            ParserError.ASSOCIATION: PolicyIgnore()
        })

    app = web.Application()
    app.router.add_get('/$metadata',
                       generate_metadata_response(headers={'content-type': 'application/xml'}, body=metadata))
    client = await aiohttp_client(app)

    with pytest.raises(PyODataException) as e_info:
        await Client.build_async_client(SERVICE_URL, client, config=custom_config, namespaces=namespaces)

    assert str(e_info.value) == 'You cannot pass namespaces and config at the same time'

    with pytest.warns(DeprecationWarning,match='Passing namespaces directly is deprecated. Use class Config instead'):
        service = await Client.build_async_client(SERVICE_URL, client, namespaces=namespaces)

    assert isinstance(service, pyodata.v2.service.Service)
    assert service.schema.config.namespaces == namespaces

    service = await Client.build_async_client(SERVICE_URL, client, config=custom_config)

    assert isinstance(service, pyodata.v2.service.Service)
    assert service.schema.config == custom_config
