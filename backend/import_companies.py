"""
Import companies from public ATS slug lists into companies.yaml.

Usage:
  python import_companies.py --audit                    Quality table on the current list (use this first)
  python import_companies.py --dry-run                  Preview what --apply would add
  python import_companies.py --apply                    Append new entries to companies.yaml
  python import_companies.py --prune                    Find companies with zero scraped jobs, propose removal
  python import_companies.py --prune --dry-run          Print prune candidates only

Source: Feashliaa/job-board-aggregator (CC BY-NC 4.0 datasets, fine for personal use).
Quality gate: backend/data/known_tech_companies.txt (edit to broaden/narrow scope).
"""
import argparse
import json
import re
import sys
import urllib.request
from pathlib import Path

import yaml

ROOT = Path(__file__).parent
COMPANIES_YAML = ROOT / "companies.yaml"
KNOWN_LIST = ROOT / "data" / "known_tech_companies.txt"

AGGREGATOR_BASE = "https://raw.githubusercontent.com/Feashliaa/job-board-aggregator/main/data"
SOURCES = {
    "greenhouse": f"{AGGREGATOR_BASE}/greenhouse_companies.json",
    "lever":      f"{AGGREGATOR_BASE}/lever_companies.json",
    "ashby":      f"{AGGREGATOR_BASE}/ashby_companies.json",
    "workday":    f"{AGGREGATOR_BASE}/workday_companies.json",
}

# Tokens we want fully uppercase in display names (slug-derived).
ACRONYMS = {"ai", "ml", "io", "hq", "us", "uk", "eu", "vc", "ny", "la", "sf", "qa", "ux", "api"}


# ---------- helpers ----------

def normalize(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", s.lower())


def slug_to_display_name(slug: str) -> str:
    parts = re.split(r"[-_]+", slug)
    out = []
    for p in parts:
        if not p:
            continue
        if p.lower() in ACRONYMS:
            out.append(p.upper())
        else:
            out.append(p[:1].upper() + p[1:])
    return " ".join(out) or slug


def load_known_names() -> dict[str, str]:
    """Returns {normalized_name: original_spelling}."""
    if not KNOWN_LIST.exists():
        print(f"warning: {KNOWN_LIST} not found — every candidate will be dropped by the quality gate", file=sys.stderr)
        return {}
    out: dict[str, str] = {}
    for line in KNOWN_LIST.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        out[normalize(s)] = s
    return out


def load_yaml() -> dict:
    return yaml.safe_load(COMPANIES_YAML.read_text(encoding="utf-8")) or {}


def fetch_json(url: str):
    with urllib.request.urlopen(url, timeout=60) as r:
        return json.loads(r.read())


def parse_workday(entry: str) -> tuple[str, int, str] | None:
    parts = entry.split("|")
    if len(parts) != 3:
        return None
    tenant, wd, site = parts
    m = re.fullmatch(r"wd(\d+)", wd)
    if not m:
        return None
    return tenant, int(m.group(1)), site


# ---------- candidate collection / filtering ----------

def collect_candidates(known: dict[str, str]) -> tuple[dict[str, list[dict]], dict[str, int]]:
    out: dict[str, list[dict]] = {}
    fetched: dict[str, int] = {}
    for ats, url in SOURCES.items():
        print(f"  fetching {ats}...", file=sys.stderr)
        try:
            data = fetch_json(url)
        except Exception as e:
            print(f"  FAILED to fetch {ats}: {e}", file=sys.stderr)
            out[ats] = []
            fetched[ats] = 0
            continue
        fetched[ats] = len(data)
        cands: list[dict] = []
        seen_tenant: set[str] = set()
        for entry in data:
            if ats == "workday":
                parsed = parse_workday(entry)
                if not parsed:
                    continue
                tenant, wd_num, site = parsed
                # The aggregator has multiple sites per tenant; keep only the first.
                if tenant in seen_tenant:
                    continue
                seen_tenant.add(tenant)
                norm = normalize(tenant)
                if norm not in known:
                    continue
                cands.append({
                    "name": known[norm],
                    "slug": tenant,
                    "ats": "workday",
                    "tenant": tenant,
                    "wd_num": wd_num,
                    "site": site,
                })
            else:
                slug = entry
                if not isinstance(slug, str) or not slug:
                    continue
                norm = normalize(slug)
                if norm not in known:
                    continue
                cands.append({
                    "name": known[norm],
                    "slug": slug,
                    "ats": ats,
                })
        out[ats] = cands
    return out, fetched


def build_existing_keys(yaml_data: dict) -> set[tuple[str, str]]:
    """Build a dedup set covering both `(slug, ats)` and `(normalized_name, ats)`.
    Some hand-typed YAML entries use a different slug than the aggregator's canonical
    one (e.g. name=Hex slug=hextechnologies, name=DoorDash slug=doordashusa). Without
    the name-based key those would re-import as duplicates."""
    keys: set[tuple[str, str]] = set()
    for c in (yaml_data.get("companies") or []):
        ats = c.get("ats")
        if not ats:
            continue
        if c.get("slug"):
            keys.add((c["slug"].lower(), ats))
        if c.get("name"):
            keys.add((normalize(c["name"]), ats))
    return keys


def build_disabled_keys(yaml_data: dict) -> set[tuple[str, str]]:
    keys: set[tuple[str, str]] = set()
    for entry in (yaml_data.get("disabled") or []):
        if not isinstance(entry, str) or ":" not in entry:
            continue
        ats, slug = entry.split(":", 1)
        keys.add((slug.lower(), ats))
    return keys


def filter_candidates(
    cands: dict[str, list[dict]],
    yaml_data: dict,
) -> tuple[dict[str, list[dict]], dict[str, dict[str, int]]]:
    existing = build_existing_keys(yaml_data)
    disabled = build_disabled_keys(yaml_data)
    exclude_terms = [
        t.lower() for t in
        ((yaml_data.get("criteria") or {}).get("exclude") or [])
        if isinstance(t, str) and t.strip()
    ]

    drops = {ats: {"already_present": 0, "disabled": 0, "excluded": 0} for ats in cands}
    kept: dict[str, list[dict]] = {ats: [] for ats in cands}

    for ats, lst in cands.items():
        for c in lst:
            slug_key = (c["slug"].lower(), ats)
            name_key = (normalize(c["name"]), ats)
            if slug_key in existing or name_key in existing:
                drops[ats]["already_present"] += 1
                continue
            if slug_key in disabled or name_key in disabled:
                drops[ats]["disabled"] += 1
                continue
            name_low = c["name"].lower()
            if any(t in name_low for t in exclude_terms):
                drops[ats]["excluded"] += 1
                continue
            kept[ats].append(c)

    return kept, drops


# ---------- YAML editing (text-level, preserves comments) ----------

def format_yaml_block(cands: list[dict]) -> str:
    out: list[str] = []
    for c in cands:
        out.append(f"  - name: {yaml_str(c['name'])}")
        out.append(f"    slug: {yaml_str(c['slug'])}")
        out.append(f"    ats: {c['ats']}")
        if c["ats"] == "workday":
            out.append(f"    tenant: {yaml_str(c['tenant'])}")
            out.append(f"    wd_num: {c['wd_num']}")
            out.append(f"    site: {yaml_str(c['site'])}")
    return "\n".join(out) + "\n"


def yaml_str(s: str) -> str:
    """Quote a YAML scalar if it contains characters PyYAML would treat as syntax."""
    if re.search(r"^[\s'\"\[\]\{\},&*#?|<>=!%@`]|[:#]\s|\s$", s):
        return '"' + s.replace('\\', '\\\\').replace('"', '\\"') + '"'
    return s


_TOP_LEVEL_KEY_RE = re.compile(r"^([a-zA-Z_][a-zA-Z0-9_]*)\s*:\s*$")


def insert_companies_block(text: str, block: str) -> str:
    """Insert block at the end of the top-level `companies:` list."""
    lines = text.splitlines(keepends=True)
    # Find the next top-level key after `companies:` — that's our insertion boundary.
    in_companies = False
    insert_idx = len(lines)
    for i, line in enumerate(lines):
        m = _TOP_LEVEL_KEY_RE.match(line)
        if m:
            if m.group(1) == "companies":
                in_companies = True
            elif in_companies:
                insert_idx = i
                break
    # Trim trailing blank lines so the new block sits flush with the list.
    j = insert_idx - 1
    while j >= 0 and lines[j].strip() == "":
        j -= 1
    insert_idx = j + 1

    head = "".join(lines[:insert_idx])
    tail = "".join(lines[insert_idx:])
    sep = "" if head.endswith("\n") else "\n"
    return head + sep + block + "\n" + tail


def remove_company_entries(text: str, keys_to_remove: set[tuple[str, str]]) -> tuple[str, int]:
    """Remove `(slug, ats)` entries from the companies: list. Returns (new_text, removed_count)."""
    lines = text.splitlines(keepends=True)
    out: list[str] = []
    i = 0
    in_companies = False
    removed = 0
    while i < len(lines):
        line = lines[i]
        m = _TOP_LEVEL_KEY_RE.match(line)
        if m:
            in_companies = (m.group(1) == "companies")
            out.append(line)
            i += 1
            continue
        if in_companies and re.match(r"^\s*-\s+name\s*:", line):
            # Collect this entry's lines (until next "  - name:" or top-level key).
            entry_start = i
            i += 1
            while i < len(lines):
                if re.match(r"^\s*-\s+name\s*:", lines[i]):
                    break
                if _TOP_LEVEL_KEY_RE.match(lines[i]):
                    break
                i += 1
            entry_lines = lines[entry_start:i]
            entry_text = "".join(entry_lines)
            slug_m = re.search(r"^\s*slug\s*:\s*(.+?)\s*$", entry_text, re.M)
            ats_m = re.search(r"^\s*ats\s*:\s*(\S+)\s*$", entry_text, re.M)
            if slug_m and ats_m:
                slug_v = slug_m.group(1).strip().strip('"').strip("'")
                ats_v = ats_m.group(1).strip()
                if (slug_v.lower(), ats_v) in keys_to_remove:
                    removed += 1
                    continue  # drop this entry's lines
            out.extend(entry_lines)
            continue
        out.append(line)
        i += 1
    return "".join(out), removed


def append_to_disabled(text: str, keys: list[tuple[str, str]]) -> str:
    """Add `<ats>:<slug>` strings under the top-level `disabled:` list. Creates the block if missing."""
    if not keys:
        return text
    lines = text.splitlines(keepends=True)
    formatted = [f"  - {ats}:{slug}" for slug, ats in keys]
    # Find existing `disabled:` block.
    for i, line in enumerate(lines):
        m = _TOP_LEVEL_KEY_RE.match(line)
        if m and m.group(1) == "disabled":
            # Find end of this block.
            j = i + 1
            while j < len(lines) and not _TOP_LEVEL_KEY_RE.match(lines[j]):
                j += 1
            # Trim blanks.
            k = j - 1
            while k > i and lines[k].strip() == "":
                k -= 1
            insert_idx = k + 1
            head = "".join(lines[:insert_idx])
            tail = "".join(lines[insert_idx:])
            sep = "" if head.endswith("\n") else "\n"
            return head + sep + "\n".join(formatted) + "\n" + tail
    # No `disabled:` block — append a new one at the end.
    text = text.rstrip() + "\n\ndisabled:\n" + "\n".join(formatted) + "\n"
    return text


# ---------- subcommands ----------

def cmd_import(args):
    yaml_data = load_yaml()
    known = load_known_names()
    print(f"Quality gate: {len(known)} names in known_tech_companies.txt", file=sys.stderr)
    cands, fetched = collect_candidates(known)
    kept, drops = filter_candidates(cands, yaml_data)

    # Print summary table.
    print()
    print(f"{'ATS':<12} {'fetched':>8} {'kept':>6} {'present':>9} {'denylist':>9} {'excluded':>9}")
    print("-" * 60)
    grand = 0
    for ats in ("greenhouse", "lever", "ashby", "workday"):
        d = drops.get(ats, {})
        k = len(kept.get(ats, []))
        grand += k
        print(f"{ats:<12} {fetched.get(ats, 0):>8} {k:>6} "
              f"{d.get('already_present', 0):>9} {d.get('disabled', 0):>9} {d.get('excluded', 0):>9}")
    print("-" * 60)
    print(f"Would add: {grand} companies\n")

    # Show a sample so the user can sanity-check before --apply.
    for ats in ("greenhouse", "lever", "ashby", "workday"):
        if not kept.get(ats):
            continue
        print(f"sample {ats} (first 8):")
        for c in kept[ats][:8]:
            print(f"  - {c['name']}  ({c['slug']})")
        print()

    if not args.apply:
        print("(dry-run — pass --apply to write to companies.yaml)")
        return

    if grand == 0:
        print("No new companies to add.")
        return

    new_entries: list[dict] = []
    for ats in ("greenhouse", "lever", "ashby", "workday"):
        new_entries.extend(kept.get(ats, []))
    block = format_yaml_block(new_entries)
    text = COMPANIES_YAML.read_text(encoding="utf-8")
    new_text = insert_companies_block(text, block)
    COMPANIES_YAML.write_text(new_text, encoding="utf-8")
    print(f"Wrote {grand} new entries to {COMPANIES_YAML}")


def cmd_audit(args):
    """Per-company quality table from the DB. No writes."""
    from db.models import Job, get_session
    yaml_data = load_yaml()
    companies = yaml_data.get("companies") or []

    s = get_session()
    try:
        # Fetch all (company, score, scraped_at) tuples once; group in Python.
        rows = s.query(Job.company, Job.score, Job.scraped_at).all()
    finally:
        s.close()

    by_company: dict[str, dict] = {}
    for company, score, scraped_at in rows:
        rec = by_company.setdefault(company, {
            "total": 0, "scored": 0, "high": 0, "mid": 0, "last": None,
        })
        rec["total"] += 1
        if score is not None:
            rec["scored"] += 1
            if score >= 7.0:
                rec["high"] += 1
            elif score >= 5.0:
                rec["mid"] += 1
        if scraped_at and (rec["last"] is None or scraped_at > rec["last"]):
            rec["last"] = scraped_at

    rows_out = []
    for c in companies:
        name = c.get("name", "?")
        ats = c.get("ats", "?")
        rec = by_company.get(name, {"total": 0, "scored": 0, "high": 0, "mid": 0, "last": None})
        rows_out.append((name, ats, rec["total"], rec["scored"], rec["high"], rec["mid"], rec["last"]))

    # Sort: zero-job (broken) first, then ascending high-score (worst-performing first).
    rows_out.sort(key=lambda r: (r[2] > 0, r[4], r[3]))

    print(f"\n{'Company':<35} {'ATS':<11} {'total':>6} {'scored':>7} {'>=7':>4} {'>=5':>4}  last_scraped")
    print("-" * 90)
    for name, ats, total, scored, high, mid, last in rows_out:
        last_s = last.strftime("%Y-%m-%d") if last else "-"
        print(f"{name[:35]:<35} {ats:<11} {total:>6} {scored:>7} {high:>4} {mid:>4}  {last_s}")
    print("-" * 90)
    print(f"{len(rows_out)} companies in companies.yaml. {sum(1 for r in rows_out if r[2] == 0)} with zero scraped jobs.")
    print()
    print("Hint: companies with total=0 are candidates for --prune. Companies with high=0 over many runs may be off-target.")


def cmd_prune(args):
    """Flag companies with zero scraped jobs ever, optionally remove and add to disabled:."""
    from db.models import Job, get_session
    yaml_data = load_yaml()
    companies = yaml_data.get("companies") or []

    s = get_session()
    try:
        scraped = {row[0] for row in s.query(Job.company).distinct().all()}
    finally:
        s.close()

    candidates: list[dict] = [c for c in companies if c.get("name") not in scraped]
    if not candidates:
        print("No prune candidates — every company in companies.yaml has at least one scraped job.")
        return

    print(f"Prune candidates ({len(candidates)} companies with zero scraped jobs):\n")
    for c in candidates:
        print(f"  - {c.get('name')} ({c.get('ats')} / {c.get('slug')})")
    print()

    if args.dry_run:
        print("(dry-run — pass without --dry-run to remove and add to disabled:)")
        return

    resp = input(f"Remove these {len(candidates)} entries and add to disabled:? [y/N] ").strip().lower()
    if resp != "y":
        print("Aborted.")
        return

    keys = {(c["slug"].lower(), c["ats"]) for c in candidates}
    text = COMPANIES_YAML.read_text(encoding="utf-8")
    text, removed = remove_company_entries(text, keys)
    text = append_to_disabled(text, [(c["slug"], c["ats"]) for c in candidates])
    COMPANIES_YAML.write_text(text, encoding="utf-8")
    print(f"Removed {removed} entries; added {len(candidates)} to disabled:.")


# ---------- entry point ----------

def main():
    p = argparse.ArgumentParser(description=__doc__)
    action = p.add_mutually_exclusive_group()
    action.add_argument("--audit", action="store_true", help="Print per-company quality table from the DB.")
    action.add_argument("--apply", action="store_true", help="Fetch from source and write new entries to companies.yaml.")
    action.add_argument("--prune", action="store_true", help="Find dead companies and propose removal.")
    p.add_argument("--dry-run", action="store_true",
                   help="Preview only — no writes. Default when no other action is given. Modifies --prune to report-only.")
    args = p.parse_args()

    if args.audit:
        cmd_audit(args)
    elif args.prune:
        cmd_prune(args)
    else:
        # --apply or --dry-run both go through cmd_import; cmd_import writes only when args.apply is True.
        cmd_import(args)


if __name__ == "__main__":
    main()
