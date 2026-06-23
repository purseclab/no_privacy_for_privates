#!/usr/bin/env python3
"""
first-party_code_provenance.py
Usage: python first-party_code_provenance.py <path_to_json_file> [--verbose]
"""

import sys
import re
from collections import Counter, defaultdict


COUNTRY_PATTERNS = [
    ("united states", "United States"),
    ("united kingdom", "United Kingdom"),
    ("canada", "Canada"),
    ("spain", "Spain"),
    ("pakistan", "Pakistan"),
    ("türkiye", "Turkey"),
    ("turkey", "Turkey"),
    ("china", "China"),
    ("india", "India"),
    ("indonesia", "Indonesia"),
    ("vietnam", "Vietnam"),
    ("greece", "Greece"),
    ("argentina", "Argentina"),
    ("uzbekistan", "Uzbekistan"),
    ("colombia", "Colombia"),
    ("armenia", "Armenia"),
    ("australia", "Australia"),
    ("brazil", "Brazil"),
    ("germany", "Germany"),
    ("france", "France"),
    ("netherlands", "Netherlands"),
    ("russia", "Russia"),
    ("ukraine", "Ukraine"),
    ("poland", "Poland"),
    ("sweden", "Sweden"),
    ("norway", "Norway"),
    ("denmark", "Denmark"),
    ("finland", "Finland"),
    ("italy", "Italy"),
    ("portugal", "Portugal"),
    ("mexico", "Mexico"),
    ("japan", "Japan"),
    ("south korea", "South Korea"),
    ("singapore", "Singapore"),
    ("philippines", "Philippines"),
    ("thailand", "Thailand"),
    ("malaysia", "Malaysia"),
    ("new zealand", "New Zealand"),
    ("south africa", "South Africa"),
    ("nigeria", "Nigeria"),
    ("kenya", "Kenya"),
    ("israel", "Israel"),
    ("saudi arabia", "Saudi Arabia"),
    ("united arab emirates", "United Arab Emirates"),
    ("bangladesh", "Bangladesh"),
    ("sri lanka", "Sri Lanka"),
    ("nepal", "Nepal"),
    ("romania", "Romania"),
    ("czech republic", "Czech Republic"),
    ("hungary", "Hungary"),
    ("austria", "Austria"),
    ("switzerland", "Switzerland"),
    ("belgium", "Belgium"),
]


def extract_country(addr: str) -> str | None:
    """Returns country string, or None if unrecognized."""
    if not addr or addr.strip() == "" or addr == "MISSING":
        return "Unknown/Missing"
    addr_lower = addr.lower()
    for key, country in COUNTRY_PATTERNS:
        if key in addr_lower:
            return country
    return None


def parse_js_style_json(raw: str) -> list[dict]:
    records = []
    blocks = re.split(r'(?=\{\n\s*appId:)', raw)
    for block in blocks:
        app_id_m = re.search(r"appId:\s*'([^']*)'", block)
        dev_m = re.search(r"developer:\s*'([^']*)'", block)
        addr_m = re.search(r"developerLegalAddress:\s*'([^']*)'", block)
        legal_name_m = re.search(r"developerLegalName:\s*'([^']*)'", block)

        if not app_id_m:
            continue

        records.append({
            "appId": app_id_m.group(1),
            "developer": dev_m.group(1) if dev_m else "",
            "developerLegalName": legal_name_m.group(1) if legal_name_m else "",
            "developerLegalAddress": addr_m.group(1) if addr_m else "MISSING",
        })
    return records


def main():
    args = sys.argv[1:]

    if not args or "--help" in args:
        print("Usage: python first-party_code_provenance.py <path_to_json_file> [--verbose]")
        sys.exit(0)

    verbose = "--verbose" in args
    positional = [a for a in args if not a.startswith("--")]

    if not positional:
        print("Error: No input file provided.")
        sys.exit(1)

    input_path = positional[0]

    try:
        with open(input_path, "r", encoding="utf-8") as f:
            raw = f.read()
    except FileNotFoundError:
        print(f"Error: File '{input_path}' not found.")
        sys.exit(1)

    records = parse_js_style_json(raw)

    if not records:
        print("No records parsed. Check that the file format matches expected JS-style object notation.")
        sys.exit(1)

    # Assign country, flag unrecognized addresses to stdout
    unrecognized = []
    apps_by_country = defaultdict(list)

    for r in records:
        country = extract_country(r["developerLegalAddress"])
        if country is None:
            unrecognized.append((r["appId"], r["developerLegalAddress"]))
            country = "Unrecognized"
        r["country"] = country
        apps_by_country[country].append(r["appId"])

    if unrecognized:
        print("UNRECOGNIZED ADDRESSES — add these to COUNTRY_PATTERNS:")
        for app_id, addr in unrecognized:
            print(f"  [{app_id}] '{addr}'")
        print()

    total_apps = len(records)
    country_counts = Counter({c: len(apps) for c, apps in apps_by_country.items()})

    lines = []
    lines.append("=" * 50)
    lines.append("DEVELOPER GEOGRAPHIC ORIGIN ANALYSIS")
    lines.append(f"Total apps: {total_apps}")
    lines.append("=" * 50)
    lines.append("")

    for country, count in country_counts.most_common():
        pct = (count / total_apps) * 100
        lines.append(f"{country}: {count} ({pct:.1f}%)")
        if verbose and country != "United States":
            for app_id in apps_by_country[country]:
                lines.append(f"  - {app_id}")

    output_path = "output.txt"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print(f"Done. Results written to '{output_path}'.")


if __name__ == "__main__":
    main()

