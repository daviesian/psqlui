# Plugin Development Guide

Quick reference for building third-party plugins against the current `psqlui` contract.

## Packaging
- Ship a Python package that exposes an entry point under `psqlui.plugins`.
- The entry point should resolve to a class implementing `PluginDescriptor`.
- During development you can also place modules under `examples/plugins` and pass them to the loader as built-ins.

## Descriptor Contract
```python
class PluginDescriptor(Protocol):
    name: str
    version: str
    min_core: str

    def register(self, ctx: PluginContext) -> Sequence[CapabilitySpec]: ...
    async def on_shutdown(self) -> None: ...
```
- `PluginContext` currently exposes `app`, `sql_intel`, and `config` instances; treat them as read-only.
- `CapabilitySpec` can be a `CommandCapability`, `PaneCapability`, `ExporterCapability`, `MetadataHookCapability`, or `SqlAssistCapability`.

## Capabilities Today
- **Commands** feed the `PluginCommandRegistry` and show up in the Textual command palette automatically.
- **Panes** return ready-to-mount Textual widgets. They render in the sidebar as soon as the plugin is loaded.
- Additional capability types (exporters, metadata hooks, SQL assistants) share the same registration model even if the UI glue is landing later in Milestone 3.

## Configuration & Enablement
- User preferences live in `~/.config/psqlui/config.toml`.
- `[plugins]` acts as an overrides table. Missing entries default to enabled; setting `plugin-name = false` disables the plugin; removing the key re-enables it.
- The “Plugin toggles” command palette provider lets users persist enable/disable flags without editing the file manually (restart required at the moment).

## Testing
- Use `tests/plugins/test_loader.py` and `tests/plugins/test_app_integration.py` as references for patching `importlib.metadata.entry_points`.
- Future third-party packages should create their own testkit by instantiating `PluginContext` with stubs and asserting on returned capabilities.
