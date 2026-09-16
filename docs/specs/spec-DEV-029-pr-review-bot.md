# Specification: DEV-029 PR Blast Radius & Breaking Schema Review Bot

## Status
✅ Implemented & Verified

## Priority Score
**91 / 100** (Highest Team & PR Governance Impact — Automates Architectural Review, Breaking Schema Detection, and Production Risk Tiering Directly in Pull Requests)

## Problem Statement
When developers submit pull requests, manual code reviews cannot easily determine:
1. **Hidden Blast Radius**: A 2-line helper function edit might have 40 downstream callers across 6 modules.
2. **Breaking API Contracts**: Renaming a parameter in a FastAPI handler or Express route may break frontend apps or mobile clients without failing unit tests.
3. **Asynchronous Event Disconnects**: Changing the payload format or deleting an event publisher breaks decoupled Kafka/RabbitMQ/Celery consumers silently.
4. **Production Traffic Exposure**: Reviewers cannot distinguish between edits touching a dormant debug script vs. a critical P0 payment endpoint handling 100,000 requests/minute.

Currently, Agtoosa has local CLI commands (`agtoosa review`, `agtoosa graph impact`, `agtoosa graph routes`, `agtoosa graph events`), but reviewers must manually pull the branch and run them.

## Acceptance Criteria
- **AC-1 (PR Diff & Blast Radius Analysis)**: WHEN given a PR git diff against `base_ref`, the engine SHALL compute directly modified symbols, upstream callers, and high-risk impact chains.
- **AC-2 (API & Event Schema Drift Detection)**: WHEN a PR modifies API routes or event topics, the bot SHALL flag contract changes, breaking payload modifications, and decoupled consumers.
- **AC-3 (Automated GitHub PR Commenting)**: WHEN `agtoosa ci pr-bot` executes in CI, it SHALL generate an interactive GitHub markdown comment summarizing risk, telemetry hotspots, and architectural drift.

## Objectives
1. **Unified PR Impact & Risk Analyzer (`PRReviewEngine`)**:
   - Ingests git diff against base ref (`origin/main`, `main`, or commit SHA).
   - Maps diff line ranges to knowledge graph symbols.
   - Computes:
     - **Upstream Blast Radius**: Transitive caller depth, impacted symbols, and dependency chains.
     - **HTTP API Route Contract Changes**: Detects if modified symbols are bound to Endpoint nodes (DEV-025); flags route additions, deletions, or handler modifications.
     - **Event Bus & Task Queue Lineage**: Detects if modified symbols publish to or subscribe to Topics (DEV-026); flags unhandled events or decoupled message flows.
     - **Production Runtime Traffic Risk Tiering**: Correlates changed symbols with telemetry to assign P0_CRITICAL, P1_HIGH, P2_MODERATE, P3_LOW, or P4_DORMANT.
     - **Cross-Repository Federation Impact**: Detects if changes touch contracts shared with federated repositories (DEV-015).
2. **Polished Sticky PR Comment Formatter (`PRBotCommentFormatter`)**:
   - Produces a high-signal, beautifully formatted GitHub Flavored Markdown comment:
     - Header verdict badge (`APPROVED`, `WARNING`, `BLOCKED`).
     - Production Traffic Risk meter (P0–P4).
     - Collapsible Route Contract table showing method, path, handler, and injected DI services.
     - Collapsible Event Bus Lineage table showing topics, brokers, and publisher/subscriber chains.
     - Architectural drift alarms (layer boundary violations, circular dependencies).
     - Targeted test suite recommendations.
3. **GitHub API Commenter & CI Bot Integration**:
   - `agtoosa ci pr-bot [--base <ref>] [--pr <num>] [--post-comment] [--output <path>] [--json] [--fail-on-p0] [--strict]`.
   - Uses zero-dependency `urllib.request` to search for existing sticky comment (`<!-- agtoosa-pr-bot-comment -->`) and update it in-place, or post a new one.
   - Exits with non-zero code if `--fail-on-p0` is enabled and P0 traffic is impacted, or if `--strict` and drift errors exist.
4. **GitHub Actions Workflow Template**:
   - Create `.github/workflows/agtoosa-pr-bot.yml` ready for immediate plug-and-play adoption in any repository.
5. **Testing & Quality Assurance**:
   - Unit and integration tests in `tests/test_pr_bot.py` testing diff parsing, route impact calculation, event lineage correlation, telemetry risk tiering, sticky comment posting mock, and CLI flags.

## Architecture

```
[ Pull Request Diff ] (git diff origin/main...HEAD)
          │
          ▼
   [ PRReviewEngine ]
   ┌──────┴──────────────────────────────┐
   │ 1. Upstream Blast Radius (Graph)     │
   │ 2. HTTP Route Contracts (DEV-025)   │
   │ 3. Event Bus Lineage (DEV-026)      │
   │ 4. Telemetry Risk Tiering (DEV-018) │
   │ 5. Architectural Drift (DEV-010)    │
   └──────┬──────────────────────────────┘
          │
          ▼
[ PRBotCommentFormatter ]
          │
     ┌────┴──────────────────────────┐
     ▼                               ▼
[ GitHub PR Comment ]    [ Local CLI / JSON Report ]
(Sticky comment via API)  (agtoosa ci pr-bot)
```

## Verification Plan
- Comprehensive unit tests in `tests/test_pr_bot.py`.
- Run `agtoosa ci pr-bot` locally on active workspace and verify output.
- All repository unit tests remain 100% passing.
