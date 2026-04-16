"""V3 service baseline tests."""

import datetime
import json

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


def test_v3_unbound_function_uses_path_style_parameters(service_v3):
    request = service_v3.functions.SearchDocuments.parameter('Query', 'draft').parameter('Limit', 2)

    assert request.get_path() == "SearchDocuments(Query='draft',Limit=2)"
    assert request.get_query_params() == {}


def test_v3_unbound_function_parameter_order_is_metadata_stable(service_v3):
    request = service_v3.functions.SearchDocuments.parameter('Limit', 2).parameter('Query', 'draft')

    assert request.get_path() == "SearchDocuments(Query='draft',Limit=2)"


def test_v3_unbound_function_reuses_existing_literal_formatting(service_v3):
    request = service_v3.functions.SearchDocumentsCreatedAfter.parameter(
        'Exact', True).parameter(
        'CreatedAfter', datetime.datetime(2017, 12, 24, 18, 0, tzinfo=datetime.timezone.utc))

    assert request.get_path() == (
        "SearchDocumentsCreatedAfter(CreatedAfter=datetime'2017-12-24T18:00:00',Exact=true)")


def test_v3_unbound_action_uses_post_and_json_request_shape(schema_v3):
    connection = _StaticResponseConnection(pyodata.v2.service.ODataHttpResponse(
        url=f'{URL_ROOT}/ApproveDocuments',
        headers={'Content-type': 'application/json'},
        status_code=200,
        content=b'{"d": true}'))
    service = pyodata.v3.service.Service(URL_ROOT, schema_v3, connection)

    request = service.functions.ApproveDocuments.parameter('Force', True).parameter('Comment', 'ship it')

    assert request.get_method() == 'POST'
    assert request.get_path() == 'ApproveDocuments'
    assert request.get_query_params() == {}
    assert request.get_headers() == {
        'Accept': 'application/json;odata=verbose',
        'Content-Type': 'application/json;odata=verbose',
        'MaxDataServiceVersion': '3.0',
    }
    assert request.get_body() == '{"Comment": "ship it", "Force": true}'
    assert request.execute() is True
    assert connection.requests == [{
        'method': 'POST',
        'url': f'{URL_ROOT}/ApproveDocuments',
        'headers': {
            'Accept': 'application/json;odata=verbose',
            'Content-Type': 'application/json;odata=verbose',
            'MaxDataServiceVersion': '3.0',
        },
        'params': '',
        'data': '{"Comment": "ship it", "Force": true}',
    }]


def test_v3_unbound_action_without_return_uses_no_return_handling(schema_v3):
    connection = _StaticResponseConnection(pyodata.v2.service.ODataHttpResponse(
        url=f'{URL_ROOT}/RefreshSearchIndex',
        headers={},
        status_code=204,
        content=b''))
    service = pyodata.v3.service.Service(URL_ROOT, schema_v3, connection)

    request = service.functions.RefreshSearchIndex

    assert request.get_method() == 'POST'
    assert request.get_path() == 'RefreshSearchIndex'
    assert request.get_body() is None
    assert request.execute() is None


def test_v3_bound_function_url_shape(service_v3):
    request = service_v3.entity_sets.Documents.get_entity(1).functions.GetPeerDocument.parameter('Mode', 'related')

    assert request.get_method() == 'GET'
    assert request.get_path() == "Documents(1)/GetPeerDocument(Mode='related')"
    assert request.get_query_params() == {}


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


def test_v3_bound_function_omits_binding_parameter_from_callers(service_v3):
    request = service_v3.entity_sets.Documents.get_entity(1).functions.GetPeerDocument

    with pytest.raises(PyODataException) as exc_info:
        request.parameter('bindingParameter', {'Id': 1})

    assert str(exc_info.value) == 'Bound operation GetPeerDocument is not available via service.functions'


def test_v3_bound_function_execute_uses_entity_context_and_returns_v3_entity_proxy(schema_v3):
    connection = _StaticResponseConnection(pyodata.v2.service.ODataHttpResponse(
        url=f'{URL_ROOT}/Documents(1)/GetPeerDocument(Mode=%27related%27)',
        headers={'Content-type': 'application/json'},
        status_code=200,
        content=b'{"d": {"Id": 2, "Title": "Peer draft"}}'))
    service = pyodata.v3.service.Service(URL_ROOT, schema_v3, connection)

    request = service.entity_sets.Documents.get_entity(1).functions.GetPeerDocument.parameter('Mode', 'related')
    result = request.execute()

    assert isinstance(result, pyodata.v3.service.EntityProxy)
    assert result.Id == 2
    assert result.Title == 'Peer draft'
    assert result.actions.Approve.get_path() == 'Documents(2)/V3DemoContainer.Approve'
    assert connection.requests == [{
        'method': 'GET',
        'url': f"{URL_ROOT}/Documents(1)/GetPeerDocument(Mode='related')",
        'headers': {
            'Accept': 'application/json;odata=verbose',
            'MaxDataServiceVersion': '3.0',
        },
        'params': '',
        'data': None,
    }]


def test_v3_bound_action_execute_uses_entity_context(schema_v3):
    connection = _StaticResponseConnection(pyodata.v2.service.ODataHttpResponse(
        url=f'{URL_ROOT}/Documents(1)/V3DemoContainer.Approve',
        headers={'Content-type': 'application/json'},
        status_code=200,
        content=b'{"d": true}'))
    service = pyodata.v3.service.Service(URL_ROOT, schema_v3, connection)

    request = service.entity_sets.Documents.get_entity(1).actions.Approve.parameter('Comment', 'ship it')

    assert request.execute() is True
    assert connection.requests == [{
        'method': 'POST',
        'url': f'{URL_ROOT}/Documents(1)/V3DemoContainer.Approve',
        'headers': {
            'Accept': 'application/json;odata=verbose',
            'Content-Type': 'application/json;odata=verbose',
            'MaxDataServiceVersion': '3.0',
        },
        'params': '',
        'data': '{"Comment": "ship it"}',
    }]


def test_v3_collection_bound_function_url_shape_and_parameter_order(service_v3):
    request = service_v3.entity_sets.Documents.functions.FilterDocuments.parameter(
        'Limit', 2).parameter(
        'Query', 'draft')

    assert request.get_method() == 'GET'
    assert request.get_path() == "Documents/FilterDocuments(Query='draft',Limit=2)"
    assert request.get_query_params() == {}


def test_v3_collection_bound_action_without_return_uses_no_return_handling(schema_v3):
    connection = _StaticResponseConnection(pyodata.v2.service.ODataHttpResponse(
        url=f'{URL_ROOT}/Documents/V3DemoContainer.ApproveAll',
        headers={},
        status_code=204,
        content=b''))
    service = pyodata.v3.service.Service(URL_ROOT, schema_v3, connection)

    request = service.entity_sets.Documents.actions.ApproveAll.parameter(
        'Force', True).parameter(
        'Comment', 'ship it')

    assert request.get_method() == 'POST'
    assert request.get_path() == 'Documents/V3DemoContainer.ApproveAll'
    assert request.get_body() == '{"Comment": "ship it", "Force": true}'
    assert request.execute() is None
    assert connection.requests == [{
        'method': 'POST',
        'url': f'{URL_ROOT}/Documents/V3DemoContainer.ApproveAll',
        'headers': {
            'Accept': 'application/json;odata=verbose',
            'Content-Type': 'application/json;odata=verbose',
            'MaxDataServiceVersion': '3.0',
        },
        'params': '',
        'data': '{"Comment": "ship it", "Force": true}',
    }]


def test_v3_batch_request_executes_verbose_json_read_and_bound_action(schema_v3):
    response_body = (
        b'--batch_v3\n'
        b'Content-Type: application/http\n'
        b'Content-Transfer-Encoding: binary\n'
        b'\n'
        b'HTTP/1.1 200 OK\n'
        b'Content-Type: application/json;odata=verbose\n'
        b'\n'
        b'{"d": {"Id": 1, "Title": "Spec draft"}}\n'
        b'--batch_v3\n'
        b'Content-Type: multipart/mixed; boundary=changeset_v3\n'
        b'\n'
        b'--changeset_v3\n'
        b'Content-Type: application/http\n'
        b'Content-Transfer-Encoding: binary\n'
        b'\n'
        b'HTTP/1.1 200 OK\n'
        b'Content-Type: application/json;odata=verbose\n'
        b'\n'
        b'{"d": true}\n'
        b'--changeset_v3--\n'
        b'\n'
        b'--batch_v3--')
    connection = _StaticResponseConnection(pyodata.v2.service.ODataHttpResponse(
        url=f'{URL_ROOT}/$batch',
        headers={'Content-Type': 'multipart/mixed; boundary=batch_v3'},
        status_code=202,
        content=response_body))
    service = pyodata.v3.service.Service(URL_ROOT, schema_v3, connection)

    batch = service.create_batch('v3')
    changeset = service.create_changeset('v3')

    batch.add_request(service.entity_sets.Documents.get_entity(1, encode_path=False))
    changeset.add_request(
        service.entity_sets.Documents.get_entity(1, encode_path=False).actions.Approve.parameter(
            'Comment', 'ship it'))
    batch.add_request(changeset)

    result = batch.execute()

    assert len(result) == 2
    assert isinstance(result[0], pyodata.v3.service.EntityProxy)
    assert result[0].Title == 'Spec draft'
    assert result[1] == [True]
    assert connection.requests == [{
        'method': 'POST',
        'url': f'{URL_ROOT}/$batch',
        'headers': {
            'Content-Type': 'multipart/mixed;boundary=batch_v3',
        },
        'params': '',
        'data': batch.get_body(),
    }]
    assert 'GET Documents(1) HTTP/1.1' in connection.requests[0]['data']
    assert 'Accept: application/json;odata=verbose' in connection.requests[0]['data']
    assert 'MaxDataServiceVersion: 3.0' in connection.requests[0]['data']
    assert 'POST Documents(1)/V3DemoContainer.Approve HTTP/1.1' in connection.requests[0]['data']
    assert 'Content-Type: application/json;odata=verbose' in connection.requests[0]['data']
    assert '{"Comment": "ship it"}' in connection.requests[0]['data']


def test_v3_media_stream_access_api_shape(service_v3):
    request = service_v3.entity_sets.Documents.get_entity(1).media_stream()

    assert isinstance(request, pyodata.v3.service.ODataHttpRequest)
    assert request.get_path() == 'Documents%281%29/$value'


def test_v3_named_stream_access_api_shape(service_v3):
    request = service_v3.entity_sets.Documents.get_entity(1).named_stream('Thumbnail')

    assert isinstance(request, pyodata.v3.service.ODataHttpRequest)
    assert request.get_path() == 'Documents%281%29/Thumbnail'


def test_v3_media_stream_execute_returns_raw_response(schema_v3):
    connection = _StaticResponseConnection(pyodata.v2.service.ODataHttpResponse(
        url=f'{URL_ROOT}/Documents(1)/$value',
        headers={'Content-type': 'application/octet-stream'},
        status_code=200,
        content=b'%PDF-1.7'))
    service = pyodata.v3.service.Service(URL_ROOT, schema_v3, connection)

    response = service.entity_sets.Documents.get_entity(1).media_stream().execute()

    assert response.content == b'%PDF-1.7'
    assert connection.requests == [{
        'method': 'GET',
        'url': f'{URL_ROOT}/Documents%281%29/$value',
        'headers': {},
        'params': '',
        'data': None,
    }]


def test_v3_named_stream_execute_returns_raw_response_from_entity_proxy(schema_v3):
    connection = _StaticResponseConnection(pyodata.v2.service.ODataHttpResponse(
        url=f'{URL_ROOT}/Documents(1)/Thumbnail',
        headers={'Content-type': 'image/png'},
        status_code=200,
        content=b'\x89PNG'))
    service = pyodata.v3.service.Service(URL_ROOT, schema_v3, connection)
    entity = pyodata.v3.service.EntityProxy(
        service,
        service.schema.entity_set('Documents'),
        service.schema.entity_type('Document'),
        {'Id': 1, 'Title': 'Spec draft'})

    response = entity.named_stream('Thumbnail').execute()

    assert response.content == b'\x89PNG'
    assert connection.requests == [{
        'method': 'GET',
        'url': f'{URL_ROOT}/Documents(1)/Thumbnail',
        'headers': {},
        'params': '',
        'data': None,
    }]


def test_v3_media_stream_requires_has_stream_metadata(service_v3):
    entity = pyodata.v3.service.EntityProxy(
        service_v3,
        service_v3.schema.entity_set('Documents'),
        service_v3.schema.entity_type('Document'),
        {'Id': 1, 'Title': 'Spec draft'})
    entity._entity_type._has_stream = False  # pylint: disable=protected-access

    with pytest.raises(PyODataException) as exc_info:
        entity.media_stream()

    assert str(exc_info.value) == 'Entity type Document does not declare HasStream'


def test_v3_named_stream_access_rejects_unknown_property(service_v3):
    with pytest.raises(PyODataException) as exc_info:
        service_v3.entity_sets.Documents.get_entity(1).named_stream('Missing')

    assert str(exc_info.value) == 'Property Missing is not declared in Document entity type'


def test_v3_named_stream_access_rejects_non_stream_property(service_v3):
    with pytest.raises(PyODataException) as exc_info:
        service_v3.entity_sets.Documents.get_entity(1).named_stream('Title')

    assert str(exc_info.value) == 'Property Title of Document is not declared as Edm.Stream'


def test_v3_open_type_entity_proxy_retains_dynamic_properties(service_v3):
    entity = pyodata.v3.service.EntityProxy(
        service_v3,
        service_v3.schema.entity_set('Documents'),
        service_v3.schema.entity_type('Document'),
        {'Id': 1, 'Title': 'Spec draft', 'DynamicTag': 'red', 'DynamicCount': 3})

    assert entity.Title == 'Spec draft'
    assert entity.DynamicTag == 'red'
    assert entity.DynamicCount == 3
    assert entity._cache['DynamicTag'] == 'red'  # pylint: disable=protected-access


def test_v3_get_entity_materializes_dynamic_properties_for_open_type(schema_v3):
    connection = _StaticResponseConnection(pyodata.v2.service.ODataHttpResponse(
        url=f'{URL_ROOT}/Documents(1)',
        headers={'Content-type': 'application/json'},
        status_code=200,
        content=b'{"d": {"Id": 1, "Title": "Spec draft", "DynamicTag": "red"}}'))
    service = pyodata.v3.service.Service(URL_ROOT, schema_v3, connection)

    entity = service.entity_sets.Documents.get_entity(1).execute()

    assert isinstance(entity, pyodata.v3.service.EntityProxy)
    assert entity.DynamicTag == 'red'


def test_v3_get_entities_materializes_dynamic_properties_for_open_type(schema_v3):
    connection = _StaticResponseConnection(pyodata.v2.service.ODataHttpResponse(
        url=f'{URL_ROOT}/Documents',
        headers={'Content-type': 'application/json'},
        status_code=200,
        content=b'{"d": {"results": [{"Id": 1, "Title": "Spec draft", "DynamicTag": "red"}]}}'))
    service = pyodata.v3.service.Service(URL_ROOT, schema_v3, connection)

    entities = service.entity_sets.Documents.get_entities().execute()

    assert len(entities) == 1
    assert isinstance(entities[0], pyodata.v3.service.EntityProxy)
    assert entities[0].DynamicTag == 'red'


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


def test_v3_spatial_properties_materialize_from_verbose_json(schema_v3):
    location = {
        'type': 'Point',
        'coordinates': [14.42076, 50.08804],
    }
    footprint = {
        'type': 'Point',
        'coordinates': [14.421, 50.088],
    }
    response_payload = json.dumps({
        'd': {
            'Id': 1,
            'Title': 'Spec draft',
            'Location': location,
            'Footprint': footprint,
        }
    }).encode('utf-8')
    connection = _StaticResponseConnection(pyodata.v2.service.ODataHttpResponse(
        url=f'{URL_ROOT}/Documents(1)',
        headers={'Content-type': 'application/json'},
        status_code=200,
        content=response_payload))
    service = pyodata.v3.service.Service(URL_ROOT, schema_v3, connection)

    entity = service.entity_sets.Documents.get_entity(1).execute()

    assert entity.Location == location
    assert entity.Footprint == footprint
    assert entity._cache['Location'] == location  # pylint: disable=protected-access


def test_v3_spatial_properties_round_trip_in_create_update_payloads(service_v3):
    location = {
        'type': 'Point',
        'coordinates': [14.42076, 50.08804],
    }
    footprint = {
        'type': 'Point',
        'coordinates': [14.421, 50.088],
    }

    create_request = service_v3.entity_sets.Documents.create_entity().set(
        Id=1,
        Title='Spec draft',
        Location=location,
        Footprint=footprint,
    )
    update_request = service_v3.entity_sets.Documents.update_entity(1).set(
        Location=location,
    )

    assert create_request.get_body() == json.dumps({
        'Id': 1,
        'Title': 'Spec draft',
        'Location': location,
        'Footprint': footprint,
    })
    assert update_request.get_body() == json.dumps({
        'Location': location,
    })


def test_v3_spatial_values_fail_clearly_for_url_literals_and_filters(service_v3):
    spatial_value = {
        'type': 'Point',
        'coordinates': [14.42076, 50.08804],
    }

    with pytest.raises(PyODataException) as literal_exc_info:
        service_v3.schema.entity_type('Document').proprty('Location').to_literal(spatial_value)

    with pytest.raises(PyODataException) as filter_exc_info:
        service_v3.entity_sets.Documents.get_entities().filter(Location=spatial_value)

    assert str(literal_exc_info.value) == (
        'Edm.GeographyPoint does not support URL literal conversion in OData V3')
    assert str(filter_exc_info.value) == (
        'Edm.GeographyPoint does not support URL literal conversion in OData V3')


def test_v3_spatial_operation_parameters_fail_clearly(service_v3):
    spatial_value = {
        'type': 'Point',
        'coordinates': [14.42076, 50.08804],
    }

    with pytest.raises(PyODataException) as exc_info:
        service_v3.functions.SearchDocumentsNearby.parameter('Center', spatial_value)

    assert str(exc_info.value) == (
        'OData V3 operation parameter Center of type Edm.GeographyPoint is not supported')


def test_v3_closed_type_entity_proxy_keeps_strict_property_behavior(service_v3):
    entity = pyodata.v3.service.EntityProxy(
        service_v3,
        service_v3.schema.entity_set('ClosedDocuments'),
        service_v3.schema.entity_type('ClosedDocument'),
        {'Id': 1, 'Title': 'Spec draft', 'DynamicTag': 'red'})

    assert 'DynamicTag' not in entity._cache  # pylint: disable=protected-access

    with pytest.raises(AttributeError) as exc_info:
        _ = entity.DynamicTag

    assert str(exc_info.value) == 'EntityType ClosedDocument does not have Property DynamicTag: \'DynamicTag\''


def test_v3_closed_type_crud_rejects_dynamic_properties(service_v3):
    with pytest.raises(PyODataException) as create_exc_info:
        service_v3.entity_sets.ClosedDocuments.create_entity().set(
            Id=1,
            Title='Spec draft',
            DynamicTag='red',
        )

    with pytest.raises(PyODataException) as update_exc_info:
        service_v3.entity_sets.ClosedDocuments.update_entity(1).set(
            DynamicTag='green',
        )

    assert str(create_exc_info.value) == 'Property DynamicTag is not declared in ClosedDocument entity type'
    assert str(update_exc_info.value) == 'Property DynamicTag is not declared in ClosedDocument entity type'
