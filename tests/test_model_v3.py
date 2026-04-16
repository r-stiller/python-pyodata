"""V3 metadata baseline tests."""

import io

import pytest
from lxml import etree

from pyodata.v3.model import Config, MetadataBuilder, NullType, ParserError, PolicyIgnore, TypeInfo
from tests.conftest import contents_of_fixtures_file


@pytest.fixture
def metadata_v3():
    """Minimal, realistic OData V3 metadata."""

    return contents_of_fixtures_file('metadata_v3.xml')


@pytest.fixture
def schema_v3(metadata_v3):
    """V3 schema parsed with property errors downgraded for baseline coverage."""

    config = Config(custom_error_policies={
        ParserError.PROPERTY: PolicyIgnore(),
    })

    return MetadataBuilder(metadata_v3, config=config).build()


def test_v3_builder_accepts_microsoft_2009_11_edm_namespace(schema_v3):
    """The builder already whitelists the V3 EDM namespace."""

    assert set(schema_v3.namespaces) == {'V3Demo.External', 'V3Demo.Model'}
    assert schema_v3.entity_type('Document').name == 'Document'


def test_v3_aliases_resolve_property_types_from_schema_alias_and_using(schema_v3):
    """V3 property types should resolve aliases declared by Schema Alias and edm:Using."""

    document = schema_v3.entity_type('Document')

    local_info = document.proprty('LocalInfo')
    external_info = document.proprty('ExternalInfo')

    assert local_info.type_info.namespace == 'V3Demo.Model'
    assert local_info.type_info.name == 'LocalInfo'
    assert local_info.typ.name == 'LocalInfo'

    assert external_info.type_info.namespace == 'V3Demo.External'
    assert external_info.type_info.name == 'TagInfo'
    assert external_info.typ.name == 'TagInfo'


def test_v3_function_import_basics_are_parsed(schema_v3):
    """Current parsing already gives us the V2-shaped baseline for V3 FunctionImport nodes."""

    search = schema_v3.function_import('SearchDocuments')
    peer = schema_v3.function_import('GetPeerDocument')
    approve = schema_v3.function_import('Approve')
    filter_documents = schema_v3.function_import('FilterDocuments')
    approve_all = schema_v3.function_import('ApproveAll')

    assert search.http_method == 'GET'
    assert search.entity_set_name == 'Documents'
    assert search.return_type.is_collection
    assert [parameter.name for parameter in search.parameters] == ['Query', 'Limit']

    assert peer.http_method == 'GET'
    assert peer.return_type.name == 'Document'
    assert [parameter.name for parameter in peer.parameters] == ['bindingParameter', 'Mode']

    assert approve.http_method == 'POST'
    assert approve.return_type.name == 'Edm.Boolean'
    assert [parameter.name for parameter in approve.parameters] == ['bindingParameter', 'Comment']

    assert filter_documents.http_method == 'GET'
    assert filter_documents.return_type.is_collection
    assert [parameter.name for parameter in filter_documents.parameters] == ['bindingParameter', 'Query', 'Limit']

    assert approve_all.http_method == 'POST'
    assert approve_all.return_type is None
    assert [parameter.name for parameter in approve_all.parameters] == ['bindingParameter', 'Comment', 'Force']


def test_v3_alias_declarations_are_extracted_for_schema_alias_and_using(metadata_v3):
    config = Config(xml_namespaces={
        'edmx': 'http://schemas.microsoft.com/ado/2007/06/edmx',
        'edm': 'http://schemas.microsoft.com/ado/2009/11/edm',
    })

    aliases = MetadataBuilder.get_aliases(etree.parse(io.BytesIO(metadata_v3)), config)

    assert aliases['V3Demo.Model'] == {'Self'}
    assert aliases['V3Demo.External'] == {'Ext', 'External'}


def test_v3_function_import_exposes_operation_flags(schema_v3):
    search = schema_v3.function_import('SearchDocuments')
    peer = schema_v3.function_import('GetPeerDocument')
    approve = schema_v3.function_import('Approve')
    filter_documents = schema_v3.function_import('FilterDocuments')
    approve_all = schema_v3.function_import('ApproveAll')

    assert search.is_bindable is False
    assert search.is_side_effecting is False
    assert search.is_composable is True
    assert search.entity_set_path is None

    assert peer.is_bindable is True
    assert peer.is_side_effecting is False
    assert peer.is_composable is True
    assert peer.entity_set_path == 'bindingParameter'

    assert approve.is_bindable is True
    assert approve.is_side_effecting is True
    assert approve.is_composable is False
    assert approve.entity_set_path == 'bindingParameter'

    assert filter_documents.is_bindable is True
    assert filter_documents.is_side_effecting is False
    assert filter_documents.is_composable is True
    assert filter_documents.entity_set_path == 'bindingParameter'

    assert approve_all.is_bindable is True
    assert approve_all.is_side_effecting is True
    assert approve_all.is_composable is False
    assert approve_all.entity_set_path == 'bindingParameter'


def test_v3_function_import_return_types_and_binding_parameters_are_parsed(schema_v3):
    search = schema_v3.function_import('SearchDocuments')
    peer = schema_v3.function_import('GetPeerDocument')
    approve = schema_v3.function_import('Approve')
    filter_documents = schema_v3.function_import('FilterDocuments')
    approve_all = schema_v3.function_import('ApproveAll')

    assert search.return_type_info == TypeInfo('V3Demo.Model', 'Document', True)
    assert search.binding_parameter is None
    assert [parameter.is_binding_parameter for parameter in search.parameters] == [False, False]

    assert peer.return_type_info == TypeInfo('V3Demo.Model', 'Document', False)
    assert peer.binding_parameter.name == 'bindingParameter'
    assert peer.binding_parameter.is_binding_parameter is True
    assert peer.binding_parameter.typ.name == 'Document'

    assert approve.return_type_info == TypeInfo(None, 'Edm.Boolean', False)
    assert approve.binding_parameter.name == 'bindingParameter'
    assert approve.binding_parameter.typ.name == 'Document'

    assert filter_documents.return_type_info == TypeInfo('V3Demo.Model', 'Document', True)
    assert filter_documents.binding_parameter.name == 'bindingParameter'
    assert filter_documents.binding_parameter.typ.is_collection is True
    assert filter_documents.binding_parameter.typ.item_type.name == 'Document'

    assert approve_all.return_type_info is None
    assert approve_all.binding_parameter.name == 'bindingParameter'
    assert approve_all.binding_parameter.typ.is_collection is True


@pytest.mark.xfail(reason='Open type and stream metadata are not exposed on entity types yet', strict=True)
def test_v3_open_type_and_stream_metadata_are_exposed(schema_v3):
    document = schema_v3.entity_type('Document')

    assert document.is_open_type is True
    assert document.has_stream is True
    assert document.proprty('Thumbnail').typ.name == 'Edm.Stream'


@pytest.mark.xfail(reason='Spatial primitives are not registered in the current type system yet', strict=True)
def test_v3_spatial_primitive_is_resolved(schema_v3):
    document = schema_v3.entity_type('Document')

    assert not isinstance(document.proprty('Location').typ, NullType)
    assert document.proprty('Location').typ.name == 'Edm.GeographyPoint'
