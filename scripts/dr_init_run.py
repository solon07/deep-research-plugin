#!/usr/bin/env python3
"""Initialize a new deep research run directory and run.json."""

import argparse
import json
import os
import re
import string
import random
from datetime import datetime, timezone


def slugify(text: str, max_length: int = 40) -> str:
    """Convert text to a URL-friendly slug."""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_]+', '-', text)
    text = re.sub(r'-+', '-', text)
    text = text.strip('-')
    return text[:max_length]


def short_id(length: int = 6) -> str:
    """Generate a short random ID."""
    chars = string.ascii_lowercase + string.digits
    return ''.join(random.choices(chars, k=length))


def main():
    parser = argparse.ArgumentParser(description='Initialize a deep research run')
    parser.add_argument('topic', help='Research topic or question')
    parser.add_argument('--depth', choices=['quick', 'standard', 'deep'], default='deep',
                        help='Research depth (default: deep)')
    parser.add_argument('--preferred-domains', nargs='*', default=[],
                        help='Preferred source domains')
    parser.add_argument('--blocked-domains', nargs='*', default=[],
                        help='Blocked source domains')
    parser.add_argument('--recency-days', type=int, default=None,
                        help='Only consider sources from the last N days')
    parser.add_argument('--base-dir', default='.deep-research',
                        help='Base directory for research runs')
    args = parser.parse_args()

    now = datetime.now(timezone.utc)
    date_str = now.strftime('%Y-%m-%d')
    slug = slugify(args.topic)
    sid = short_id()
    run_id = f"{date_str}__{slug}__{sid}"

    run_dir = os.path.join(args.base_dir, 'runs', run_id)
    os.makedirs(os.path.join(run_dir, 'notes'), exist_ok=True)

    run_json = {
        "run_id": run_id,
        "created_at": now.isoformat(),
        "topic": args.topic,
        "depth": args.depth,
        "source_preferences": {
            "preferred_domains": args.preferred_domains,
            "blocked_domains": args.blocked_domains,
            "recency_days": args.recency_days
        },
        "status": "planning"
    }

    run_json_path = os.path.join(run_dir, 'run.json')
    with open(run_json_path, 'w') as f:
        json.dump(run_json, f, indent=2)

    # Create empty artifact files so agents know the expected structure
    for filename in ['sources.jsonl', 'claims.jsonl', 'evidence.jsonl']:
        open(os.path.join(run_dir, filename), 'a').close()

    # Create placeholder markdown files
    for filename in ['plan.md', 'conflicts.md', 'synthesis.md', 'report.md']:
        filepath = os.path.join(run_dir, filename)
        if not os.path.exists(filepath):
            open(filepath, 'a').close()

    print(json.dumps({
        "run_id": run_id,
        "run_dir": os.path.abspath(run_dir),
        "run_json": os.path.abspath(run_json_path)
    }, indent=2))


if __name__ == '__main__':
    main()
