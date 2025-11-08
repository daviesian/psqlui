# Plugin Contract

Defines how optional extensions integrate with the core TUI while keeping the base runtime lean and predictable.

## Goals
- Allow community/custom teams to add panes, commands, exporters, or data integrations without forking the app.
- Keep plugins discoverable (`uv` extras / entry points) and hot-loadable at runtime.
- Provide a stable, typed interface that shields core internals while exposing the primitives third parties need.

## Non-Goals
- Enforcing strict sandboxing or process isolation in v1 (plugins run in-process; trust boundary is the user).
- Supporting closed-source/commercial license enforcement within the plugin manager.
- Plugin-driven background daemons; everything executes within the foreground app lifecycle.

## Packaging & Discovery
- Plugins are Python packages that declare an entry point group `psqlui.plugins`.
- Each entry point exposes a subclass of `PluginDescriptor` with metadata (name, version, capabilities, minimum-core-version).
- Users install plugins via `uv tool install psqlui[extras]` or `uv pip install <plugin>` and enable/disable them in config.

## Lifecycle
1. **Startup**: core loader enumerates entry points, validates semver compatibility, and constructs dependency graph.
2. **Registration**: plugin descriptor advertises capabilities (panes, commands, exporters, hooks). Loader wires them into the event bus.
3. **Activation**: when a capability is requested (e.g., user opens plugin pane), the loader instantiates the plugin class inside an `anyio` task group.
4. **Deactivation**: plugins receive `on_shutdown` before app exit or when disabled mid-session; they must release resources synchronously.

## Capability Matrix
| Capability | Description | Key Interfaces |
|------------|-------------|----------------|
| `Pane` | Contribute a Textual `Screen`/`Widget` mounted in a region (main stack, sidebar drawer, modal). | `PaneProvider.mount(ctx)` returning widget + keymaps. |
| `Command` | Register palette actions or colon commands (`:explain`, `:export csv`). | `CommandProvider.list_commands()` returning `CommandSpec` objects. |
| `Exporter` | Transform query results to formats (CSV, Parquet, clipboard). | `Exporter.handle(result_set, options)` async generator. |
| `MetadataHook` | Enrich schema metadata (e.g., comment fetchers). | `MetadataProvider.fetch(connection, scope)` coroutine. |
| `SqlAssist` | Consume `SqlIntelService` output to offer specialized flows (e.g., explain visualizer). | Read-only access to `AnalysisResult` + ability to request re-parse. |

Plugins can opt into multiple capabilities by implementing mixin interfaces.

## Core APIs
```python
class PluginContext(NamedTuple):
    app: "PsqluiApp"
    event_bus: "EventBus"
    sql_intel: "SqlIntelService"
    metadata_cache: "MetadataCache"
    config: "ConfigStore"

class PluginDescriptor(Protocol):
    name: str
    version: str
    min_core: str

    def register(self, ctx: PluginContext) -> list[Capability]: ...
    async def on_shutdown(self) -> None: ...
```
- Context exposes read-only accessors; mutations happen through public services (command bus, metadata updates) to avoid tight coupling.
- Capabilities are dataclasses describing routes/commands; loader takes ownership of wiring them into UI + domain layers.

## Configuration
- `.psqlui/config.toml` includes `[plugins]` section for enablement flags and optional per-plugin config tables.
- Plugins read config via `ctx.config.get_plugin_section("my_plugin")` to avoid direct filesystem access.

## Error Handling
- Plugin exceptions bubble to loader, which logs them and surfaces a toast/modal without killing the app.
- Misbehaving plugins can be auto-disabled for the session; user prompted to re-enable later.
- Long-running plugin tasks should use `anyio` cancellation scopes tied to the app shutdown to avoid orphan coroutines.

## Security & Trust
- Plugins execute with the same privileges as the user. Document this clearly; no sandbox in v1.
- Encourage best practices: avoid credential logging, respect redaction APIs, honor cancellation.
- Provide signing hooks later if community demands, but not part of the initial contract.

## Testing Strategy
- Provide a `psqlui-plugin-testkit` module with fake `PluginContext`, in-memory event bus, and stub metadata cache.
- Offer contract tests to ensure plugins implement required methods and declare semver compatibility correctly.

## Decision Log
- Entry points (`psqlui.plugins`) are the discovery mechanism; no custom manifest format.
- Plugins run in-process with read-only access to core services; isolation/postMessage-style APIs deferred.
- Advanced UX (explain visualizer, SSH tunnels, telemetry exporters) must ship as plugins using this contract.
