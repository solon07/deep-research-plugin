---
name: status
description: Check the progress of the current or most recent deep research run. Shows stage, source counts, claim counts, and any issues.
---

Check the status of the most recent deep research run.

## Instructions

1. Find the latest run directory under `.deep-research/runs/` (sort by directory name, most recent first).
2. Read `run.json` for the run metadata and current status.
3. Count entries in `sources.jsonl`, `claims.jsonl`, and `evidence.jsonl`.
4. List any notes files in the `notes/` directory.
5. Check if `report.md` exists and has content.
6. Run a quick audit: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/dr_audit.py --mode full --run-dir <run_dir>`

## Output

Provide a concise status summary:
- **Run ID**: the run identifier
- **Topic**: the research question
- **Status**: current phase (planning/scouting/analyzing/synthesizing/complete)
- **Sources**: count and breakdown by type
- **Claims**: count and breakdown by importance and status
- **Evidence**: edge count
- **Notes**: number of source notes written
- **Report**: exists/empty/missing
- **Audit**: pass/fail with failure details if any
