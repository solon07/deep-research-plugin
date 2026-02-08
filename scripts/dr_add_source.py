#!/usr/bin/env python3
"""Add a source to sources.jsonl with deduplication by URL."""

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone


def url_hash(url: str) -> str:
    """SHA-256 hash of normalized URL."""
    normalized = url.strip().rstrip('/').lower()
    return hashlib.sha256(normalized.encode()).hexdigest()


def load_existing_hashes(sources_path: str) -> set:
    """Load existing URL hashes from sources.jsonl."""
    hashes = set()
    if not os.path.exists(sources_path):
        return hashes
    with open(sources_path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                if 'hash' in entry:
                    hashes.add(entry['hash'])
            except json.JSONDecodeError:
                continue
    return hashes


def next_source_id(sources_path: str) -> str:
    """Generate the next source ID (S0001, S0002, ...)."""
    max_id = 0
    if os.path.exists(sources_path):
        with open(sources_path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    sid = entry.get('source_id', 'S0000')
                    num = int(sid[1:])
                    max_id = max(max_id, num)
                except (json.JSONDecodeError, ValueError):
                    continue
    return f"S{max_id + 1:04d}"


def main():
    parser = argparse.ArgumentParser(description='Add a source to sources.jsonl')
    parser.add_argument('--run-dir', required=True, help='Path to run directory')
    parser.add_argument('--url', required=True, help='Source URL')
    parser.add_argument('--title', required=True, help='Source title')
    parser.add_argument('--publisher', default='', help='Publisher name')
    parser.add_argument('--published-date', default='', help='Publication date')
    parser.add_argument('--type', default='news',
                        choices=['paper', 'report', 'news', 'blog', 'documentation', 'policy', 'dataset', 'forum'],
                        help='Source type')
    parser.add_argument('--credibility-score', type=float, default=0.5,
                        help='Credibility score 0-1')
    parser.add_argument('--credibility-rationale', nargs='*', default=[],
                        help='Credibility rationale items')
    parser.add_argument('--tags', nargs='*', default=[], help='Tags')
    args = parser.parse_args()

    sources_path = os.path.join(args.run_dir, 'sources.jsonl')
    h = url_hash(args.url)

    existing = load_existing_hashes(sources_path)
    if h in existing:
        print(json.dumps({"status": "duplicate", "url": args.url}))
        sys.exit(0)

    source_id = next_source_id(sources_path)

    entry = {
        "source_id": source_id,
        "url": args.url,
        "title": args.title,
        "publisher": args.publisher,
        "published_date": args.published_date,
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "type": args.type,
        "credibility": {
            "score": args.credibility_score,
            "rationale": args.credibility_rationale
        },
        "tags": args.tags,
        "hash": h
    }

    with open(sources_path, 'a') as f:
        f.write(json.dumps(entry) + '\n')

    print(json.dumps({"status": "added", "source_id": source_id, "url": args.url}))


if __name__ == '__main__':
    main()
