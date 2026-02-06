"""Seed Data Loader: JSONL events + culture/factions into PostgreSQL

Loads into *_seed tables for safe development.

Example:
  python load_seed_data.py --dsn postgresql://user:pass@host:5432/db \
    --events seed_data/events/sample_events.jsonl \
    --culture seed_data/culture/culture_records.json \
    --factions seed_data/factions/factions.json \
    --alignments seed_data/factions/alignments.json
"""

from __future__ import annotations
import argparse, json

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dsn', required=True)
    ap.add_argument('--events')
    ap.add_argument('--culture')
    ap.add_argument('--factions')
    ap.add_argument('--alignments')
    args = ap.parse_args()

    try:
        import psycopg2
        from psycopg2.extras import execute_values
    except Exception:
        psycopg2 = None

    if psycopg2 is None:
        print("psycopg2 not installed. Install with: pip install psycopg2-binary")
        return

    conn = psycopg2.connect(args.dsn)
    conn.autocommit = True
    cur = conn.cursor()

    if args.events:
        rows = []
        with open(args.events, 'r', encoding='utf-8') as f:
            for line in f:
                if not line.strip():
                    continue
                e = json.loads(line)
                rows.append((e['id'], e['type'], e['timestamp'], json.dumps(e.get('source',{})),
                             json.dumps(e.get('actor',{})), json.dumps(e.get('location',{})), json.dumps(e.get('payload',{}))))
        cur.execute('''CREATE TABLE IF NOT EXISTS world_events_seed (
            id TEXT PRIMARY KEY,
            type TEXT,
            ts TIMESTAMPTZ,
            source JSONB,
            actor JSONB,
            location JSONB,
            payload JSONB
        );''')
        execute_values(cur, "INSERT INTO world_events_seed (id,type,ts,source,actor,location,payload) VALUES %s ON CONFLICT (id) DO NOTHING", rows)
        print(f"Loaded {len(rows)} events into world_events_seed")

    if args.culture:
        recs = json.load(open(args.culture, 'r', encoding='utf-8'))
        cur.execute('''CREATE TABLE IF NOT EXISTS culture_records_seed (
            id TEXT PRIMARY KEY,
            scope JSONB,
            kind TEXT,
            summary TEXT,
            strength DOUBLE PRECISION,
            last_observed TIMESTAMPTZ,
            evidence_ids JSONB
        );''')
        rows = [(r['id'], json.dumps(r.get('scope',{})), r['kind'], r['summary'], float(r['strength']), r['last_observed'], json.dumps(r.get('evidence_ids',[]))) for r in recs]
        execute_values(cur, "INSERT INTO culture_records_seed (id,scope,kind,summary,strength,last_observed,evidence_ids) VALUES %s ON CONFLICT (id) DO NOTHING", rows)
        print(f"Loaded {len(rows)} culture records into culture_records_seed")

    if args.factions:
        recs = json.load(open(args.factions, 'r', encoding='utf-8'))
        cur.execute('''CREATE TABLE IF NOT EXISTS factions_seed (
            id TEXT PRIMARY KEY,
            name TEXT,
            description TEXT,
            values JSONB,
            norms JSONB,
            rituals JSONB,
            membership_rules JSONB,
            rivalries JSONB
        );''')
        rows = [(r['id'], r['name'], r['description'], json.dumps(r.get('values',[])), json.dumps(r.get('norms',[])),
                 json.dumps(r.get('rituals',[])), json.dumps(r.get('membership_rules',{})), json.dumps(r.get('rivalries',{}))) for r in recs]
        execute_values(cur, "INSERT INTO factions_seed (id,name,description,values,norms,rituals,membership_rules,rivalries) VALUES %s ON CONFLICT (id) DO NOTHING", rows)
        print(f"Loaded {len(rows)} factions into factions_seed")

    if args.alignments:
        recs = json.load(open(args.alignments, 'r', encoding='utf-8'))
        cur.execute('''CREATE TABLE IF NOT EXISTS faction_alignments_seed (
            agent TEXT,
            faction TEXT,
            alignment DOUBLE PRECISION,
            PRIMARY KEY (agent, faction)
        );''')
        rows = [(r['agent'], r['faction'], float(r['alignment'])) for r in recs]
        execute_values(cur, "INSERT INTO faction_alignments_seed (agent,faction,alignment) VALUES %s ON CONFLICT (agent,faction) DO NOTHING", rows)
        print(f"Loaded {len(rows)} alignments into faction_alignments_seed")

    cur.close()
    conn.close()

if __name__ == '__main__':
    main()
