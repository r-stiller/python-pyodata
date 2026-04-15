"""V3 service baseline tests."""

import pytest

import pyodata
import pyodata.v2.service
import pyodata.v3.service
from pyodata.exceptions import PyODataException
from pyodata.v3.model import Config, MetadataBuilder, ParserError, PolicyIgnore
from tests.conftest import contents_of_fixtures_file


URL_ROOT = 'http://odatapy.example.com'
DUMMY_CONNECTION = object()


class _StaticMetadataConnection:

    def __init__(self, metadata):
        self.metadata = metadata
        self.requested_urls = []

    def get(self, url):
        self.requested_urls.append(url)
        return pyodata.v2.service.ODataHttpResponse(
            url=url,
            headers={'content-type': 'application/xml'},
            status_code=200,
            content=self.metadata)


class _AsyncMetadataResponse:

    def __init__(self, url, metadata):
        self.url = url
        self.headers = {'content-type': 'application/xml'}
        self.status = 200
        self._metadata = metadata

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return False

    async def read(self):
        return self._metadata


class _AsyncMetadataConnection:

    def __init__(self, metadata):
        self.metadata = metadata
        self.requested_urls = []

    def get(self, url):
        self.requested_urls.append(url)
        return _AsyncMetadataResponse(url, self.metadata)


class _StaticResponseConnection:

    def __init__(self, response):
        self.response = response
        self.requests = []

    def request(self, method, url, headers=None, params=None, data=None):
        self.requests.append({
            'method': method,
            'url': url,
            'headers': headers,
            'params': params,
            'data': data,
        })
        return self.response


@pytest.fixture
def metadata_v3():
    """Minimal, realistic OData V3 metadata."""

    return contents_of_fixtures_file('metadata_v3.xml')


@pytest.fixture
def schema_v3(metadata_v3):
    """V3 schema parsed with property errors downgraded for baseline request-shape tests."""

    config = Config(custom_error_policies={
        ParserError.PROPERTY: PolicyIgnore(),
    })

    return MetadataBuilder(metadata_v3, config=config).build()


@pytest.fixture
def service_v3(schema_v3):
    """Direct service fixture used to describe future V3 request behavior."""

    return pyodata.v3.service.Service(URL_ROOT, schema_v3, DUMMY_CONNECTION)


@pytest.fixture
def service_v2_compat(schema_v3):
    """V2 service using the same schema fixture to pin header differences to protocol version."""

    return pyodata.v2.service.Service(URL_ROOT, schema_v3, DUMMY_CONNECTION)


def test_client_exposes_odata_version_3():
    assert pyodata.Client.ODATA_VERSION_3 == 3


def test_v3_fixture_can_build_a_direct_service(service_v3):
    """The direct service fixture gives us a stable baseline for request-shape tests."""

    assert isinstance(service_v3, pyodata.v3.service.Service)
    assert service_v3.schema.entity_set('Documents').name == 'Documents'
    assert service_v3.functions.SearchDocuments.get_method() == 'GET'


def test_create_sync_client_with_odata_version_3(metadata_v3):
    service = pyodata.Client(URL_ROOT, DUMMY_CONNECTION, odata_version=3, metadata=metadata_v3)

    assert isinstance(service, pyodata.v3.service.Service)
    assert service.schema.entity_type('Document').name == 'Document'


def test_create_sync_client_with_fetched_metadata_odata_version_3(metadata_v3):
    connection = _StaticMetadataConnection(metadata_v3)

    service = pyodata.Client(URL_ROOT, connection, odata_version=3)

    assert isinstance(service, pyodata.v3.service.Service)
    assert service.schema.entity_type('Document').name == 'Document'
    assert connection.requested_urls == [f'{URL_ROOT}/$metadata']


@pytest.mark.asyncio
async def test_create_async_client_with_odata_version_3(metadata_v3):
    connection = _AsyncMetadataConnection(metadata_v3)

    service = await pyodata.Client.build_async_client(
        URL_ROOT,
        connection,
        odata_version=3,
        metadata=metadata_v3)

    assert isinstance(service, pyodata.v3.service.Service)
    assert service.schema.entity_type('Document').name == 'Document'
    assert connection.requested_urls == []


@pytest.mark.asyncio
async def test_create_async_client_with_fetched_metadata_odata_version_3(metadata_v3):
    connection = _AsyncMetadataConnection(metadata_v3)

    service = await pyodata.Client.build_async_client(URL_ROOT, connection, odata_version=3)

    assert isinstance(service, pyodata.v3.service.Service)
    assert service.schema.entity_type('Document').name == 'Document'
    assert connection.requested_urls == [f'{URL_ROOT}/$metadata']


def test_v3_json_requests_use_verbose_json_and_max_data_service_version(service_v3):
    entity_request = service_v3.entity_sets.Documents.get_entity(1)
    query_request = service_v3.entity_sets.Documents.get_entities()
    function_request = service_v3.functions.SearchDocuments

    expected_headers = {
        'Accept': 'application/json;odata=verbose',
        'MaxDataServiceVersion': '3.0',
    }

    assert entity_request.get_headers() == expected_headers
    assert query_request.get_headers() == expected_headers
    assert function_request.get_headers() == expected_headers


def test_v3_json_write_requests_use_verbose_json_headers(service_v3):
    create_request = service_v3.entity_sets.Documents.create_entity()
    update_request = service_v3.entity_sets.Documents.update_entity(1)

    assert create_request.get_headers() == {
        'Accept': 'application/json;odata=verbose',
        'Content-Type': 'application/json;odata=verbose',
        'MaxDataServiceVersion': '3.0',
        'X-Requested-With': 'X',
    }
    assert update_request.get_headers() == {
        'Accept': 'application/json;odata=verbose',
        'Content-Type': 'application/json;odata=verbose',
        'MaxDataServiceVersion': '3.0',
    }


def test_v2_json_request_headers_remain_unchanged(service_v2_compat):
    entity_request = service_v2_compat.entity_sets.Documents.get_entity(1)
    create_request = service_v2_compat.entity_sets.Documents.create_entity()

    assert entity_request.get_headers() == {
        'Accept': 'application/json',
    }
    assert create_request.get_headers() == {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'X-Requested-With': 'X',
    }


def test_v3_non_verbose_json_payload_fails_clearly(schema_v3):
    connection = _StaticResponseConnection(pyodata.v2.service.ODataHttpResponse(
        url=f'{URL_ROOT}/Documents(1)',
        headers={'Content-type': 'application/json'},
        status_code=200,
        content=b'{"Id": 1, "Title": "Spec draft"}'))
    service = pyodata.v3.service.Service(URL_ROOT, schema_v3, connection)

    with pytest.raises(PyODataException) as exc_info:
        service.entity_sets.Documents.get_entity(1, encode_path=False).execute()

    assert str(exc_info.value) == (
        'OData V3 currently supports Verbose JSON only; '
        'expected a top-level "d" envelope in the response payload')


@pytest.mark.xfail(reason='FunctionRequest still serializes parameters as V2 query-string options', strict=True)
def test_v3_unbound_function_uses_path_style_parameters(service_v3):
    request = service_v3.functions.SearchDocuments.parameter('Query', 'draft').parameter('Limit', 2)

    assert request.get_path() == "SearchDocuments(Query='draft',Limit=2)"
    assert request.get_query_params() == {}


@pytest.mark.xfail(reason='Bound functions do not have a V3 invocation surface yet', strict=True)
def test_v3_bound_function_url_shape(service_v3):
    request = service_v3.entity_sets.Documents.get_entity(1).functions.GetPeerDocument.parameter('Mode', 'related')

    assert request.get_method() == 'GET'
    assert request.get_path() == "Documents(1)/GetPeerDocument(Mode='related')"
    assert request.get_query_params() == {}


@pytest.mark.xfail(reason='Bound actions do not have a V3 invocation surface yet', strict=True)
def test_v3_bound_action_url_shape(service_v3):
    request = service_v3.entity_sets.Documents.get_entity(1).actions.Approve.parameter('Comment', 'ship it')

    assert request.get_method() == 'POST'
    assert request.get_path() == 'Documents(1)/V3DemoContainer.Approve'
    assert request.get_headers() == {
        'Accept': 'application/json;odata=verbose',
        'Content-Type': 'application/json;odata=verbose',
        'MaxDataServiceVersion': '3.0',
    }
    assert request.get_body() == '{"Comment": "ship it"}'


@pytest.mark.xfail(reason='Named stream access is not modelled on the service surface yet', strict=True)
def test_v3_named_stream_access_api_shape(service_v3):
    request = service_v3.entity_sets.Documents.get_entity(1).named_stream('Thumbnail')

    assert isinstance(request, pyodata.v3.service.ODataHttpRequest)
    assert request.get_path() == 'Documents(1)/Thumbnail'


@pytest.mark.xfail(reason='Open type CRUD still rejects undeclared properties', strict=True)
def test_v3_open_type_crud_allows_dynamic_properties(service_v3):
    create_request = service_v3.entity_sets.Documents.create_entity().set(
        Id=1,
        Title='Spec draft',
        DynamicTag='red',
    )
    update_request = service_v3.entity_sets.Documents.update_entity(1).set(
        DynamicTag='green',
    )

    assert create_request.get_body() == '{"Id": 1, "Title": "Spec draft", "DynamicTag": "red"}'
    assert update_request.get_body() == '{"DynamicTag": "green"}'
