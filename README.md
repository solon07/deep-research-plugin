# deep-research

A Claude Code plugin for multi-agent deep research with evidence graphs, quality gates, and publication-quality report generation.

## What It Does

Turns Claude Code into a deep research system that goes beyond simple summarization:

- **Evidence-first**: Every claim traces to specific source excerpts. No unsupported assertions.
- **Triangulation**: Key claims require corroboration from multiple independent sources, or are explicitly marked as single-source.
- **Honest uncertainty**: Conflicts between sources are surfaced, not hidden. Confidence levels are calibrated.
- **Structured artifacts**: Research runs produce reproducible, inspectable data (sources, claims, evidence edges, notes) — not just a final essay.
- **Quality gates**: Hooks enforce that agents can't mark work complete without producing required artifacts.

## Installation

```bash
claude --plugin-dir /path/to/deep-research-plugin
```

Or add to your Claude Code settings to load it automatically.

### Requirements

- Claude Code v2.1.32+
- Python 3.10+
- For full multi-agent parallelism, enable Agent Teams:
  ```bash
  export CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1
  ```

## Usage

### Run a research workflow

```
/deep-research:run What are the implications of the EU AI Act for US technology companies?
```

This kicks off the full pipeline: planning → source discovery → deep reading → claim extraction → triangulation → synthesis → adversarial review → report generation.

### Check progress

```
/deep-research:status
```

### Re-render the report from existing artifacts

```
/deep-research:report
```

### Initialize the workspace

```
/deep-research:init
```

## Architecture

### Agents

| Agent | Model | Role |
|-------|-------|------|
| `dr-lead` | Opus | Orchestrates the run, decomposes questions, assigns tasks, performs adversarial review |
| `dr-scout` | Sonnet | Wide-pass discovery: searches, evaluates sources, writes preliminary notes |
| `dr-analyst` | Opus | Deep reading, atomic claim extraction, triangulation, conflict identification |
| `dr-writer` | Opus | Synthesis and publication-quality report generation |

### Research Pipeline

1. **Intake & Planning** — Decompose the question into research strands, generate diverse query sets
2. **Wide-Pass Discovery** — Search across core, synonym, contrarian, primary-source, and time-bounded queries
3. **Deep Analysis** — Read top sources, extract atomic claims with citations, build evidence edges
4. **Triangulation** — Cross-reference claims across sources, flag single-source and contested claims
5. **Synthesis** — Write evidence-backed narrative with explicit confidence levels
6. **Adversarial Review** — Attempt to falsify key claims, check for missing perspectives
7. **Audit & Report** — Validate all artifacts, generate the final structured report

### Run Artifacts

Each research run produces a directory under `.deep-research/runs/` containing:

```
run.json          — Run metadata and configuration
plan.md           — Research plan with strands and query strategy
queries.json      — Generated search queries by category
sources.jsonl     — Sources with metadata and credibility scoring
notes/            — Structured notes per source
claims.jsonl      — Atomic claims with citations
evidence.jsonl    — Triangulation edges (supports/contradicts)
conflicts.md      — Documented disagreements between sources
synthesis.md      — Narrative synthesis
report.md         — Final structured report
audit.json        — Quality audit results
```

### Quality Gates

Hooks enforce artifact requirements:

- **TaskCompleted**: Blocks task completion if required artifacts are missing or incomplete
- **TeammateIdle**: Prevents agents from going idle before finishing assigned work
- **PreCompact**: Snapshots run state before context compaction

## Optional: MCP Integration

The plugin works with built-in `WebSearch` and `WebFetch` by default. For enhanced capabilities, configure MCP servers for:

- Search APIs (Brave, Tavily, Google Custom Search)
- Academic metadata (Semantic Scholar, CrossRef)
- Internal tools (Notion, Slack, GitHub)

## License

MIT
