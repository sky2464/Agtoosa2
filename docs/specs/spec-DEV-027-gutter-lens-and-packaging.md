# Specification: DEV-027 In-Editor Gutter Lens, 1-Click Refactoring & Marketplace Packaging

## Status
Approved / In Progress

## Priority Score
**89 / 100** (High Impact — Direct Developer In-Editor Experience in VS Code & Cursor + Global Marketplace Distribution)

## Problem Statement
Developers spend most of their time in the editor (VS Code, Cursor, Windsurf). While Agtoosa provides powerful CLI, MCP, and Studio tools, forcing developers to switch windows or manually query the CLI reduces adoption. Furthermore, without a packaged `.vsix` and automated marketplace pipeline, teams cannot easily install the extension across organizations.

## Objectives
1. **Live In-Editor CodeLens & Gutter Overlays**:
   - Expand `AgtoosaCodeLensProvider` with real-time upstream caller badges: `⎇ N callers | 💥 blast radius: X`.
   - Add `AgtoosaGutterDecorator`: Queries `agtoosa telemetry --json` to apply gutter decoration badges on symbols (🔥 Hot execution path, ⚠️ High error rate, ❄️ Cold/Dormant).
2. **1-Click QuickFix Refactoring (VS Code CodeActionProvider)**:
   - Register `AgtoosaCodeActionProvider` implementing `vscode.CodeActionKind.QuickFix`:
     - **"✂️ Agtoosa: Safe Prune Dead Symbol"**: Invokes `agtoosa refactor dead-code --clean` with automatic atomic rollback backup.
     - **"🔄 Agtoosa: Decouple Cyclic Dependency"**: Invokes `agtoosa refactor decouple`.
     - **"🛡️ Agtoosa: Inspect Blast Radius"**: Focuses blast radius view.
3. **Guard Daemon & Pre-Push In-Editor Status Bar**:
   - Status bar item dynamically polls `.agtoosa/guard_status.json` or runs lightweight checks to display:
     - `$(shield) Agtoosa: Clean` when invariants hold.
     - `$(alert) Agtoosa: N Drift Alarms` when architectural drift is detected.
4. **Packaging & Marketplace Distribution Pipeline**:
   - Update `extension/package.json` to v0.5.0 with full command/codeaction contributions.
   - Create `extension/.vscodeignore` to exclude development artifacts.
   - Create `scripts/build_extension.py` that validates package manifest, assets, and packages the extension into `.vsix`.
   - Create GitHub Actions workflow `.github/workflows/marketplace-release.yml` automating releases to VS Code Marketplace and Open VSX.
5. **Testing & Verification**:
   - Automated tests in `tests/test_extension.py` verifying CodeAction providers, CodeLens formats, gutter logic, and VSIX packaging integrity.

## Architecture

```
[ VS Code / Cursor Editor ]
   │
   ├── CodeLens Provider (⎇ Callers | 💥 Blast Radius)
   ├── Gutter Decoration Provider (🔥 Hot / ⚠️ Error / ❄️ Cold)
   ├── CodeAction Provider ("✂️ Prune Dead Symbol", "🔄 Decouple Cycle")
   └── Status Bar Item (Live Guard & Drift Status)
              │
              ▼
    [ Agtoosa CLI Engine ]
   (agtoosa graph / telemetry / refactor / guard)
```

## Verification Plan
- Unit and integration tests in `tests/test_extension.py`.
- Run VSIX package builder script.
- Ensure all 169+ repository unit tests pass.
