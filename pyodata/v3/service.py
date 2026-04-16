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
    EntityGetRequest as _EntityGetRequest,
    EntityProxy as _EntityProxy,
    EntitySetProxy as _EntitySetProxy,
    FunctionContainer as _FunctionContainer,
    FunctionRequest as _FunctionRequest,
    ODataHttpRequest,
    Service as _Service,
    _ODataRequestPolicy,
)


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


class EntityProxy(_BoundOperationTargetMixin, _EntityProxy):
    """V3 entity proxy with bound operations available from entity instances."""

    def _get_bound_operation_context(self):
        return self.get_path(), self._entity_set, self._entity_type, False


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
