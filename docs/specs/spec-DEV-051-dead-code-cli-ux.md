# Spec: DEV-051 — Human-Centric Dead-Code CLI Formatting & Progressive Dry-Run Preview

> **Story ID:** DEV-051  
> **Milestone:** Milestone 17 (Developer Experience & Contextual Intelligence — DX-02)  
> **Status:** 📋 Ready for Implementation  
> **Impact Rating:** 92 / 100  
> **Research Basis:** Developer UX feedback & CLI usability audit (unbounded 550+ lines raw diff dump & repetitive per-symbol boilerplate makes `agtoosa refactor dead-code --dry-run` overwhelming and hard to parse)  
> **Dependencies:** DEV-020 (Dead Code Pruning), DEV-044 (Verified Repair Actions), DEV-050 (Actionable Architecture Hints)  
> **Spec Created:** 2026-09-14  

---

## 1. Requirements & Goal Contract

### Problem Statement
Running `agtoosa refactor dead-code --dry-run` currently generates over 550 lines of unformatted, dense terminal output:
1. **Boilerplate Repetition**: For every flagged zombie symbol, 5 verbose bullet points of deletion instructions (`grep -rn ...`, `Review downstream callees...`, etc.) are printed, repeating identical advice dozens of times.
2. **Unbounded Raw Diff Dump**: The `--dry-run` flag immediately streams complete, uncollapsible unified diffs (`--- a/... +++ b/...`) across all affected files to standard output.
3. **Missing Executive Scannability**: Developers and tech leads cannot quickly answer:
   - *How many symbols and files are affected?*
   - *Which symbols are safe internal helpers vs. public exports needing manual review?*
   - *What exact lines would change?*
   - *What exact command should be executed next?*

### User Stories
- **US-1**: As an engineer or tech lead running `agtoosa refactor dead-code --dry-run`, I want a concise executive summary and an aligned candidate table so I can see what was detected at a glance within a single terminal viewport.
- **US-2**: As a developer previewing dead-code removal, I want a Git-style diffstat summary (files affected, lines changed) by default, rather than hundreds of lines of raw unified diffs.
- **US-3**: As an engineer who needs line-by-line verification, I want an explicit `--diff` flag to display full unified diffs on demand, and a `-v` / `--verbose` flag to inspect symbol-specific deletion rationale.
- **US-4**: As an AI coding agent or CI runner, I want `--json` to output structured metadata with machine-readable confidence scores, candidate nodes, and patch plans.

### Acceptance Criteria (EARS)
- **AC-1 (Executive Summary & Single-Screen Scannability)**: WHEN `agtoosa refactor dead-code` (with or without `--dry-run`) is run without `--verbose`, the output SHALL present a high-level summary banner (total analyzed, candidates found, estimated pruneable lines, confidence breakdown) followed by a compact, aligned table of candidate symbols (Confidence, Node Type, Symbol Name, File:Line, Estimated Lines, Safety Status).
- **AC-2 (Progressive Diffstat Preview in Dry-Run)**: WHEN `--dry-run` is provided without `--diff`, the CLI SHALL print a Git-style diffstat preview showing each affected file and line reductions (e.g. `path/to/file.py | -13 ━━━━━━━━━━`), accompanied by a total impact line. It SHALL NOT dump full unified diff text by default.
- **AC-3 (Explicit Unified Diff Gate)**: WHEN `--dry-run` is combined with `--diff`, the engine SHALL output the full unified diff blocks for each affected file after the diffstat summary.
- **AC-4 (Symbol Step Suppression & Verbose Mode)**: WHEN `--verbose` (or `-v`) is absent, individual multi-step deletion instructions SHALL NOT be printed for each symbol. WHEN `--verbose` is passed, symbol-specific step-by-step guidance and rationale SHALL be displayed.
- **AC-5 (Guided Next-Steps Integration)**: The terminal output SHALL conclude with explicit next-step commands tailored to the findings (e.g., viewing diffs, filtering by confidence, applying pruning with auto-rollback backup, or exporting JSON).

---

## 2. Terminal Layout & Progressive Disclosure Design

### 2.1 Default Terminal Output Mockup (`agtoosa refactor dead-code --dry-run`)

```text
🧹 Agtoosa Architecture: Dead Code & Zombie Symbol Analysis
════════════════════════════════════════════════════════════════════════════════

📊 Analysis Summary:
   • Total Symbols Analyzed:   1,420
   • Dead Candidates Detected: 28 (13 High, 9 Medium, 6 Low)
   • Estimated Removable Code: 412 lines across 11 files

🔍 Candidates Breakdown:
   CONFIDENCE  TYPE      SYMBOL                   FILE:LINE                   LINES   STATUS
  ─────────────────────────────────────────────────────────────────────────────────────────────
   🔴 HIGH     method    _send_json               agtoosa/graph/server.py:28   13     ✅ Safe to Delete
   🔴 HIGH     method    _get_path_tier           agtoosa/review/intel.py:74   13     ✅ Safe to Delete
   🔴 HIGH     method    _capture_mtime_snapshot  agtoosa/watcher/watcher.py:30 11    ✅ Safe to Delete
   🟡 MEDIUM   function  compute_legacy_score     agtoosa/core/scoring.py:102  24     ⚠️  Review Export
   🟢 LOW      class     OldSchemaAdapter         agtoosa/parser/v1.py:15      48     ⚠️  Public Symbol

─────────────────────────────────────────────────────────────────────────────────────────────
🔍 Dry Run Preview: 11 files would be modified (-412 lines)

   agtoosa/graph/server.py          |  -13 ━━━━━━━━━━
   agtoosa/review/intelligence.py   |  -13 ━━━━━━━━━━
   agtoosa/watcher/watcher.py       |  -11 ━━━━━━━━━
   agtoosa/review/pr_bot.py         |  -26 ━━━━━━━━━━━━━━━━━━━
   agtoosa/federation/synthesis.py  |  -26 ━━━━━━━━━━━━━━━━━━━
   ... (6 more files)

💡 Next Steps:
   • Inspect full patch diffs:   agtoosa refactor dead-code --dry-run --diff
   • Target only safe symbols:   agtoosa refactor dead-code --min-confidence high --dry-run
   • Apply safe pruning:         agtoosa refactor dead-code --apply
   • Export machine JSON:        agtoosa refactor dead-code --json
```

---

## 3. CLI Argument Contract

| Option | Type | Default | Description |
|---|---|---|---|
| `--dry-run` | `bool` | `False` | Simulates dead-code removal; outputs compact diffstat preview without modifying disk files. |
| `--diff` | `bool` | `False` | When passed with `--dry-run`, outputs full unified diff blocks for all affected files. |
| `-v`, `--verbose` | `bool` | `False` | Displays in-depth per-symbol rationales and individual multi-step deletion guidelines. |
| `--min-confidence` | `str` | `low` | Filters candidates by confidence threshold (`high`, `medium`, `low`). |
| `--apply` | `bool` | `False` | Executes safe AST deletion with atomic backup creation and rollback ID generation. |
| `--json` | `bool` | `False` | Emits raw JSON structure (`DeadCodeReport.to_dict()`) for MCP and automated tools. |

---

## 4. Implementation Details

1. **`agtoosa/refactor/dead_code.py`**:
   - Refactor `format_dead_code_text(report, verbose: bool = False)`:
     - Render aligned terminal table for candidate symbols with fixed column widths and truncation for long paths.
     - Only emit the multi-line `deletion_steps` when `verbose=True`.
   - Add `format_diffstat(diffs: Dict[str, str], max_files: int = 10) -> str`:
     - Calculate deleted and added lines from unified diff blocks.
     - Render visual ASCII bar chart (`━━━`) for line reductions per file.
2. **`agtoosa/cli/refactor_cmd.py`**:
   - In `cmd_refactor_dead_code()`:
     - Pass `verbose=getattr(args, "verbose", False)` to `format_dead_code_text()`.
     - In `--dry-run` branch: print `format_diffstat(res.get("diffs", {}))`.
     - If `getattr(args, "diff", False)`: print full unified diffs; otherwise print tip explaining `--diff`.
     - Print contextual next-steps block.
3. **`agtoosa/cli/main.py`**:
   - Register `--diff` and `-v`/`--verbose` flags on `dead_code_p`.
4. **Verification & Regression Tests**:
   - Update `tests/test_dead_code.py` to assert compact table formatting, `--diff` gate, and diffstat summary generation.
