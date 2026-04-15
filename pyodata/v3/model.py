"""OData V3 metadata facade backed by the shared parser implementation."""

from pyodata.v2.model import *  # noqa: F401,F403
from pyodata.v2.model import Config as _Config
from pyodata.v2.model import ParserError, PolicyIgnore


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
