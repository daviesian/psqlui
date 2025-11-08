"""Plugin loader exports."""

from .loader import LoadedPlugin, PluginLoader
from .registry import PluginCommandRegistry
from .types import (
    CapabilitySpec,
    CommandCapability,
    ExporterCapability,
    MetadataHookCapability,
    PaneCapability,
    PluginCompatibilityError,
    PluginContext,
    PluginDescriptor,
    PluginError,
    SqlAssistCapability,
)

__all__ = [
    "CapabilitySpec",
    "CommandCapability",
    "ExporterCapability",
    "LoadedPlugin",
    "MetadataHookCapability",
    "PaneCapability",
    "PluginCompatibilityError",
    "PluginCommandRegistry",
    "PluginContext",
    "PluginDescriptor",
    "PluginError",
    "PluginLoader",
    "SqlAssistCapability",
]
