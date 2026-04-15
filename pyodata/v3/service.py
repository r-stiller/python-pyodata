"""OData V3 service facade backed by the shared request implementation."""

from pyodata.v2.service import *  # noqa: F401,F403
from pyodata.exceptions import PyODataException
from pyodata.v2.service import Service as _Service, _ODataRequestPolicy


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
