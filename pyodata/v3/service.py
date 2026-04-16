"""OData V3 service facade backed by the shared request implementation."""

import json
import logging
from functools import partial

from pyodata.v2 import model
from pyodata.v2.service import *  # noqa: F401,F403
from pyodata.exceptions import HttpError, PyODataException
from pyodata.v2.service import (
    LOGGER_NAME,
    EntityProxy,
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


class FunctionContainer(_FunctionContainer):
    """V3 unbound operation surface backed by FunctionImport metadata."""

    def __init__(self, service):
        self._service = service
        self._functions = dict()

        for fimport in self._service.schema.function_imports:
            if not fimport.is_bindable:
                self._functions[fimport.name] = fimport

    @staticmethod
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

    def __getattr__(self, name):

        if name not in self._functions:
            raise AttributeError(
                f"Function {name} not defined in {','.join(list(self._functions.keys()))}.")

        fimport = self._service.schema.function_import(name)

        def function_import_handler(fimport, response):
            """Get operation response from HTTP Response."""

            if 300 <= response.status_code < 400:
                raise HttpError(f'Function Import {fimport.name} requires Redirection which is not supported',
                                response)

            if response.status_code == 401:
                raise HttpError(f'Not authorized to call Function Import {fimport.name}',
                                response)

            if response.status_code == 403:
                raise HttpError(f'Missing privileges to call Function Import {fimport.name}',
                                response)

            if response.status_code == 405:
                raise HttpError(
                    f'Despite definition Function Import {fimport.name} does not support HTTP {fimport.http_method}',
                    response)

            if 400 <= response.status_code < 500:
                raise HttpError(
                    f'Function Import {fimport.name} call has failed with status code {response.status_code}',
                    response)

            if response.status_code >= 500:
                raise HttpError(f'Server has encountered an error while processing Function Import {fimport.name}',
                                response)

            if fimport.return_type is None:
                if response.status_code != 204:
                    logging.getLogger(LOGGER_NAME).warning(
                        'The No Return Function Import %s has replied with HTTP Status Code %d instead of 204',
                        fimport.name, response.status_code)

                response_text = self._get_response_text(response)
                if response_text:
                    logging.getLogger(LOGGER_NAME).warning(
                        'The No Return Function Import %s has returned content:\n%s',
                        fimport.name, response_text)

                return None

            if response.status_code != 200:
                logging.getLogger(LOGGER_NAME).warning(
                    'The Function Import %s has replied with HTTP Status Code %d instead of 200',
                    fimport.name, response.status_code)

            response_data = self._service.extract_json_payload(response)

            if isinstance(fimport.return_type, model.EntityType):
                entity_set = self._service.schema.entity_set(fimport.entity_set_name)
                return EntityProxy(self._service, entity_set, fimport.return_type, response_data)

            return response_data

        return FunctionRequest(self._service.url, self._service.connection,
                               partial(function_import_handler, fimport), fimport,
                               request_policy=self._service.request_policy)
