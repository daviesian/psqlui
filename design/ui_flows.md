# UI Flows

## Navigation Model
- Global layout: left sidebar (connections + objects), main content stack (query/grid/forms), bottom status bar.
- Keyboard-centric: `Tab` cycles panes, `Ctrl+P` opens command palette, `:` enters command-line mode.
- Breadcrumbs show current context (cluster › db › schema › table) and allow quick jumps.
- Mouse interactions (click, scroll, drag-resize) mirror the keyboard affordances so casual users can explore without memorizing shortcuts.

## Primary Screens
1. **Connection Hub**
   - List of saved profiles + recent URIs.
   - Inline indicators for availability (success/last failure time).
   - Actions: connect, edit profile, duplicate, delete.
2. **Schema Explorer**
   - Tree view with lazy loading for schemas/tables/views/functions.
   - Metadata panel: row counts, size, owner, indexes.
   - Shortcut to open query pad scoped to selection.
3. **Query Pad**
   - Editor with syntax highlighting, query snippets, and result split view.
   - Execution options: run selection, run file, explain/analyze.
   - History drawer for re-running/editing previous statements.
4. **Data Grid / Edit Mode**
   - Pageable grid with sticky header and cell search.
   - Enter edit mode to modify rows via form or inline; wrap edits in explicit transactions.
   - Show generated SQL diff before commit.
5. **Session Monitor**
   - Active connections, locks, blocking chains.
   - Quick actions: cancel backend PID, view query text, copy diagnostic SQL.

## Cross-cutting Interactions
- **Command Palette**: fuzzy finder for commands, connections, bookmarks; fed by local SQL-intel context for autocomplete.
- **Notifications**: non-blocking toast area, promoting errors to modal if destructive.
- **Themes**: preset themes (light/dark/high contrast) with runtime switch.
- **Help Overlay**: keymap cheatsheet + quickstart walkthrough on first run.
- **Layout memory**: persist the last pane arrangement between runs so the workspace feels stable without managing named profiles.

## Accessibility
- Ensure focus indicators on all widgets.
- Provide configurable keybindings and font sizes (if terminal supports ligatures/Unicode fallback).
- Consider screen-reader hints by emitting minimal descriptive text for major actions.

## Decision Log
- Mouse support (click to focus, drag to resize, scroll in grids) ships in v1 alongside keyboard flows.
- We remember only the most recent layout per user; no multiple saved profiles in the first release.
- No embedded scripting console—the CLI remains the automation surface while plugins cover advanced workflows.
