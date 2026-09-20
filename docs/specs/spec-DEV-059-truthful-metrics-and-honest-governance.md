# DEV-059: Truthful Architecture Metrics, Dynamic Commit Deltas & Honest Governance

> **Cycle:** DEV-059  
> **Milestone:** Milestone 19 (v1.0.0 GA Integrity, Trust & Calibration)  
> **Status:** Completed  
> **Type:** Architecture Health, Metrics Integrity & Visualizer Correctness  

---

## 1. Problem Statement

A senior forensic audit on test repository `test2` revealed critical metric illusions and confirmation bias mechanisms within the Agtoosa Visualizer and Metrics Engine:

1. **Hardcoded UI Placebo Deltas (`+2.4% vs last commit`)**:
   In `agtoosa/graph/web/index.html` (lines 68 and 252), the string `+2.4% vs last commit` and `+2.4% vs baseline • Zero structural drift` was hardcoded static HTML. It was never calculated from Git history or previous snapshots, giving developers a false sense of improvement regardless of actual changes or regressions.

2. **Fictitious AI Context Cut (`~74% Saved Token efficiency`)**:
   In `agtoosa/graph/web/index.html` (line 88), `~74% Saved` was hardcoded static text. In `state.js`, the `#kpi-ai-cut` element was never bound or updated with empirical graph extraction measurements.

3. **Traceability Logical Absurdity (`0 Stories, 0 Mapped • Verified`)**:
   When a workspace has zero user stories or specification requirements mapped (`storyCount === 0`), `state.js` rendered `0 Stories` and `0 Mapped • Verified`. Displaying an empty requirements set as "Verified" creates a misleading impression of audit compliance.

4. **Inflated Architecture Grading Curve (100/100 Grade A+ with 79% Unverified Code)**:
   In `agtoosa/graph/metrics.py` lines 305–308, the deduction for low test verification applied only when `test_ratio < 0.20`. A project with only 21% verified units and 79% completely unverified functions received zero deductions, earning a perfect `100/100 Grade A+`.

---

## 2. Acceptance Criteria

- **AC-1 (Dynamic Git & Snapshot Delta Tracking)**:
  - The metrics and visualizer subsystem SHALL store the previous health score in local SQLite storage (`.agtoosa/graph.db` metadata).
  - WHEN a new index or build is triggered, Agtoosa SHALL compute the true delta:
    $$\Delta = \text{score}_{\text{current}} - \text{score}_{\text{previous}}$$
  - IF no prior snapshot exists, the UI SHALL display `Baseline Active` or `Initial Scan` instead of fabricating `+2.4%`.
  - IF $\Delta > 0$, display `+X% vs baseline`; IF $\Delta < 0$, display `-X% vs baseline` (in red/danger); IF $\Delta = 0$, display `No drift`.

- **AC-2 (Empirical AI Context Cut Telemetry)**:
  - The Visualizer SHALL dynamically compute the token efficiency ratio based on average bounded subgraph size ($k=2$ neighborhood) relative to the total repository symbol footprint.
  - The Studio header metric SHALL bind `#kpi-ai-cut` to this empirical ratio (e.g. `~68% Cut` or `Active`), with zero hardcoded percentages in `index.html`.

- **AC-3 (Truthful Delivery Traceability States)**:
  - IF `storyCount === 0`, the Delivery Traceability card SHALL display `0 Stories` and `0 Mapped • Awaiting Specs` (neutral dim/warning), NEVER `Verified`.
  - IF `0 < storyCount` and all stories have verified AST test edges, it SHALL display `100% Mapped • AST Verified`.
  - IF `0 < storyCount` and some stories lack test edges, it SHALL display `${pct}% Mapped • Partial Proof`.

- **AC-4 (Calibrated Proportional Test Verification Scoring)**:
  - `_compute_health_scorecard` in `agtoosa/graph/metrics.py` SHALL replace the binary $<0.20$ threshold with a progressive verification grading curve for codebases with $>5$ code units:
    - $\text{test\_ratio} \ge 0.80$: 0 deduction (Full Verification).
    - $0.60 \le \text{test\_ratio} < 0.80$: 5 deduction (Minor Gap).
    - $0.40 \le \text{test\_ratio} < 0.60$: 12 deduction (Moderate Risk).
    - $0.20 \le \text{test\_ratio} < 0.40$: 20 deduction (High Risk).
    - $\text{test\_ratio} < 0.20$: 30 deduction (Severe Debt, grade capped at C/B).

- **AC-5 (Zero Hardcoded Claims in Web Assets)**:
  - `index.html` SHALL NOT contain any hardcoded delta numbers (`+2.4%`), arbitrary token savings (`~74%`), or static placeholder drift claims. All badge texts must be dynamically populated from `window.GRAPH_DATA`.

- **AC-6 (Backward Compatibility & Automated Verification)**:
  - All existing unit and visualizer tests SHALL pass, and new tests in `tests/test_metrics.py` and `tests/test_genesis_onboarding.py` SHALL verify the calibrated curve and dynamic badge bindings.

---

## 3. Mathematical Specifications

### Verification Scoring Function
Let $N_{\text{code}}$ be the count of code units (`function`, `class`). If $N_{\text{code}} > 5$, test ratio is defined as:
$$\rho_{\text{test}} = \frac{|\{u \in N_{\text{code}} \mid \exists e \in E_{\text{test}} : \text{target}(e) = u\}|}{N_{\text{code}}}$$

The deduction $D_{\text{test}}$ is assigned piecewise:
$$D_{\text{test}} = \begin{cases}
0 & \text{if } \rho_{\text{test}} \ge 0.80 \\
5 & \text{if } 0.60 \le \rho_{\text{test}} < 0.80 \\
12 & \text{if } 0.40 \le \rho_{\text{test}} < 0.60 \\
20 & \text{if } 0.20 \le \rho_{\text{test}} < 0.40 \\
30 & \text{if } \rho_{\text{test}} < 0.20
\end{cases}$$

### Empirical Subgraph Token Efficiency
Let $V$ be the set of all code nodes in the graph. For a typical agent task centered at symbol $s$, the $k$-hop bounded subgraph contains $V_{s, k} \subset V$. The empirical context cut ratio $\eta_{\text{cut}}$ is:
$$\eta_{\text{cut}} = 1 - \frac{\mathbb{E}_{s \in V}[|V_{s, k=2}|]}{|V|}$$
This value $\eta_{\text{cut}}$ is formatted as a percentage (e.g. `71% Saved`) and injected into `window.GRAPH_DATA.healthData.ai_context_cut_pct`.

---

## 4. Tasks & Deliverables

- [x] **Task 59.1**: Update `agtoosa/graph/metrics.py` with the calibrated verification deduction curve and subgraph context cut computation.
- [x] **Task 59.2**: Update `agtoosa/graph/store.py` to persist `health_score` in snapshot metadata for historical delta calculations.
- [x] **Task 59.3**: Enhance `agtoosa/graph/visualizer.py` to extract previous score, calculate $\Delta$, compute empirical context cut, and export truthful traceability status in `workspaceMetadata`.
- [x] **Task 59.4**: Refactor `agtoosa/graph/web/index.html` and `agtoosa/graph/web/js/state.js` to eliminate all hardcoded placebo strings and bind real values.
- [x] **Task 59.5**: Update and expand test suites `tests/test_metrics.py` and `tests/test_genesis_onboarding.py` to ensure complete regression coverage.
- [x] **Task 59.6**: Run end-to-end audit verification on `test2` to ensure honest, truthful display in the Agtoosa Studio.
