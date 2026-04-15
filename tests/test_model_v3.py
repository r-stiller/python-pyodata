"""V3 metadata baseline tests."""

import io

import pytest
from lxml import etree

from pyodata.v2.model import Config, MetadataBuilder, NullType, ParserError, PolicyIgnore
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


def test_v3_alias_references_are_preserved_in_property_type_info(schema_v3):
    """Alias-qualified type names should survive parsing even before alias resolution exists."""

    document = schema_v3.entity_type('Document')

    local_info = document.proprty('LocalInfo')
    external_info = document.proprty('ExternalInfo')

    assert local_info.type_info.namespace == 'Self'
    assert local_info.type_info.name == 'LocalInfo'
    assert external_info.type_info.namespace == 'Ext'
    assert external_info.type_info.name == 'TagInfo'


def test_v3_function_import_basics_are_parsed(schema_v3):
    """Current parsing already gives us the V2-shaped baseline for V3 FunctionImport nodes."""

    search = schema_v3.function_import('SearchDocuments')
    peer = schema_v3.function_import('GetPeerDocument')
    approve = schema_v3.function_import('Approve')

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


@pytest.mark.xfail(reason='V3 alias declarations are not collected from Schema Alias and edm:Using yet', strict=True)
def test_v3_alias_declarations_are_extracted_for_schema_alias_and_using(metadata_v3):
    config = Config(xml_namespaces={
        'edmx': 'http://schemas.microsoft.com/ado/2007/06/edmx',
        'edm': 'http://schemas.microsoft.com/ado/2009/11/edm',
    })

    aliases = MetadataBuilder.get_aliases(etree.parse(io.BytesIO(metadata_v3)), config)

    assert aliases['V3Demo.Model'] == {'Self'}
    assert aliases['V3Demo.External'] == {'Ext'}


@pytest.mark.xfail(reason='FunctionImport does not expose V3 bindable and side-effect metadata yet', strict=True)
def test_v3_function_import_exposes_operation_flags(schema_v3):
    search = schema_v3.function_import('SearchDocuments')
    peer = schema_v3.function_import('GetPeerDocument')
    approve = schema_v3.function_import('Approve')

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
