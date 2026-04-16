"""OData V3 service facade backed by the shared request implementation."""

import json
import logging
from functools import partial

from pyodata.v2 import model
from pyodata.v2.service import *  # noqa: F401,F403
from pyodata.exceptions import HttpError, PyODataException
from pyodata.v2.service import (
    LOGGER_NAME,
    EntityContainer as _EntityContainer,
    EntityCreateRequest as _EntityCreateRequest,
    EntityGetRequest as _EntityGetRequest,
    EntityModifyRequest as _EntityModifyRequest,
    EntityProxy as _EntityProxy,
    EntitySetProxy as _EntitySetProxy,
    FunctionContainer as _FunctionContainer,
    FunctionRequest as _FunctionRequest,
    ODataHttpRequest,
    Service as _Service,
    _ODataRequestPolicy,
)


def _is_spatial_type(typ):
    if typ is None:
        return False

    return typ.name.startswith('Edm.Geography') or typ.name.startswith('Edm.Geometry')


class _ODataV3RequestPolicy(_ODataRequestPolicy):
    """OData V3 request/response policy for the current first milestone."""

    def json_get_headers(self):
        return {
            'Accept': 'application/json;odata=verbose',
            'MaxDataServiceVersion': '3.0',
        }

    def json_write_headers(self, include_x_requested_with=False):
        headers = {
            'Accept': 'application/json;odata=verbose',
            'Content-Type': 'application/json;odata=verbose',
            'MaxDataServiceVersion': '3.0',
        }
        if include_x_requested_with:
            headers['X-Requested-With'] = 'X'
        return headers

    def extract_json_payload_from_content(self, content):
        if not isinstance(content, dict) or 'd' not in content:
            raise PyODataException(
                'OData V3 currently supports Verbose JSON only; '
                'expected a top-level "d" envelope in the response payload')

        return content['d']


class Service(_Service):
    """Explicit V3 service type for client/bootstrap routing."""

    REQUEST_POLICY_CLASS = _ODataV3RequestPolicy

    def __init__(self, url, schema, connection, config=None):
        super(Service, self).__init__(url, schema, connection, config=config)
        self._entity_container = EntityContainer(self)
        self._function_container = FunctionContainer(self)


class FunctionRequest(_FunctionRequest):
    """V3 unbound operation request with path-style functions and POST actions."""

    def __init__(self, url, connection, handler, function_import, request_policy=None):
        super(FunctionRequest, self).__init__(
            url, connection, handler, function_import, request_policy=request_policy)
        self._parameters = {}

    @property
    def _ordered_parameters(self):
        return [
            parameter for parameter in self._function_import.parameters
            if not parameter.is_binding_parameter and parameter.name in self._parameters
        ]

    def parameter(self, name, value):
        """Sets value of parameter."""

        try:
            param = self._function_import.get_parameter(name)
        except KeyError:
            raise PyODataException('Function import {0} does not have pararmeter {1}'
                                   .format(self._function_import.name, name))

        if param.is_binding_parameter:
            raise PyODataException(
                f'Bound operation {self._function_import.name} is not available via service.functions')

        if _is_spatial_type(param.typ):
            raise PyODataException(
                f'OData V3 operation parameter {param.name} of type {param.typ.name} is not supported')

        self._parameters[param.name] = value
        return self

    def get_path(self):
        if self._function_import.is_side_effecting:
            return self._function_import.name

        if not self._parameters:
            return self._function_import.name

        arguments = ','.join(
            f'{parameter.name}={parameter.to_literal(self._parameters[parameter.name])}'
            for parameter in self._ordered_parameters)

        return f'{self._function_import.name}({arguments})'

    def get_query_params(self):
        return ODataHttpRequest.get_query_params(self)

    def get_method(self):
        if self._function_import.is_side_effecting:
            return 'POST'

        return self._function_import.http_method

    def get_body(self):
        if not self._function_import.is_side_effecting:
            return None

        if not self._parameters:
            return None

        body = {
            parameter.name: parameter.to_json(self._parameters[parameter.name])
            for parameter in self._ordered_parameters
        }
        return json.dumps(body)

    def get_default_headers(self):
        if self._function_import.is_side_effecting:
            return self._request_policy.json_write_headers()

        return self._request_policy.json_get_headers()


class BoundOperationRequest(FunctionRequest):
    """V3 bound operation request that appends the operation to a binding path."""

    def __init__(self, url, connection, handler, function_import, binding_path, request_policy=None):
        super(BoundOperationRequest, self).__init__(
            url, connection, handler, function_import, request_policy=request_policy)
        self._binding_path = binding_path.rstrip('/')

    @property
    def _operation_segment(self):
        if self._function_import.is_side_effecting and self._function_import.container_name:
            return f'{self._function_import.container_name}.{self._function_import.name}'

        return self._function_import.name

    def get_path(self):
        operation_path = f'{self._binding_path}/{self._operation_segment}'

        if self._function_import.is_side_effecting or not self._parameters:
            return operation_path

        arguments = ','.join(
            f'{parameter.name}={parameter.to_literal(self._parameters[parameter.name])}'
            for parameter in self._ordered_parameters)

        return f'{operation_path}({arguments})'


def _get_response_text(response):
    text = getattr(response, 'text', None)
    if text is not None:
        return text

    content = getattr(response, 'content', None)
    if not content:
        return ''

    if isinstance(content, bytes):
        return content.decode('utf-8')

    return str(content)


def _resolve_entity_set_for_return_type(service, function_import, bound_entity_set):
    if function_import.entity_set_name is not None:
        return service.schema.entity_set(function_import.entity_set_name)

    if bound_entity_set is not None and isinstance(function_import.return_type, model.EntityType):
        if bound_entity_set.entity_type is function_import.return_type:
            return bound_entity_set

    return None


class StreamRequest(ODataHttpRequest):
    """Raw-content request used for V3 media and named stream access."""

    def __init__(self, url, connection, handler, path, method='GET', headers=None, body=None, request_policy=None):
        super(StreamRequest, self).__init__(
            url, connection, handler, headers=headers, request_policy=request_policy)
        self._path = path
        self._method = method
        self._body = body

    def get_path(self):
        return self._path

    def get_method(self):
        return self._method

    def get_body(self):
        return self._body


def _operation_response_handler(service, function_import, response, bound_entity_set=None):
    """Get operation response from HTTP Response."""

    if 300 <= response.status_code < 400:
        raise HttpError(f'Function Import {function_import.name} requires Redirection which is not supported',
                        response)

    if response.status_code == 401:
        raise HttpError(f'Not authorized to call Function Import {function_import.name}',
                        response)

    if response.status_code == 403:
        raise HttpError(f'Missing privileges to call Function Import {function_import.name}',
                        response)

    if response.status_code == 405:
        raise HttpError(
            f'Despite definition Function Import {function_import.name} does not support HTTP '
            f'{function_import.http_method}',
            response)

    if 400 <= response.status_code < 500:
        raise HttpError(
            f'Function Import {function_import.name} call has failed with status code {response.status_code}',
            response)

    if response.status_code >= 500:
        raise HttpError(f'Server has encountered an error while processing Function Import {function_import.name}',
                        response)

    if function_import.return_type is None:
        if response.status_code != 204:
            logging.getLogger(LOGGER_NAME).warning(
                'The No Return Function Import %s has replied with HTTP Status Code %d instead of 204',
                function_import.name, response.status_code)

        response_text = _get_response_text(response)
        if response_text:
            logging.getLogger(LOGGER_NAME).warning(
                'The No Return Function Import %s has returned content:\n%s',
                function_import.name, response_text)

        return None

    if response.status_code != 200:
        logging.getLogger(LOGGER_NAME).warning(
            'The Function Import %s has replied with HTTP Status Code %d instead of 200',
            function_import.name, response.status_code)

    response_data = service.extract_json_payload(response)

    if isinstance(function_import.return_type, model.EntityType):
        entity_set = _resolve_entity_set_for_return_type(service, function_import, bound_entity_set)
        if entity_set is not None:
            return EntityProxy(service, entity_set, function_import.return_type, response_data)

    return response_data


def _stream_response_handler(description, response):
    """Return the raw HTTP response for stream reads."""

    if response.status_code != 200:
        raise HttpError(
            f'HTTP GET for {description} failed with status code {response.status_code}',
            response)

    return response


def _build_stream_read_request(service, path, description, connection=None):
    conn = connection or service.connection

    return StreamRequest(
        service.url,
        conn,
        partial(_stream_response_handler, description),
        path,
        request_policy=service.request_policy)


def _get_declared_named_stream(entity_type, name):
    try:
        proprty = entity_type.proprty(name)
    except KeyError as ex:
        raise PyODataException(
            f'Property {name} is not declared in {entity_type.name} entity type') from ex

    if proprty.type_info.name != 'Edm.Stream':
        raise PyODataException(
            f'Property {name} of {entity_type.name} is not declared as Edm.Stream')

    return proprty


def _validate_media_entity(entity_type):
    if not getattr(entity_type, 'has_stream', False):
        raise PyODataException(f'Entity type {entity_type.name} does not declare HasStream')


def _is_open_entity_type(entity_type):
    return getattr(entity_type, 'is_open_type', False)


def _normalize_dynamic_value(value):
    if isinstance(value, _EntityProxy):
        return value._get_body()  # pylint: disable=protected-access

    if isinstance(value, list):
        return [_normalize_dynamic_value(item) for item in value]

    if isinstance(value, dict):
        return {key: _normalize_dynamic_value(item) for key, item in value.items()}

    return value


def _build_entity_values(entity_type, entity):
    if isinstance(entity, list):
        return [_build_entity_values(entity_type, item) for item in entity]

    values = {}
    for key, val in entity.items():
        try:
            val = entity_type.proprty(key).to_json(val)
        except KeyError:
            try:
                nav_prop = entity_type.nav_proprty(key)
                val = _build_entity_values(nav_prop.typ, val)
            except KeyError as ex:
                if not _is_open_entity_type(entity_type):
                    raise PyODataException(
                        f'Property {key} is not declared in {entity_type.name} entity type') from ex

                val = _normalize_dynamic_value(val)

        values[key] = val

    return values


def _cache_dynamic_properties(cache, entity_type, proprties):
    if proprties is None or not _is_open_entity_type(entity_type):
        return

    for key, value in proprties.items():
        if key == '__metadata':
            continue

        if entity_type.has_proprty(key):
            continue

        try:
            entity_type.nav_proprty(key)
            continue
        except KeyError:
            cache[key] = value


class _BoundOperationTargetMixin:
    """Shared V3-bound operation access for entity and entity-set contexts."""

    def _get_bound_operation_context(self):
        raise NotImplementedError

    def _get_bound_operation_container(self, is_side_effecting):
        cache_name = '_bound_action_container' if is_side_effecting else '_bound_function_container'
        container = getattr(self, cache_name, None)
        if container is None:
            binding_path, entity_set, entity_type, is_collection = self._get_bound_operation_context()
            container = BoundOperationContainer(
                self._service,
                binding_path,
                entity_set,
                entity_type,
                is_collection,
                is_side_effecting)
            setattr(self, cache_name, container)

        return container

    @property
    def functions(self):
        return self._get_bound_operation_container(False)

    @property
    def actions(self):
        return self._get_bound_operation_container(True)


class EntityGetRequest(_BoundOperationTargetMixin, _EntityGetRequest):
    """V3 entity request that also exposes bound operations."""

    @property
    def _service(self):
        return self._entity_set_proxy.service

    def _get_bound_operation_context(self):
        return (
            self._entity_set_proxy.last_segment + self._entity_key.to_key_string(),
            self._entity_set_proxy._entity_set,  # pylint: disable=protected-access
            self._entity_set_proxy._entity_set.entity_type,  # pylint: disable=protected-access
            False,
        )

    def media_stream(self, connection=None):
        entity_type = self._entity_set_proxy._entity_set.entity_type  # pylint: disable=protected-access
        _validate_media_entity(entity_type)

        path = urljoin(self.get_path(), '/$value')
        return _build_stream_read_request(self._service, path, f'$value of Entity {self.get_path()}', connection)

    def named_stream(self, name, connection=None):
        entity_type = self._entity_set_proxy._entity_set.entity_type  # pylint: disable=protected-access
        _get_declared_named_stream(entity_type, name)

        path = urljoin(self.get_path(), name)
        return _build_stream_read_request(
            self._service,
            path,
            f'named stream {name} of Entity {self.get_path()}',
            connection)


class EntityProxy(_BoundOperationTargetMixin, _EntityProxy):
    """V3 entity proxy with bound operations available from entity instances."""

    def __init__(self, service, entity_set, entity_type, proprties=None, entity_key=None, etag=None):
        super(EntityProxy, self).__init__(service, entity_set, entity_type, proprties, entity_key=entity_key, etag=etag)
        _cache_dynamic_properties(self._cache, self._entity_type, proprties)  # pylint: disable=protected-access

    def _get_bound_operation_context(self):
        return self.get_path(), self._entity_set, self._entity_type, False

    def media_stream(self, connection=None):
        _validate_media_entity(self._entity_type)

        path = urljoin(self.get_path(), '/$value')
        return _build_stream_read_request(self._service, path, f'$value of Entity {self.get_path()}', connection)

    def named_stream(self, name, connection=None):
        _get_declared_named_stream(self._entity_type, name)

        path = urljoin(self.get_path(), name)
        return _build_stream_read_request(
            self._service,
            path,
            f'named stream {name} of Entity {self.get_path()}',
            connection)


class EntitySetProxy(_BoundOperationTargetMixin, _EntitySetProxy):
    """V3 entity-set proxy with collection-bound operations."""

    def _get_bound_operation_context(self):
        return self.last_segment, self._entity_set, self._entity_set.entity_type, True

    def get_entity(self, key=None, encode_path=True, **args):
        """Get entity based on provided key properties."""

        def get_entity_handler(response):
            if response.status_code != 200:
                raise HttpError('HTTP GET for Entity {0} failed with status code {1}'
                                .format(self._name, response.status_code), response)

            entity = self._service.extract_json_payload(response)
            etag = response.headers.get('ETag', None)

            return EntityProxy(self._service, self._entity_set, self._entity_set.entity_type, entity, etag=etag)

        if key is not None and isinstance(key, EntityKey):
            entity_key = key
        else:
            entity_key = EntityKey(self._entity_set.entity_type, key, **args)

        self._logger.info('Getting entity %s for key %s and args %s', self._entity_set.entity_type.name, key, args)

        return EntityGetRequest(get_entity_handler, entity_key, self, encode_path=encode_path)

    def get_entities(self, encode_path=True):
        """Get some, potentially all entities."""

        def get_entities_handler(response):
            if response.status_code != HTTP_CODE_OK:
                raise HttpError('HTTP GET for Entity Set {0} failed with status code {1}'
                                .format(self._name, response.status_code), response)

            content = response.json()

            if isinstance(content, int):
                return content

            entities = self._service.extract_json_payload_from_content(content)
            total_count = None
            next_url = None

            if isinstance(entities, dict):
                if '__count' in entities:
                    total_count = int(entities['__count'])
                if '__next' in entities:
                    next_url = entities['__next']
                entities = entities['results']

            self._logger.info('Fetched %d entities', len(entities))

            result = ListWithTotalCount(total_count, next_url)
            for props in entities:
                entity = EntityProxy(self._service, self._entity_set, self._entity_set.entity_type, props)
                result.append(entity)

            return result

        entity_set_name = self._alias if self._alias is not None else self._entity_set.name
        return GetEntitySetRequest(self._service.url, self._service.connection, get_entities_handler,
                                   self._parent_last_segment + entity_set_name, self._entity_set.entity_type,
                                   request_policy=self._service.request_policy,
                                   encode_path=encode_path)

    def create_entity(self, return_code=HTTP_CODE_CREATED):
        """Creates a new entity in the given entity-set."""

        def create_entity_handler(response):
            if response.status_code != return_code:
                raise HttpError('HTTP POST for Entity Set {0} failed with status code {1}'
                                .format(self._name, response.status_code), response)

            entity_props = self._service.extract_json_payload(response)
            etag = response.headers.get('ETag', None)

            return EntityProxy(self._service, self._entity_set, self._entity_set.entity_type, entity_props, etag=etag)

        return EntityCreateRequest(self._service.url, self._service.connection, create_entity_handler, self._entity_set,
                                   self.last_segment, request_policy=self._service.request_policy)

    def update_entity(self, key=None, method=None, encode_path=True, **kwargs):
        """Updates an existing entity in the given entity-set."""

        def update_entity_handler(response):
            if response.status_code != 204:
                raise HttpError('HTTP modify request for Entity Set {} failed with status code {}'
                                .format(self._name, response.status_code), response)

        if key is not None and isinstance(key, EntityKey):
            entity_key = key
        else:
            entity_key = EntityKey(self._entity_set.entity_type, key, **kwargs)

        self._logger.info('Updating entity %s for key %s and args %s', self._entity_set.entity_type.name, key, kwargs)

        if method is None:
            method = self._service.config['http']['update_method']

        return EntityModifyRequest(self._service.url, self._service.connection, update_entity_handler, self._entity_set,
                                   entity_key, method=method, encode_path=encode_path,
                                   request_policy=self._service.request_policy)


class EntityCreateRequest(_EntityCreateRequest):
    """V3 entity create request with open-type write support."""

    def set(self, **kwargs):
        self._logger.info(kwargs)
        self._values = _build_entity_values(self._entity_type, kwargs)
        return self


class EntityModifyRequest(_EntityModifyRequest):
    """V3 entity update request with open-type write support."""

    def set(self, **kwargs):
        self._logger.info(kwargs)

        for key, val in kwargs.items():
            try:
                val = self._entity_type.proprty(key).to_json(val)
            except KeyError as ex:
                if not _is_open_entity_type(self._entity_type):
                    raise PyODataException(
                        f'Property {key} is not declared in {self._entity_type.name} entity type') from ex

                val = _normalize_dynamic_value(val)

            self._values[key] = val

        return self


class EntityContainer(_EntityContainer):
    """Set of V3 entity-set proxies."""

    def __init__(self, service):
        self._service = service
        self._entity_sets = dict()

        for entity_set in self._service.schema.entity_sets:
            self._entity_sets[entity_set.name] = EntitySetProxy(self._service, entity_set)


class BoundOperationContainer:
    """V3 bindable operation surface for a specific entity or collection context."""

    def __init__(self, service, binding_path, entity_set, entity_type, is_collection, is_side_effecting):
        self._service = service
        self._binding_path = binding_path
        self._entity_set = entity_set
        self._entity_type = entity_type
        self._is_collection = is_collection
        self._is_side_effecting = is_side_effecting
        self._operations = dict()

        for function_import in self._service.schema.function_imports:
            if self._matches_binding_context(function_import):
                self._operations[function_import.name] = function_import

    def _matches_binding_context(self, function_import):
        if not function_import.is_bindable or function_import.is_side_effecting != self._is_side_effecting:
            return False

        binding_parameter = function_import.binding_parameter
        if binding_parameter is None or binding_parameter.typ is None:
            return False

        if binding_parameter.typ.is_collection != self._is_collection:
            return False

        bound_type = binding_parameter.typ.item_type if binding_parameter.typ.is_collection else binding_parameter.typ
        return bound_type is self._entity_type

    def __getattr__(self, name):
        if name not in self._operations:
            raise AttributeError(
                f"Function {name} not defined in {','.join(list(self._operations.keys()))}.")

        function_import = self._operations[name]
        handler = partial(_operation_response_handler, self._service, function_import,
                          bound_entity_set=self._entity_set)

        return BoundOperationRequest(
            self._service.url,
            self._service.connection,
            handler,
            function_import,
            self._binding_path,
            request_policy=self._service.request_policy)


class FunctionContainer(_FunctionContainer):
    """V3 unbound operation surface backed by FunctionImport metadata."""

    def __init__(self, service):
        self._service = service
        self._functions = dict()

        for fimport in self._service.schema.function_imports:
            if not fimport.is_bindable:
                self._functions[fimport.name] = fimport

    def __getattr__(self, name):

        if name not in self._functions:
            raise AttributeError(
                f"Function {name} not defined in {','.join(list(self._functions.keys()))}.")

        function_import = self._service.schema.function_import(name)
        handler = partial(_operation_response_handler, self._service, function_import)

        return FunctionRequest(self._service.url, self._service.connection,
                               handler, function_import,
                               request_policy=self._service.request_policy)
