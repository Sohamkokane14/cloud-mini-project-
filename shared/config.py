"""Configuration helpers for mock, local, and Azure-hosted execution."""

from __future__ import annotations

import os
from functools import lru_cache


APP_MODE = os.getenv("APP_MODE", "mock").strip().lower()
if APP_MODE not in {"mock", "local", "cloud"}:
    raise RuntimeError("APP_MODE must be one of: mock, local, cloud")

_ENVIRONMENT_NAMES = {
    "SqlConnectionString": "SQL_CONNECTION_STRING",
    "StorageConnectionString": "STORAGE_CONNECTION_STRING",
    "VisionEndpoint": "VISION_ENDPOINT",
    "VisionKey": "VISION_KEY",
    "AdminPasswordHash": "ADMIN_PASSWORD_HASH",
}


@lru_cache(maxsize=1)
def _key_vault_client():
    """Create the Azure Key Vault client only when cloud mode needs it."""
    vault_url = os.getenv("KEY_VAULT_URL", "").strip()
    if not vault_url:
        raise RuntimeError("KEY_VAULT_URL is required when APP_MODE=cloud")
    try:
        from azure.identity import DefaultAzureCredential
        from azure.keyvault.secrets import SecretClient
    except ImportError as error:
        raise RuntimeError("Azure Key Vault packages are not installed") from error
    return SecretClient(vault_url=vault_url, credential=DefaultAzureCredential())


def get_secret(name: str) -> str:
    """Return a named secret without ever logging its value.

    Mock mode deliberately returns an empty string. Local mode reads the
    conventional environment variable; cloud mode reads the corresponding
    Azure Key Vault secret through managed identity.
    """
    if APP_MODE == "mock":
        return ""
    if APP_MODE == "cloud":
        value = _key_vault_client().get_secret(name).value
    else:
        value = os.getenv(_ENVIRONMENT_NAMES.get(name, name), "")
    if not value:
        raise RuntimeError(f"Required configuration value is missing: {name}")
    return value
