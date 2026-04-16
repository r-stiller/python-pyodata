"""OData V3 metadata facade with V3-specific alias collection hooks."""

import io
import warnings

from lxml import etree

from pyodata.exceptions import PyODataParserError
from pyodata.v2.model import *  # noqa: F401,F403
from pyodata.v2.model import Config as _Config
from pyodata.v2.model import MetadataBuilder as _MetadataBuilder
from pyodata.v2.model import ParserError, PolicyIgnore, Schema


class Config(_Config):
    """V3 bootstrap config with tolerant property parsing by default."""

    def __init__(self,
                 custom_error_policies=None,
                 default_error_policy=None,
                 xml_namespaces=None,
                 retain_null=False):

        policies = dict(custom_error_policies or {})
        policies.setdefault(ParserError.PROPERTY, PolicyIgnore())

        super().__init__(
            custom_error_policies=policies,
            default_error_policy=default_error_policy,
            xml_namespaces=xml_namespaces,
            retain_null=retain_null)

        self._type_aliases = {}

    @property
    def type_aliases(self):
        return self._type_aliases

    @type_aliases.setter
    def type_aliases(self, value):
        self._type_aliases = dict(value)


class MetadataBuilder(_MetadataBuilder):
    """V3 metadata builder with Schema Alias and Using alias collection."""

    def build(self):
        """Build model from the XML metadata."""

        if isinstance(self._xml, str):
            mdf = io.StringIO(self._xml)
        elif isinstance(self._xml, bytes):
            mdf = io.BytesIO(self._xml)
        else:
            raise TypeError(f'Expected bytes or str type on metadata_xml, got : {type(self._xml)}')

        namespaces = self._config.namespaces

        try:
            xml = etree.parse(mdf)
        except etree.XMLSyntaxError as ex:
            raise PyODataParserError('Metadata document syntax error') from ex

        edmx = xml.getroot()

        try:
            dataservices = next((child for child in edmx if etree.QName(child.tag).localname == 'DataServices'))
        except StopIteration:
            raise PyODataParserError('Metadata document is missing the element DataServices')

        try:
            schema = next((child for child in dataservices if etree.QName(child.tag).localname == 'Schema'))
        except StopIteration:
            raise PyODataParserError('Metadata document is missing the element Schema')

        if 'edmx' not in self._config.namespaces:
            namespace = etree.QName(edmx.tag).namespace

            if namespace not in self.EDMX_WHITELIST:
                raise PyODataParserError(f'Unsupported Edmx namespace - {namespace}')

            namespaces['edmx'] = namespace

        if 'edm' not in self._config.namespaces:
            namespace = etree.QName(schema.tag).namespace

            if namespace not in self.EDM_WHITELIST:
                raise PyODataParserError(f'Unsupported Schema namespace - {namespace}')

            namespaces['edm'] = namespace

        self._config.namespaces = namespaces

        aliases = self.get_aliases(xml, self._config)
        self._config.type_aliases = self.get_type_aliases(aliases)
        self.update_global_variables_with_alias(aliases)

        edm_schemas = xml.xpath('/edmx:Edmx/edmx:DataServices/edm:Schema', namespaces=self._config.namespaces)
        schema = Schema.from_etree(edm_schemas, self._config)
        return schema

    @staticmethod
    def get_aliases(edmx, config: Config):
        aliases = _MetadataBuilder.get_aliases(edmx, config)

        for schema_node in edmx.xpath('/edmx:Edmx/edmx:DataServices/edm:Schema', namespaces=config.namespaces):
            namespace = schema_node.get('Namespace')
            alias = schema_node.get('Alias')
            if namespace is not None and alias is not None:
                aliases[namespace].add(alias)

            for using_node in schema_node.xpath('edm:Using', namespaces=config.namespaces):
                using_namespace = using_node.get('Namespace')
                using_alias = using_node.get('Alias')
                if using_namespace is not None and using_alias is not None:
                    aliases[using_namespace].add(using_alias)

        return aliases

    @staticmethod
    def get_type_aliases(aliases):
        resolved_aliases = {}
        for namespace, namespace_aliases in aliases.items():
            for alias in namespace_aliases:
                resolved_aliases[alias] = namespace

        return resolved_aliases


def schema_from_xml(metadata_xml, namespaces=None):
    """Parses XML data and returns Schema representing OData Metadata."""

    meta = MetadataBuilder(
        metadata_xml,
        config=Config(
            xml_namespaces=namespaces,
        ))

    return meta.build()


class Edmx:
    @staticmethod
    def parse(metadata_xml, namespaces=None):
        warnings.warn("Edmx class is deprecated in favor of MetadataBuilder", DeprecationWarning)
        return schema_from_xml(metadata_xml, namespaces)
