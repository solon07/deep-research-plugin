#!/usr/bin/env python3
"""Render a final report from run artifacts (claims, evidence, sources, synthesis)."""

import argparse
import json
import os
import sys
from datetime import datetime, timezone


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


def read_file(filepath: str) -> str:
    """Read a file's contents, return empty string if missing."""
    if not os.path.exists(filepath):
        return ''
    with open(filepath, 'r') as f:
        return f.read()


def build_evidence_table(claims: list, evidence: list, sources: list) -> str:
    """Build a markdown evidence table."""
    source_map = {s['source_id']: s for s in sources}
    lines = []
    lines.append("| Claim ID | Claim | Importance | Status | Supporting Sources | Contradicting Sources |")
    lines.append("|----------|-------|------------|--------|-------------------|----------------------|")

    for c in claims:
        claim_id = c.get('claim_id', '?')
        claim_text = c.get('claim', '?')
        # Truncate long claims for the table
        if len(claim_text) > 80:
            claim_text = claim_text[:77] + '...'
        importance = c.get('importance', '?')
        status = c.get('status', '?')

        supporting = []
        contradicting = []
        for e in evidence:
            if e.get('claim_id') == claim_id:
                sid = e.get('source_id', '?')
                source = source_map.get(sid, {})
                label = source.get('title', sid)
                if len(label) > 30:
                    label = label[:27] + '...'
                if e.get('relation') == 'supports':
                    supporting.append(f"{sid}")
                elif e.get('relation') == 'contradicts':
                    contradicting.append(f"{sid}")

        sup_str = ', '.join(supporting) if supporting else '-'
        con_str = ', '.join(contradicting) if contradicting else '-'
        lines.append(f"| {claim_id} | {claim_text} | {importance} | {status} | {sup_str} | {con_str} |")

    return '\n'.join(lines)


def build_bibliography(sources: list) -> str:
    """Build a markdown bibliography."""
    lines = []
    for s in sources:
        sid = s.get('source_id', '?')
        title = s.get('title', 'Untitled')
        url = s.get('url', '')
        publisher = s.get('publisher', '')
        pub_date = s.get('published_date', '')
        stype = s.get('type', '')
        cred = s.get('credibility', {})
        score = cred.get('score', '?')
        rationale = ', '.join(cred.get('rationale', []))

        entry = f"- **[{sid}]** [{title}]({url})"
        if publisher:
            entry += f" — {publisher}"
        if pub_date:
            entry += f" ({pub_date})"
        entry += f" | Type: {stype} | Credibility: {score}"
        if rationale:
            entry += f" ({rationale})"
        lines.append(entry)

    return '\n'.join(lines)


def render_report(run_dir: str, output_format: str = 'md') -> str:
    """Compile the full report from artifacts."""
    run_json_path = os.path.join(run_dir, 'run.json')
    if not os.path.exists(run_json_path):
        print(f"run.json not found in {run_dir}", file=sys.stderr)
        sys.exit(1)

    with open(run_json_path, 'r') as f:
        run_data = json.load(f)

    sources = load_jsonl(os.path.join(run_dir, 'sources.jsonl'))
    claims = load_jsonl(os.path.join(run_dir, 'claims.jsonl'))
    evidence = load_jsonl(os.path.join(run_dir, 'evidence.jsonl'))
    synthesis = read_file(os.path.join(run_dir, 'synthesis.md'))
    conflicts = read_file(os.path.join(run_dir, 'conflicts.md'))

    topic = run_data.get('topic', 'Unknown Topic')
    created = run_data.get('created_at', '')
    run_id = run_data.get('run_id', '')

    key_claims = [c for c in claims if c.get('importance') == 'key']
    supporting_claims = [c for c in claims if c.get('importance') == 'supporting']

    # Statistics
    stats = {
        "sources": len(sources),
        "claims": len(claims),
        "key_claims": len(key_claims),
        "evidence_edges": len(evidence),
        "contested": len([c for c in claims if c.get('status') == 'contested']),
        "single_source": len([c for c in claims if c.get('status') == 'single-source']),
    }

    report_parts = []

    # Title
    report_parts.append(f"# Deep Research Report: {topic}\n")
    report_parts.append(f"*Run ID: {run_id}*  ")
    report_parts.append(f"*Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}*  ")
    report_parts.append(f"*Sources: {stats['sources']} | Claims: {stats['claims']} | Evidence edges: {stats['evidence_edges']}*\n")
    report_parts.append("---\n")

    # Executive Summary
    report_parts.append("## Executive Summary\n")
    if synthesis:
        # Extract first paragraph or first N lines as executive summary
        synth_lines = synthesis.strip().split('\n')
        # Look for a summary section or use first paragraph
        summary_lines = []
        for line in synth_lines:
            if line.strip() == '' and summary_lines:
                break
            if not line.startswith('#'):
                summary_lines.append(line)
        if summary_lines:
            report_parts.append('\n'.join(summary_lines) + '\n')
        else:
            report_parts.append("*No executive summary generated. See Key Findings below.*\n")
    else:
        report_parts.append("*No synthesis available. Report generated from raw artifacts.*\n")

    # Key Findings
    report_parts.append("## Key Findings\n")
    if key_claims:
        for c in key_claims:
            status_badge = ""
            if c.get('status') == 'verified':
                status_badge = " [VERIFIED]"
            elif c.get('status') == 'contested':
                status_badge = " [CONTESTED]"
            elif c.get('status') == 'single-source':
                status_badge = " [SINGLE SOURCE]"

            cit_refs = ', '.join(cit.get('source_id', '?') for cit in c.get('citations', []))
            report_parts.append(f"- **{c['claim']}**{status_badge} (Sources: {cit_refs})")
        report_parts.append("")
    else:
        report_parts.append("*No key claims extracted.*\n")

    # Full Synthesis
    if synthesis:
        report_parts.append("## Detailed Analysis\n")
        report_parts.append(synthesis + "\n")

    # Evidence Table
    report_parts.append("## Evidence Table\n")
    if claims and evidence:
        report_parts.append(build_evidence_table(claims, evidence, sources) + "\n")
    else:
        report_parts.append("*No evidence table available.*\n")

    # Conflicts & Disagreements
    report_parts.append("## Conflicts & Disagreements\n")
    if conflicts and conflicts.strip():
        report_parts.append(conflicts + "\n")
    else:
        contested = [c for c in claims if c.get('status') == 'contested']
        if contested:
            for c in contested:
                report_parts.append(f"- **{c['claim_id']}**: {c['claim']}")
            report_parts.append("")
        else:
            report_parts.append("*No conflicts identified between sources.*\n")

    # Limitations & Unknowns
    report_parts.append("## Limitations & Unknowns\n")
    single_source = [c for c in claims if c.get('status') == 'single-source']
    if single_source:
        report_parts.append("### Single-Source Claims\n")
        report_parts.append("The following claims are backed by only one source and should be treated with caution:\n")
        for c in single_source:
            report_parts.append(f"- {c['claim']} ({c['claim_id']})")
        report_parts.append("")

    report_parts.append(f"- Total sources evaluated: {stats['sources']}")
    report_parts.append(f"- Claims with contested evidence: {stats['contested']}")
    report_parts.append(f"- Claims with single-source backing: {stats['single_source']}")
    report_parts.append("")

    # Methodology
    report_parts.append("## Methodology\n")
    report_parts.append("This report was generated using a multi-agent deep research workflow:\n")
    report_parts.append("1. **Wide-pass discovery**: Diverse search queries across multiple source types")
    report_parts.append("2. **Deep reading**: Structured note-taking from top sources")
    report_parts.append("3. **Claim extraction**: Atomic, testable claims with citation pointers")
    report_parts.append("4. **Triangulation**: Cross-referencing claims across independent sources")
    report_parts.append("5. **Adversarial review**: Attempting to falsify key claims and find counterevidence")
    report_parts.append("6. **Synthesis**: Evidence-backed narrative with explicit uncertainty\n")

    # Bibliography
    report_parts.append("## Sources & Bibliography\n")
    if sources:
        report_parts.append(build_bibliography(sources) + "\n")
    else:
        report_parts.append("*No sources.*\n")

    report = '\n'.join(report_parts)

    # Write to file
    report_path = os.path.join(run_dir, 'report.md')
    with open(report_path, 'w') as f:
        f.write(report)

    print(json.dumps({
        "status": "rendered",
        "report_path": os.path.abspath(report_path),
        "stats": stats
    }, indent=2))

    return report


def main():
    parser = argparse.ArgumentParser(description='Render a deep research report')
    parser.add_argument('--run-dir', required=True, help='Path to run directory')
    parser.add_argument('--format', choices=['md', 'html'], default='md',
                        help='Output format (default: md)')
    args = parser.parse_args()

    render_report(args.run_dir, args.format)


if __name__ == '__main__':
    main()
