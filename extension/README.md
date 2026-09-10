# Agtoosa for VS Code & Cursor IDE

Zero-dependency architecture intelligence, real-time caller blast radius, drift alarms, and C4 visualizer navigation directly inside your editor.

![Agtoosa Architecture Command Center](https://img.shields.io/badge/Agtoosa-Architecture_OS-3b82f6?style=for-the-badge&logo=visualstudiocode&logoColor=white)

---

## Features

### 1. Real-Time Inline CodeLens & Blast Radius
Every class and function in supported languages (Python, TypeScript, JavaScript, Go, Rust, Java, C++, C#, SQL) displays inline caller intelligence:
```
🏛️ 8 callers | Blast Radius: HIGH
def evaluate_review(self, modified_files):
```
Clicking the CodeLens opens the **Active Blast Radius** tree in the sidebar to trace all upstream callers up to 3 hops deep.

### 2. Architecture Tiers & Stories Navigator
The sidebar displays your Clean Architecture domain hierarchy:
- **Tier 1**: Presentation & Entrypoints (`cli`, `mcp`)
- **Tier 2**: Application Services & Engines (`parser`, `graph`, `watcher`, `review`)
- **Tier 3**: Domain Core & Security Foundations (`core/model`, `core/security`)
- **User Stories & Requirements**: Live status of delivery milestones (`DEV-001` through `DEV-013`).
- **Institutional Architectural Memory Bank**: Live display of all design invariants stored via `agtoosa review remember`.

### 3. Architecture Drift Alarms & CI Pre-Flight
Run pre-flight checks directly before committing code:
- Detects circular dependency cycles introduced into the graph.
- Flags layer boundary violations (e.g. low-level models importing CLI presentation logic).
- Warns on high-impact modifications ($\ge 5$ upstream callers).

### 4. Interactive C4 Architecture Command Center
Click the status bar item `$(shield) Agtoosa: Ready` or run `Agtoosa: Open Architecture Command Center` to instantly open the visual Cytoscape.js C4 studio.

---

## Commands

| Command | Description |
|---|---|
| `Agtoosa: Rebuild Knowledge Graph` | Rebuilds SQLite knowledge graph from workspace source files. |
| `Agtoosa: Open Architecture Command Center` | Opens standalone offline C4 architecture visualizer. |
| `Agtoosa: Run Architecture Drift Review` | Checks working tree for cyclic dependencies and layer inversions. |
| `Agtoosa: Inspect Symbol Blast Radius` | Calculates upstream blast radius for any symbol or file. |
| `Agtoosa: Remember Architectural Rule` | Records a new architectural invariant into project memory. |

---

## Configuration

In `settings.json`:
```json
{
  "agtoosa.executablePath": "agtoosa",
  "agtoosa.enableCodeLens": true,
  "agtoosa.enableDiagnostics": true,
  "agtoosa.maxBlastRadiusDepth": 3
}
```
