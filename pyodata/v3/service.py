"""OData V3 service facade backed by the shared request implementation."""

from pyodata.v2.service import *  # noqa: F401,F403
from pyodata.v2.service import Service as _Service


class Service(_Service):
    """Explicit V3 service type for client/bootstrap routing."""
