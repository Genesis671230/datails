"""Connector registry — the single place that knows which module implements
which connector type.

This is the ONLY module outside integrations/<vendor>/ that may import
vendor-specific code (Slice 1 genericity criterion). Adding a connector:
write integrations/<name>/, add one entry here. Nothing else changes.
"""

from app.db.models.enums import ConnectorType
from app.integrations.crystal.client import CrystalConnector
from app.integrations.generic_api.base import ConnectorClient, MockConnector

_CLIENTS: dict[ConnectorType, ConnectorClient] = {
    ConnectorType.CRYSTAL: CrystalConnector(),
    ConnectorType.GENERIC_API: MockConnector(),
    # ConnectorType.BLOCKCHAIN_EXPLORER: vendor selected in the LD-6 spike (LD-15)
    # ConnectorType.MCP_SERVER: post-pilot Connector Platform milestone
}


def get_connector_client(connector_type: ConnectorType) -> ConnectorClient:
    client = _CLIENTS.get(connector_type)
    if client is None:
        raise ValueError(f"no client implemented for connector type {connector_type.value!r}")
    return client
