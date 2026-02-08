#!/usr/bin/env python3
"""
Deep Research audit and quality gate script.

Modes:
  task_gate  - Called by TaskCompleted hook. Validates task artifacts exist.
  idle_gate  - Called by TeammateIdle hook. Checks if teammate finished work.
  snapshot   - Called by PreCompact hook. Saves run state summary.
  full       - Full audit producing audit.json.

Exit codes:
  0 - Pass (or non-blocking modes)
  2 - Block (artifacts missing, used by task_gate and idle_gate)
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone


def find_latest_run(base_dir: str = '.deep-research') -> str | None:
    """Find the most recent run directory."""
    runs_dir = os.path.join(base_dir, 'runs')
    if not os.path.isdir(runs_dir):
        return None
    runs = sorted(
        [d for d in os.listdir(runs_dir) if os.path.isdir(os.path.join(runs_dir, d))],
        reverse=True
    )
    return os.path.join(runs_dir, runs[0]) if runs else None


def load_jsonl(filepath: str) -> list:
    """Load a JSONL file into a list of dicts."""
    entries = []
    if not os.path.exists(filepath):
        return entries
    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return entries


def check_file_exists(path: str, name: str) -> dict:
    """Check if a file exists and is non-empty."""
    if not os.path.exists(path):
        return {"check": name, "passed": False, "message": f"{name} does not exist"}
    if os.path.getsize(path) == 0:
        return {"check": name, "passed": False, "message": f"{name} is empty"}
    return {"check": name, "passed": True, "message": f"{name} exists"}


def check_sources(run_dir: str) -> list:
    """Validate sources.jsonl."""
    results = []
    sources = load_jsonl(os.path.join(run_dir, 'sources.jsonl'))

    results.append({
        "check": "sources_exist",
        "passed": len(sources) > 0,
        "message": f"Found {len(sources)} sources" if sources else "No sources found"
    })

    # Check that sources have required fields
    missing_fields = []
    for s in sources:
        for field in ['source_id', 'url', 'title', 'type', 'credibility']:
            if field not in s:
                missing_fields.append(f"{s.get('source_id', '?')}.{field}")

    results.append({
        "check": "sources_complete",
        "passed": len(missing_fields) == 0,
        "message": f"All sources have required fields" if not missing_fields
                   else f"Missing fields: {', '.join(missing_fields[:5])}"
    })

    # Check that credibility has rationale, not just a score
    no_rationale = [s['source_id'] for s in sources
                    if isinstance(s.get('credibility'), dict)
                    and not s['credibility'].get('rationale')]
    if no_rationale:
        results.append({
            "check": "credibility_rationale",
            "passed": False,
            "message": f"Sources without credibility rationale: {', '.join(no_rationale[:5])}"
        })
    else:
        results.append({
            "check": "credibility_rationale",
            "passed": True,
            "message": "All sources have credibility rationale"
        })

    return results


def check_notes(run_dir: str) -> list:
    """Check that notes exist for top sources."""
    results = []
    notes_dir = os.path.join(run_dir, 'notes')
    sources = load_jsonl(os.path.join(run_dir, 'sources.jsonl'))

    if not sources:
        return [{"check": "notes", "passed": False, "message": "No sources to check notes for"}]

    # Sort by credibility score descending, take top sources
    scored = [s for s in sources if isinstance(s.get('credibility'), dict)]
    scored.sort(key=lambda s: s['credibility'].get('score', 0), reverse=True)
    top_sources = scored[:min(10, len(scored))]

    notes_files = set(os.listdir(notes_dir)) if os.path.isdir(notes_dir) else set()
    missing_notes = []
    for s in top_sources:
        expected = f"{s['source_id']}.md"
        if expected not in notes_files:
            missing_notes.append(s['source_id'])

    results.append({
        "check": "notes_for_top_sources",
        "passed": len(missing_notes) == 0,
        "message": f"Notes exist for all top {len(top_sources)} sources" if not missing_notes
                   else f"Missing notes for: {', '.join(missing_notes)}"
    })

    return results


def check_claims(run_dir: str) -> list:
    """Validate claims.jsonl."""
    results = []
    claims = load_jsonl(os.path.join(run_dir, 'claims.jsonl'))
    sources = load_jsonl(os.path.join(run_dir, 'sources.jsonl'))
    source_ids = {s['source_id'] for s in sources}

    results.append({
        "check": "claims_exist",
        "passed": len(claims) > 0,
        "message": f"Found {len(claims)} claims" if claims else "No claims found"
    })

    # Check that every claim has at least one citation
    no_citations = [c['claim_id'] for c in claims if not c.get('citations')]
    results.append({
        "check": "claims_have_citations",
        "passed": len(no_citations) == 0,
        "message": "All claims have citations" if not no_citations
                   else f"Claims without citations: {', '.join(no_citations[:5])}"
    })

    # Check that citation source_ids reference valid sources
    invalid_refs = []
    for c in claims:
        for cit in c.get('citations', []):
            if cit.get('source_id') not in source_ids:
                invalid_refs.append(f"{c['claim_id']}→{cit.get('source_id')}")

    results.append({
        "check": "citations_reference_valid_sources",
        "passed": len(invalid_refs) == 0,
        "message": "All citation references are valid" if not invalid_refs
                   else f"Invalid references: {', '.join(invalid_refs[:5])}"
    })

    return results


def check_evidence(run_dir: str) -> list:
    """Validate evidence.jsonl and triangulation."""
    results = []
    claims = load_jsonl(os.path.join(run_dir, 'claims.jsonl'))
    evidence = load_jsonl(os.path.join(run_dir, 'evidence.jsonl'))
    sources = load_jsonl(os.path.join(run_dir, 'sources.jsonl'))

    claim_ids = {c['claim_id'] for c in claims}
    source_ids = {s['source_id'] for s in sources}

    results.append({
        "check": "evidence_exists",
        "passed": len(evidence) > 0,
        "message": f"Found {len(evidence)} evidence edges" if evidence else "No evidence edges found"
    })

    # Check that evidence references valid claims and sources
    invalid = []
    for e in evidence:
        if e.get('claim_id') not in claim_ids:
            invalid.append(f"claim:{e.get('claim_id')}")
        if e.get('source_id') not in source_ids:
            invalid.append(f"source:{e.get('source_id')}")

    results.append({
        "check": "evidence_references_valid",
        "passed": len(invalid) == 0,
        "message": "All evidence references are valid" if not invalid
                   else f"Invalid references: {', '.join(invalid[:5])}"
    })

    # Triangulation: key claims should have >=2 supporting sources or be marked uncertain
    key_claims = [c for c in claims if c.get('importance') == 'key']
    under_supported = []
    for c in key_claims:
        supporting = [e for e in evidence
                      if e.get('claim_id') == c['claim_id']
                      and e.get('relation') == 'supports']
        unique_sources = {e['source_id'] for e in supporting}
        if len(unique_sources) < 2 and c.get('status') not in ('single-source', 'contested'):
            under_supported.append(c['claim_id'])

    results.append({
        "check": "key_claims_triangulated",
        "passed": len(under_supported) == 0,
        "message": f"All {len(key_claims)} key claims are triangulated or marked uncertain"
                   if not under_supported
                   else f"Under-supported key claims (need >=2 sources or 'single-source' status): {', '.join(under_supported[:5])}"
    })

    return results


def check_report(run_dir: str) -> list:
    """Validate report.md has required sections."""
    results = []
    report_path = os.path.join(run_dir, 'report.md')

    if not os.path.exists(report_path) or os.path.getsize(report_path) == 0:
        return [{"check": "report_exists", "passed": False, "message": "report.md does not exist or is empty"}]

    with open(report_path, 'r') as f:
        content = f.read().lower()

    required_sections = [
        ("executive summary", "Executive Summary"),
        ("key findings", "Key Findings"),
        ("evidence", "Evidence Table"),
        ("conflict", "Conflicts"),
        ("limitation", "Limitations"),
        ("source", "Sources/Bibliography"),
    ]

    for keyword, section_name in required_sections:
        results.append({
            "check": f"report_has_{keyword.replace(' ', '_')}",
            "passed": keyword in content,
            "message": f"Report has {section_name}" if keyword in content
                       else f"Report is missing {section_name} section"
        })

    return results


def run_full_audit(run_dir: str) -> dict:
    """Run all checks and produce audit.json."""
    all_results = []
    all_results.extend(check_sources(run_dir))
    all_results.extend(check_notes(run_dir))
    all_results.extend(check_claims(run_dir))
    all_results.extend(check_evidence(run_dir))
    all_results.extend(check_report(run_dir))

    passed = sum(1 for r in all_results if r['passed'])
    failed = sum(1 for r in all_results if not r['passed'])

    audit = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "run_dir": os.path.abspath(run_dir),
        "summary": {
            "total_checks": len(all_results),
            "passed": passed,
            "failed": failed,
            "pass_rate": passed / len(all_results) if all_results else 0
        },
        "results": all_results
    }

    audit_path = os.path.join(run_dir, 'audit.json')
    with open(audit_path, 'w') as f:
        json.dump(audit, f, indent=2)

    return audit


def task_gate(run_dir: str) -> None:
    """Quality gate for TaskCompleted hook. Exit 2 to block if artifacts missing."""
    # Read hook input from stdin to determine task type
    stdin_data = {}
    try:
        raw = sys.stdin.read()
        if raw.strip():
            stdin_data = json.loads(raw)
    except (json.JSONDecodeError, IOError):
        pass

    failures = []

    # Always check: do basic artifacts exist?
    sources = load_jsonl(os.path.join(run_dir, 'sources.jsonl'))
    claims = load_jsonl(os.path.join(run_dir, 'claims.jsonl'))
    evidence = load_jsonl(os.path.join(run_dir, 'evidence.jsonl'))
    report_path = os.path.join(run_dir, 'report.md')

    # Check based on run status to determine what phase we're in
    run_json_path = os.path.join(run_dir, 'run.json')
    status = "unknown"
    if os.path.exists(run_json_path):
        with open(run_json_path, 'r') as f:
            run_data = json.load(f)
            status = run_data.get('status', 'unknown')

    if status in ('scouting', 'analyzing', 'synthesizing', 'complete'):
        if not sources:
            failures.append("No sources in sources.jsonl. Scout work is incomplete.")

    if status in ('analyzing', 'synthesizing', 'complete'):
        if not claims:
            failures.append("No claims in claims.jsonl. Analysis is incomplete.")
        else:
            no_cit = [c['claim_id'] for c in claims if not c.get('citations')]
            if no_cit:
                failures.append(f"Claims without citations: {', '.join(no_cit[:3])}")

    if status in ('synthesizing', 'complete'):
        if not evidence:
            failures.append("No evidence edges. Triangulation is incomplete.")

    if status == 'complete':
        if not os.path.exists(report_path) or os.path.getsize(report_path) == 0:
            failures.append("report.md is missing or empty.")

    if failures:
        print('\n'.join(failures), file=sys.stderr)
        sys.exit(2)

    sys.exit(0)


def idle_gate(run_dir: str) -> None:
    """Quality gate for TeammateIdle hook. Exit 2 to keep teammate working."""
    # Check if the run is in a state where there's still work to do
    run_json_path = os.path.join(run_dir, 'run.json')
    if not os.path.exists(run_json_path):
        sys.exit(0)

    with open(run_json_path, 'r') as f:
        run_data = json.load(f)

    status = run_data.get('status', 'unknown')

    if status == 'complete':
        sys.exit(0)

    # If run is not complete, check if there's pending work
    failures = []
    sources = load_jsonl(os.path.join(run_dir, 'sources.jsonl'))
    claims = load_jsonl(os.path.join(run_dir, 'claims.jsonl'))
    evidence = load_jsonl(os.path.join(run_dir, 'evidence.jsonl'))
    report_path = os.path.join(run_dir, 'report.md')

    if status == 'scouting' and not sources:
        failures.append("Still in scouting phase but no sources gathered yet.")

    if status == 'analyzing' and not claims:
        failures.append("Still in analysis phase but no claims extracted yet.")

    if status == 'synthesizing':
        if not os.path.exists(report_path) or os.path.getsize(report_path) == 0:
            failures.append("Still in synthesis phase but report not written yet.")

    if failures:
        print('\n'.join(failures), file=sys.stderr)
        sys.exit(2)

    sys.exit(0)


def snapshot(run_dir: str) -> None:
    """Save a state summary before compaction."""
    summary = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "sources_count": len(load_jsonl(os.path.join(run_dir, 'sources.jsonl'))),
        "claims_count": len(load_jsonl(os.path.join(run_dir, 'claims.jsonl'))),
        "evidence_count": len(load_jsonl(os.path.join(run_dir, 'evidence.jsonl'))),
    }

    run_json_path = os.path.join(run_dir, 'run.json')
    if os.path.exists(run_json_path):
        with open(run_json_path, 'r') as f:
            run_data = json.load(f)
            summary['status'] = run_data.get('status', 'unknown')

    notes_dir = os.path.join(run_dir, 'notes')
    if os.path.isdir(notes_dir):
        summary['notes_count'] = len(os.listdir(notes_dir))

    snapshot_path = os.path.join(run_dir, 'snapshot.json')
    with open(snapshot_path, 'w') as f:
        json.dump(summary, f, indent=2)

    print(json.dumps(summary))


def main():
    parser = argparse.ArgumentParser(description='Deep Research audit and quality gates')
    parser.add_argument('--mode', required=True,
                        choices=['task_gate', 'idle_gate', 'snapshot', 'full'],
                        help='Audit mode')
    parser.add_argument('--run-dir', default=None,
                        help='Path to run directory (auto-detects latest if not specified)')
    parser.add_argument('--base-dir', default='.deep-research',
                        help='Base directory for research runs')
    args = parser.parse_args()

    run_dir = args.run_dir or find_latest_run(args.base_dir)
    if not run_dir:
        if args.mode in ('task_gate', 'idle_gate'):
            # No run directory found — don't block, just pass
            sys.exit(0)
        else:
            print("No run directory found", file=sys.stderr)
            sys.exit(1)

    if args.mode == 'task_gate':
        task_gate(run_dir)
    elif args.mode == 'idle_gate':
        idle_gate(run_dir)
    elif args.mode == 'snapshot':
        snapshot(run_dir)
    elif args.mode == 'full':
        audit = run_full_audit(run_dir)
        print(json.dumps(audit, indent=2))
        if audit['summary']['failed'] > 0:
            sys.exit(1)


if __name__ == '__main__':
    main()
