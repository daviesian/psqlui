"""Shared dataclasses used across connection/session modules."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

MetadataSnapshot = Mapping[str, tuple[str, ...]]


@dataclass(frozen=True, slots=True)
class ConnectionProfile:
    """Runtime representation of a connection profile."""

    name: str
    dsn: str | None = None
    host: str | None = None
    port: int | None = None
    database: str | None = None
    user: str | None = None
    metadata_key: str | None = None
    metadata: MetadataSnapshot | None = None


__all__ = ["ConnectionProfile", "MetadataSnapshot"]
