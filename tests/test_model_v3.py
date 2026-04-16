"""V3 metadata baseline tests."""

import io

import pytest
from lxml import etree

from pyodata.v3.model import Config, MetadataBuilder, TypeInfo, Types


@pytest.fixture
def reference_schema_v3_odata(reference_v3_odata_metadata):
    return MetadataBuilder(reference_v3_odata_metadata, config=Config()).build()


@pytest.fixture
def reference_schema_v3_odata_readwrite(reference_v3_odata_readwrite_metadata):
    return MetadataBuilder(reference_v3_odata_readwrite_metadata, config=Config()).build()


@pytest.fixture
def reference_schema_v3_northwind(reference_v3_northwind_metadata):
    return MetadataBuilder(reference_v3_northwind_metadata, config=Config()).build()


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


def test_v3_stream_metadata_is_exposed(schema_v3):
    document = schema_v3.entity_type('Document')

    assert document.has_stream is True
    assert document.proprty('Thumbnail').type_info == TypeInfo(None, 'Edm.Stream', False)
    assert document.proprty('Thumbnail').typ.name == 'Edm.Stream'


def test_v3_open_type_metadata_is_exposed(schema_v3):
    document = schema_v3.entity_type('Document')
    closed_document = schema_v3.entity_type('ClosedDocument')

    assert document.is_open_type is True
    assert closed_document.is_open_type is False


def test_v3_spatial_primitive_types_are_registered(schema_v3):
    assert Types.from_name('Edm.GeographyPoint').name == 'Edm.GeographyPoint'
    assert Types.from_name('Edm.GeometryPoint').name == 'Edm.GeometryPoint'
    assert Types.from_name('Collection(Edm.GeographyPoint)').item_type.name == 'Edm.GeographyPoint'


def test_v3_spatial_primitive_is_resolved(schema_v3):
    document = schema_v3.entity_type('Document')

    assert document.proprty('Location').typ.name == 'Edm.GeographyPoint'
    assert document.proprty('Footprint').typ.name == 'Edm.GeometryPoint'
    assert document.proprty('Location').type_info == TypeInfo(None, 'Edm.GeographyPoint', False)
    assert document.proprty('Footprint').type_info == TypeInfo(None, 'Edm.GeometryPoint', False)


def test_reference_v3_odata_metadata_exposes_public_service_features(reference_schema_v3_odata):
    category = reference_schema_v3_odata.entity_type('Category')
    person_detail = reference_schema_v3_odata.entity_type('PersonDetail')
    supplier = reference_schema_v3_odata.entity_type('Supplier')
    advertisement = reference_schema_v3_odata.entity_type('Advertisement')
    get_products_by_rating = reference_schema_v3_odata.function_import('GetProductsByRating')

    assert category.is_open_type is True
    assert person_detail.proprty('Photo').type_info == TypeInfo(None, 'Edm.Stream', False)
    assert advertisement.has_stream is True
    assert supplier.proprty('Location').type_info == TypeInfo(None, 'Edm.GeographyPoint', False)
    assert get_products_by_rating.http_method == 'GET'
    assert get_products_by_rating.is_bindable is False
    assert get_products_by_rating.is_side_effecting is False
    assert get_products_by_rating.return_type.is_collection is True
    assert [parameter.name for parameter in get_products_by_rating.parameters] == ['rating']


def test_reference_v3_odata_readwrite_metadata_defaults_missing_http_methods(reference_schema_v3_odata_readwrite):
    discount = reference_schema_v3_odata_readwrite.function_import('Discount')
    increase_salaries = reference_schema_v3_odata_readwrite.function_import('IncreaseSalaries')

    assert discount.http_method == 'GET'
    assert discount.is_bindable is True
    assert discount.is_side_effecting is False
    assert discount.binding_parameter.name == 'product'
    assert discount.binding_parameter.typ.name == 'Product'
    assert discount.container_name == 'DemoService'

    assert increase_salaries.http_method == 'POST'
    assert increase_salaries.is_bindable is False
    assert increase_salaries.is_side_effecting is True
    assert increase_salaries.return_type is None
    assert [parameter.name for parameter in increase_salaries.parameters] == ['percentage']


def test_reference_v3_northwind_metadata_parses_large_real_world_service(reference_schema_v3_northwind):
    assert set(reference_schema_v3_northwind.namespaces) == {'NorthwindModel', 'ODataWebV3.Northwind.Model'}
    assert reference_schema_v3_northwind.entity_set('Products').entity_type.name == 'Product'
    assert reference_schema_v3_northwind.entity_set('Categories').entity_type.name == 'Category'
    assert reference_schema_v3_northwind.entity_type('Product').proprty('ProductName').type_info == (
        TypeInfo(None, 'Edm.String', False))
    assert len(reference_schema_v3_northwind.entity_sets) > 20
