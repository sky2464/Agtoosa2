# Spec: DEV-034 — Hierarchical Living C4 Architecture Wiki & Automated Export Engine

> **Story ID:** DEV-034  
> **Parent Milestone:** Milestone 14 (v0.7.0)  
> **Status:** 📋 Ready for Implementation  
> **Impact Rating:** 93 / 100  
> **Dependencies:** DEV-048 (First-Party Community Modularity Optimizer), DEV-033  
> **Spec Created:** 2026-09-14  

---

## 1. Requirements & Goal Contract

### Goal Contract
DEV-034 synthesizes a living, cross-linked, browsable codebase architecture wiki powered by first-party modularity community detection and Robert C. Martin package metrics. While tools like Graphify generate flat, disconnected markdown summaries, DEV-034 builds an interconnected knowledge wiki in `.agtoosa/wiki/` with Obsidian `[[wikilinks]]`, auto-generated dynamic C4 container/component diagrams for each detected subsystem, and mathematical package architecture metrics ($C_a, C_e, I, A, D$).

### User Stories
- **US-1**: As a software architect, I want to run `agtoosa wiki build` to generate an interconnected wiki for my repository with Obsidian-compatible `[[wikilinks]]` and embedded Mermaid C4 architecture diagrams.
- **US-2**: As an engineering manager, I want `agtoosa wiki metrics` to compute Martin package metrics (Instability $I$, Abstractness $A$, Distance from Main Sequence $D$) across communities to pinpoint packages in the Zone of Pain ($I \approx 0, A \approx 0$) or Zone of Uselessness ($I \approx 1, A \approx 1$).
- **US-3**: As an AI coding agent, I want structured wiki articles and component indices to rapidly orient in unfamiliar subsystems without exhaustive code scanning.

### Acceptance Criteria (EARS)
- **AC-34.1 (Community-Partitioned Wiki Generation)**: WHEN `agtoosa wiki build` is executed, the engine SHALL partition the graph into communities and generate index and community markdown articles in `.agtoosa/wiki/` containing member symbols, external dependencies, and `[[wikilinks]]`.
- **AC-34.2 (Martin Architecture Metrics)**: WHEN `agtoosa wiki metrics` is invoked, the engine SHALL compute $C_a, C_e, I, A,$ and $D$ for each community, reporting stability and distance from the Main Sequence.
- **AC-34.3 (Embedded Dynamic C4 Diagrams)**: WHEN community articles are generated, each article SHALL embed a valid Mermaid diagram illustrating that community's internal connections and external boundary links.

---

## 2. Architecture & Data Flow

```mermaid
flowchart TD
    Store[GraphStore SQLite] --> CommEngine[Community Modularity Engine]
    CommEngine --> Communities[Partitioned Architecture Subsystems]
    
    Communities --> MetricCalc[Martin Package Metrics: Ca, Ce, I, A, D]
    Communities --> C4Gen[Subsystem Mermaid C4 Diagram Generator]
    
    MetricCalc --> WikiGen[Living Wiki Generator]
    C4Gen --> WikiGen
    
    WikiGen --> WikiFiles[Structured Wiki: .agtoosa/wiki/ with [[wikilinks]]]
```

---

## 3. Implementation Verification
- Engine: `agtoosa/graph/wiki.py`
- CLI: `agtoosa wiki build`, `agtoosa wiki metrics`
- Test Suite: `tests/test_living_wiki.py`
