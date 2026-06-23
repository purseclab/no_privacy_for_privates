import sys
import csv
import pandas as pd
from collections import defaultdict
import statistics

# ---------------------------------------------------------------------------
# MAPPINGS
# ---------------------------------------------------------------------------

PERMISSION_TO_Q17 = {
    "CAMERA": "Permission: Access Camera",
    "ACCESS_COARSE_LOCATION": "Permission: Access Approximate Location",
    "ACCESS_FINE_LOCATION": "Permission: Access Fine Location",
    "ACCESS_BACKGROUND_LOCATION": "Permission: Access Background Location",
    "CALL_PHONE": "Permission: Make / Manage Phone Calls",
    "RECORD_AUDIO": "Permission: Record Audio",
    "READ_CONTACTS": "Permission: Access Contacts",
    "WRITE_CONTACTS": "Permission: Access Contacts",
    "READ_SMS": "Permission: Access SMS / iMessages",
    "SEND_SMS": "Permission: Access SMS / iMessages",
    "RECEIVE_SMS": "Permission: Access SMS / iMessages",
    "ACTIVITY_RECOGNITION": "Permission: Access Health and Fitness Data",
    "BODY_SENSORS": "Permission: Access Health and Fitness Data",
    "BODY_SENSORS_BACKGROUND": "Permission: Access Health and Fitness Data",
}

PII_TO_Q17 = {
    "Name": "Name",
    "Address": "Address",
    "Email": "Email Address",
    "Phone": "Phone Number",
    "Branch": "Branch",
    "Age": "Age",
    "Birth Date": "DOB",
    "Gender": "Gender",
    "Sexual Orientation": "Sexual Orientation",
    "Income": "Financial Information",
    "Credit Score": "Financial Information",
    "Net Worth": "Financial Information",
    "Installation": "Military Base / Installation",
}
PII_NO_Q17 = {"SSN", "Marital", "Occupation", "Family Size", "Children"}

Q17_INDEX_TO_LABEL = {
    0:  "Email Address",
    1:  "Name",
    2:  "Phone Number",
    3:  "Military Base / Installation",
    4:  "Branch",
    5:  "Address",
    6:  "DOB",
    7:  "Gender",
    8:  "Sexual Orientation",
    9:  "Age",
    10: "Financial Information",
    11: "App Activity",
    12: "Device Identifiers",
    13: "Permission: Access Camera",
    14: "Permission: Access Approximate Location",
    15: "Permission: Access Fine Location",
    16: "Permission: Access Background Location",
    17: "Permission: Make / Manage Phone Calls",
    18: "Permission: Record Audio",
    19: "Permission: Access Contacts",
    20: "Permission: Access Health and Fitness Data",
    21: "Permission: Access SMS / iMessages",
}
Q17_LABEL_TO_INDEX = {v: k for k, v in Q17_INDEX_TO_LABEL.items()}

UNCOMFORTABLE_VALUES = {"Extremely uncomfortable", "Somewhat uncomfortable"}
EXPECTED_Q17_VALUES = {
    "Extremely uncomfortable",
    "Somewhat uncomfortable",
    "Neither comfortable nor uncomfortable",
    "Somewhat comfortable",
    "Extremely comfortable",
}

# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------

def is_health_permission(perm):
    return "health" in perm.lower()

def get_q17_label_for_permission(perm):
    perm_upper = perm.strip().upper()
    if perm_upper in PERMISSION_TO_Q17:
        return PERMISSION_TO_Q17[perm_upper]
    if is_health_permission(perm):
        return "Permission: Access Health and Fitness Data"
    return None

def parse_permissions(raw):
    if pd.isna(raw):
        return []
    raw = str(raw).strip()
    if not raw or raw.lower() in ("no report found", "no permissions found"):
        return []
    parts = [p.strip() for p in raw.split(",")]
    if all(len(p) <= 1 for p in parts if p):
        return []
    return [p.strip() for p in parts if p.strip()]

# ---------------------------------------------------------------------------
# LOAD APP NAME MAPPING
# ---------------------------------------------------------------------------

def load_app_name_mapping(path):
    try:
        df = pd.read_csv(path)
    except Exception as e:
        print(f"[ERROR] Could not read app name mapping file: {e}")
        sys.exit(1)

    df.columns = df.columns.str.strip()
    required = {"link", "Title", "pii_name_match"}
    if not required.issubset(set(df.columns)):
        print(f"[ERROR] app_name_matches.csv must have columns: {required}. Found: {list(df.columns)}")
        sys.exit(1)

    title_to_pii = {}
    unmatched_pii_only = []

    for _, row in df.iterrows():
        title = str(row["Title"]).strip()
        pii_match = str(row["pii_name_match"]).strip()

        if not title or title.lower() == "nan":
            if pii_match and pii_match.lower() != "nan":
                unmatched_pii_only.append(pii_match)
            continue

        if pii_match and pii_match.lower() != "nan":
            title_to_pii[title.lower()] = pii_match
        else:
            print(f"[INFO] No PII match for app: '{title}' — will attempt direct name lookup.")

    if unmatched_pii_only:
        print(f"[INFO] {len(unmatched_pii_only)} PII app name(s) in mapping file had no matching Title.")
        for name in unmatched_pii_only:
            print(f"  [UNMATCHED PII] '{name}'")

    print(f"[INFO] Loaded {len(title_to_pii)} app name mappings from {path}.")
    return title_to_pii

def resolve_app_name(app_name, title_to_pii):
    key = app_name.lower()
    if key in title_to_pii:
        return title_to_pii[key]
    return app_name

# ---------------------------------------------------------------------------
# LOAD REFERENCE DATA
# ---------------------------------------------------------------------------

def load_pii_collection(path):
    try:
        df = pd.read_csv(path)
    except Exception as e:
        print(f"[ERROR] Could not read pii_collection: {e}")
        sys.exit(1)

    df.columns = df.columns.str.strip()
    app_col = df.columns[0]
    app_pii = {}

    for _, row in df.iterrows():
        app_name = str(row[app_col]).strip()
        if not app_name or app_name.lower() == "nan":
            continue
        q17_labels = []
        for pii_col, q17_label in PII_TO_Q17.items():
            if pii_col in df.columns:
                val = str(row.get(pii_col, "")).strip()
                if val in {"Y", "N", "P"} and q17_label not in q17_labels:
                    q17_labels.append(q17_label)
        app_pii[app_name.lower()] = (app_name, q17_labels)

    print(f"[INFO] Loaded PII data for {len(app_pii)} apps from {path}.")
    return app_pii

def load_permission_collection(path):
    try:
        df = pd.read_csv(path)
    except Exception as e:
        print(f"[ERROR] Could not read permission_collection: {e}")
        sys.exit(1)

    df.columns = df.columns.str.strip()
    if "App" not in df.columns or "Permissions" not in df.columns:
        print(f"[ERROR] permission_collection must have 'App' and 'Permissions' columns. Found: {list(df.columns)}")
        sys.exit(1)

    app_perms = {}
    unmapped_permissions = set()

    for _, row in df.iterrows():
        app_name = str(row["App"]).strip()
        if not app_name or app_name.lower() == "nan":
            continue
        perms = parse_permissions(row["Permissions"])
        q17_labels = []
        for perm in perms:
            label = get_q17_label_for_permission(perm)
            if label:
                if label not in q17_labels:
                    q17_labels.append(label)
            else:
                unmapped_permissions.add(perm)
        app_perms[app_name.lower()] = (app_name, q17_labels)

    print(f"[INFO] Loaded permission data for {len(app_perms)} apps from {path}.")
    print(f"[INFO] {len(unmapped_permissions)} unique permission(s) have no Q17 mapping (see unmapped_permissions.txt).")
    return app_perms, unmapped_permissions

# ---------------------------------------------------------------------------
# PROCESS RESPONSE CSVs
# ---------------------------------------------------------------------------

def load_response_csv(path):
    try:
        with open(path, newline="", encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            rows = list(reader)
    except Exception as e:
        print(f"[ERROR] Could not read response CSV {path}: {e}")
        sys.exit(1)

    if len(rows) < 4:
        print(f"[WARNING] Response CSV {path} has fewer than 4 rows — skipping.")
        return None, None, []

    machine_headers = rows[0]
    human_headers = rows[1]
    data_rows = rows[3:]

    records = []
    for row in data_rows:
        if not any(cell.strip() for cell in row):
            continue
        record = {}
        for i, val in enumerate(row):
            if i < len(machine_headers):
                record[machine_headers[i]] = val.strip()
        records.append(record)

    return machine_headers, human_headers, records

def extract_q12_app_map(machine_headers, human_headers):
    q12_map = {}
    for i, col in enumerate(machine_headers):
        if col.startswith("Q12_"):
            human = human_headers[i] if i < len(human_headers) else ""
            if " - " in human:
                app_name = human.rsplit(" - ", 1)[-1].strip()
            else:
                app_name = human.strip()
            if app_name:
                q12_map[col] = app_name
            else:
                print(f"[WARNING] Could not extract app name from Q12 human header for column '{col}': '{human}'")
    return q12_map

def get_q17_values(record, machine_headers):
    q17_cols = [col for col in machine_headers if col.startswith("Q17_")]
    q17_cols_sorted = sorted(q17_cols, key=lambda c: int(c.split("_")[1]))
    values = []
    for col in q17_cols_sorted:
        val = record.get(col, "").strip()
        values.append(val if val else None)
    return values

# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) < 5:
        print("Usage: python behavior-uncomfortability_discrepancy.py pii_collection.csv permission_collection_named.csv app_name_matches.csv responses1.csv [responses2.csv ...]")
        sys.exit(1)

    pii_path = sys.argv[1]
    perm_path = sys.argv[2]
    mapping_path = sys.argv[3]
    response_paths = sys.argv[4:]

    app_pii = load_pii_collection(pii_path)
    app_perms, unmapped_permissions = load_permission_collection(perm_path)
    title_to_pii = load_app_name_mapping(mapping_path)

    with open("unmapped_permissions.txt", "w") as f:
        for perm in sorted(unmapped_permissions):
            f.write(perm + "\n")
    print(f"[INFO] unmapped_permissions.txt written with {len(unmapped_permissions)} entries.")

    all_output_rows = []
    all_output_cols = set(["response_id", "app_name"])
    txt_lines = []

    uncomfortable_app_counts = []
    comfortable_only_app_counts = []

    # Track successfully mapped apps across all participants (unique app names)
    successfully_mapped_apps = set()
    # Track (participant, app) pairs that were successfully compared
    total_participant_app_comparisons = 0

    for rpath in response_paths:
        print(f"[INFO] Processing response file: {rpath}")
        machine_headers, human_headers, records = load_response_csv(rpath)
        if not records:
            print(f"[WARNING] No data records found in {rpath} — skipping.")
            continue

        q12_map = extract_q12_app_map(machine_headers, human_headers)
        if not q12_map:
            print(f"[WARNING] No Q12 columns found in {rpath}.")

        for record in records:
            response_id = record.get("ResponseId", "").strip()
            if not response_id:
                print(f"[WARNING] Found a record with no ResponseId — skipping.")
                continue

            q17_values = get_q17_values(record, machine_headers)
            for i, val in enumerate(q17_values):
                if val and val not in EXPECTED_Q17_VALUES:
                    label = Q17_INDEX_TO_LABEL.get(i, f"Q17_{i+1}")
                    print(f"[WARNING] Participant {response_id}: unexpected Q17 value for '{label}': '{val}'")

            def get_comfortability(q17_label):
                idx = Q17_LABEL_TO_INDEX.get(q17_label)
                if idx is None:
                    return None
                if idx >= len(q17_values):
                    return "N/A"
                val = q17_values[idx]
                return val if val else "N/A"

            used_apps = []
            for col, app_name in q12_map.items():
                response = record.get(col, "").strip()
                if response and response.lower() != "never":
                    used_apps.append(app_name)

            if not used_apps:
                print(f"[WARNING] Participant {response_id}: no apps used (all 'Never' or blank).")

            apps_with_uncomfortable = set()
            apps_with_no_uncomfortable = set()
            uncomfortable_instances = 0

            for app_name in used_apps:
                resolved_name = resolve_app_name(app_name, title_to_pii)
                if resolved_name.lower() != app_name.lower():
                    print(f"[INFO] Participant {response_id}: '{app_name}' resolved to '{resolved_name}' via mapping.")
                resolved_key = resolved_name.lower()

                pii_entry = app_pii.get(resolved_key)
                if pii_entry is None:
                    print(f"[WARNING] Participant {response_id}: app '{app_name}' (resolved: '{resolved_name}') not found in pii_collection.")
                    pii_q17_labels = []
                else:
                    pii_q17_labels = pii_entry[1]

                perm_entry = app_perms.get(resolved_key)
                if perm_entry is None:
                    perm_entry = app_perms.get(app_name.lower())
                if perm_entry is None:
                    print(f"[WARNING] Participant {response_id}: app '{app_name}' (resolved: '{resolved_name}') not found in permission_collection.")
                    perm_q17_labels = []
                else:
                    perm_q17_labels = perm_entry[1]

                # An app is "successfully mapped" if it was found in at least one reference file
                found_in_pii = pii_entry is not None
                found_in_perms = perm_entry is not None
                if found_in_pii or found_in_perms:
                    successfully_mapped_apps.add(resolved_name)
                    total_participant_app_comparisons += 1

                combined_labels = list(dict.fromkeys(pii_q17_labels + perm_q17_labels))

                if not combined_labels:
                    row = {"response_id": response_id, "app_name": app_name}
                    all_output_rows.append(row)
                    apps_with_no_uncomfortable.add(app_name)
                    continue

                row = {"response_id": response_id, "app_name": app_name}
                app_has_uncomfortable = False

                for label in combined_labels:
                    comfort = get_comfortability(label)
                    row[label] = comfort
                    all_output_cols.add(label)
                    if comfort in UNCOMFORTABLE_VALUES:
                        uncomfortable_instances += 1
                        app_has_uncomfortable = True

                if app_has_uncomfortable:
                    apps_with_uncomfortable.add(app_name)
                else:
                    apps_with_no_uncomfortable.add(app_name)

                all_output_rows.append(row)

            uncomfortable_app_counts.append(len(apps_with_uncomfortable))
            comfortable_only_app_counts.append(len(apps_with_no_uncomfortable))

            txt_lines.append(
                f"{response_id} | apps_with_uncomfortable_collection: {len(apps_with_uncomfortable)} | "
                f"uncomfortable_pii_permission_instances: {uncomfortable_instances}"
            )

    # Write output.csv
    ordered_q17_cols = list(Q17_INDEX_TO_LABEL.values())
    data_cols = [c for c in ordered_q17_cols if c in all_output_cols]
    final_cols = ["response_id", "app_name"] + data_cols

    with open("output.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=final_cols, extrasaction="ignore")
        writer.writeheader()
        for row in all_output_rows:
            writer.writerow(row)
    print(f"[INFO] output.csv written with {len(all_output_rows)} rows.")

    # Compute aggregate stats
    total_participants = len(txt_lines)
    participants_with_uncomfortable = sum(1 for c in uncomfortable_app_counts if c > 0)
    participants_without_uncomfortable = sum(1 for c in uncomfortable_app_counts if c == 0)

    avg_uncomfortable = statistics.mean(uncomfortable_app_counts) if uncomfortable_app_counts else 0
    std_uncomfortable = statistics.stdev(uncomfortable_app_counts) if len(uncomfortable_app_counts) > 1 else 0

    avg_comfortable_only = statistics.mean(comfortable_only_app_counts) if comfortable_only_app_counts else 0
    std_comfortable_only = statistics.stdev(comfortable_only_app_counts) if len(comfortable_only_app_counts) > 1 else 0

    # Write output.txt
    with open("output.txt", "w", encoding="utf-8") as f:
        for line in txt_lines:
            f.write(line + "\n")
        f.write("\n")
        f.write("--- MAPPING SUMMARY ---\n")
        f.write(f"Unique apps successfully mapped and compared: {len(successfully_mapped_apps)}\n")
        f.write(f"Total participant-app comparisons performed: {total_participant_app_comparisons}\n")
        f.write("\n")
        f.write("--- AGGREGATE SUMMARY ---\n")
        f.write(f"Total participants: {total_participants}\n")
        f.write(f"Participants who use at least one app they are uncomfortable with: {participants_with_uncomfortable}\n")
        f.write(f"Participants who use no apps they are uncomfortable with: {participants_without_uncomfortable}\n")
        f.write(f"Avg apps per participant that do something uncomfortable: {avg_uncomfortable:.2f} (std dev: {std_uncomfortable:.2f})\n")
        f.write(f"Avg apps per participant that do nothing uncomfortable: {avg_comfortable_only:.2f} (std dev: {std_comfortable_only:.2f})\n")

    print(f"[INFO] output.txt written with {total_participants} participant summaries and aggregate stats.")

if __name__ == "__main__":
    main()

