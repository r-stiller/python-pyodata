"""V3 service baseline tests."""

import pytest

import pyodata
import pyodata.v2.service
from pyodata.v2.model import Config, MetadataBuilder, ParserError, PolicyIgnore
from tests.conftest import contents_of_fixtures_file


URL_ROOT = 'http://odatapy.example.com'
DUMMY_CONNECTION = object()


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

    return pyodata.v2.service.Service(URL_ROOT, schema_v3, DUMMY_CONNECTION)


def test_v3_fixture_can_build_a_direct_service(service_v3):
    """The direct service fixture gives us a stable baseline for request-shape tests."""

    assert service_v3.schema.entity_set('Documents').name == 'Documents'
    assert service_v3.functions.SearchDocuments.get_method() == 'GET'


@pytest.mark.xfail(reason='Client entrypoints reject odata_version=3 today', strict=True)
def test_create_sync_client_with_odata_version_3(metadata_v3):
    service = pyodata.Client(URL_ROOT, DUMMY_CONNECTION, odata_version=3, metadata=metadata_v3)

    assert isinstance(service, pyodata.v2.service.Service)
    assert service.schema.entity_type('Document').name == 'Document'


@pytest.mark.xfail(reason='V3 request headers are still hard-coded to V2 JSON defaults', strict=True)
def test_v3_json_requests_use_verbose_json_and_max_data_service_version(service_v3):
    request = service_v3.entity_sets.Documents.get_entity(1)

    assert request.get_headers() == {
        'Accept': 'application/json;odata=verbose',
        'MaxDataServiceVersion': '3.0',
    }


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

    assert isinstance(request, pyodata.v2.service.ODataHttpRequest)
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
