---
name: report
description: Re-render the deep research report from existing artifacts without re-fetching sources. Useful for updating the report format or regenerating after manual edits to claims/evidence.
disable-model-invocation: true
context: fork
agent: dr-writer
---

ultrathink

Re-render the deep research report from existing artifacts.

## Instructions

1. Find the latest run directory under `.deep-research/runs/` (or use the run specified in $ARGUMENTS if provided).
2. Read all existing artifacts: `sources.jsonl`, `claims.jsonl`, `evidence.jsonl`, `conflicts.md`, `notes/*.md`.
3. Write a fresh `synthesis.md` based on the evidence.
4. Generate the report: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/dr_render_report.py --run-dir <run_dir>`
5. Review and enhance the generated `report.md` with your narrative analysis.

## Constraints

- Do NOT re-fetch any web sources. Work only from existing artifacts.
- Do NOT modify `sources.jsonl`, `claims.jsonl`, or `evidence.jsonl`.
- You MAY update `synthesis.md`, `conflicts.md`, and `report.md`.

## Deliverable

Return the path to the updated `report.md` and a brief summary of changes.
