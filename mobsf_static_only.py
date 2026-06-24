from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

try:
    import requests
except ImportError as exc:  
    raise SystemExit(
        "Missing dependency: requests. Install with: python3 -m pip install requests"
    ) from exc


Json = Dict[str, Any]


class MobSFError(RuntimeError):
    


class MobSFClient:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        timeout: int = 600,
        verify_tls: bool = False,
        retries: int = 2,
        retry_sleep: float = 2.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.verify_tls = verify_tls
        self.retries = retries
        self.retry_sleep = retry_sleep
        self.session = requests.Session()
        self.session.headers.update({"Authorization": api_key})

    def _post(
        self,
        endpoint: str,
        *,
        data: Optional[Dict[str, Any]] = None,
        files: Optional[Dict[str, Any]] = None,
    ) -> Json:
        url = f"{self.base_url}{endpoint}"
        last_error: Optional[Exception] = None
        for attempt in range(self.retries + 1):
            try:
                response = self.session.post(
                    url,
                    data=data,
                    files=files,
                    timeout=self.timeout,
                    verify=self.verify_tls,
                )
                if not response.ok:
                    raise MobSFError(
                        f"MobSF API error {response.status_code} for {endpoint}: "
                        f"{response.text[:1000]}"
                    )
                try:
                    payload = response.json()
                except ValueError as exc:
                    raise MobSFError(
                        f"MobSF returned non-JSON response for {endpoint}: "
                        f"{response.text[:1000]}"
                    ) from exc
                if isinstance(payload, dict) and payload.get("error"):
                    raise MobSFError(f"MobSF error for {endpoint}: {payload}")
                return payload
            except (requests.RequestException, MobSFError) as exc:
                last_error = exc
                if attempt < self.retries:
                    time.sleep(self.retry_sleep)
                    continue
                raise MobSFError(str(last_error)) from last_error
        raise MobSFError(str(last_error))

    def upload(self, apk_path: Path) -> Json:
        with apk_path.open("rb") as fp:
            return self._post("/api/v1/upload", files={"file": fp})

    def scan(self, upload_result: Json) -> Json:
        scan_hash = upload_result.get("hash")
        file_name = upload_result.get("file_name") or upload_result.get("filename")
        scan_type = upload_result.get("scan_type") or "apk"
        if not scan_hash:
            raise MobSFError(f"Upload response did not contain hash: {upload_result}")
        data = {"hash": scan_hash, "scan_type": scan_type}
        if file_name:
            data["file_name"] = file_name
        return self._post("/api/v1/scan", data=data)

    def report_json(self, scan_hash: str) -> Json:
        return self._post("/api/v1/report_json", data={"hash": scan_hash})


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fp:
        for chunk in iter(lambda: fp.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_name(value: str) -> str:
    value = value.strip() or "unknown_app"
    return re.sub(r"[^A-Za-z0-9._-]+", "_", value)[:160]


def write_json(path: Path, data: Any, indent: int = 2) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fp:
        json.dump(data, fp, indent=indent, ensure_ascii=False, sort_keys=False)


def write_jsonl(path: Path, rows: Iterable[Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fp:
        for row in rows:
            fp.write(json.dumps(row, ensure_ascii=False, sort_keys=False) + "\n")


def flatten_for_csv(value: Any) -> Any:
    if isinstance(value, (dict, list, tuple, set)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return value


def write_csv(path: Path, rows: List[Json]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames: List[str] = []
    for row in rows:
        for key in row.keys():
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", encoding="utf-8", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: flatten_for_csv(row.get(k)) for k in fieldnames})


def as_list(value: Any) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, set):
        return sorted(value)
    return [value]


def get_first(report: Json, keys: Iterable[str], default: Any = None) -> Any:
    for key in keys:
        if key in report and report[key] not in (None, ""):
            return report[key]
    return default


def extract_metadata(report: Json, apk_path: Path, upload_result: Json) -> Json:
    metadata = {
        "apk_path": str(apk_path),
        "apk_file_name": apk_path.name,
        "local_sha256": sha256_file(apk_path),
        "mobsf_hash": upload_result.get("hash"),
        "scan_type": upload_result.get("scan_type") or report.get("scan_type") or "apk",
        "app_name": get_first(report, ["app_name", "title", "file_name"]),
        "package_name": get_first(report, ["package_name", "packagename", "package"]),
        "version_name": get_first(report, ["version_name", "version"]),
        "version_code": get_first(report, ["version_code"]),
        "min_sdk": get_first(report, ["min_sdk", "min_sdk_version"]),
        "target_sdk": get_first(report, ["target_sdk", "target_sdk_version"]),
        "main_activity": get_first(report, ["main_activity"]),
        "md5": get_first(report, ["md5"]),
        "sha1": get_first(report, ["sha1"]),
        "sha256": get_first(report, ["sha256"]),
        "size": get_first(report, ["size"]),
    }
    return metadata


def normalize_permission_meta(permission: str, meta: Any) -> Json:
    row: Json = {"permission": permission, "raw": meta}
    if isinstance(meta, dict):
        row.update(
            {
                "status": meta.get("status") or meta.get("protection_level"),
                "info": meta.get("info"),
                "description": meta.get("description") or meta.get("desc"),
            }
        )
    elif isinstance(meta, str):
        row["status"] = meta
    elif isinstance(meta, (list, tuple)):
        row["status"] = meta[0] if len(meta) > 0 else None
        row["info"] = meta[1] if len(meta) > 1 else None
        row["description"] = meta[2] if len(meta) > 2 else None
    return row


def extract_permissions(report: Json) -> List[Json]:
    permissions = report.get("permissions") or report.get("android_permissions") or {}
    rows: List[Json] = []
    if isinstance(permissions, dict):
        for permission, meta in sorted(permissions.items()):
            rows.append(normalize_permission_meta(permission, meta))
    elif isinstance(permissions, list):
        for item in permissions:
            if isinstance(item, dict):
                permission = (
                    item.get("permission")
                    or item.get("name")
                    or item.get("perm")
                    or json.dumps(item, sort_keys=True)
                )
                row = {"permission": permission, "raw": item}
                row.update({k: item.get(k) for k in ("status", "info", "description", "protection_level")})
                rows.append(row)
            else:
                rows.append({"permission": str(item), "raw": item})
    return rows


def is_dangerous_permission(row: Json) -> bool:
    blob = json.dumps(row, ensure_ascii=False).lower()
    return "dangerous" in blob or "signatureorsystem" in blob


def extract_trackers(report: Json) -> List[Json]:
    trackers = report.get("trackers")
    rows: List[Json] = []

    def add_tracker(item: Any, source_key: str) -> None:
        if isinstance(item, dict):
            row = dict(item)
            row["source_key"] = source_key
            rows.append(row)
        else:
            rows.append({"name": str(item), "source_key": source_key, "raw": item})

    if isinstance(trackers, dict):
        for key, value in trackers.items():
            if isinstance(value, list):
                for item in value:
                    add_tracker(item, key)
            elif isinstance(value, dict):
                add_tracker(value, key)
            elif key.lower() in {"detected_trackers", "trackers"}:
                for item in as_list(value):
                    add_tracker(item, key)
    elif isinstance(trackers, list):
        for item in trackers:
            add_tracker(item, "trackers")

    # Deduplicate by normalized JSON.
    seen = set()
    deduped: List[Json] = []
    for row in rows:
        key = json.dumps(row, sort_keys=True, ensure_ascii=False)
        if key not in seen:
            seen.add(key)
            deduped.append(row)
    return deduped


def extract_native_libraries(report: Json) -> List[Json]:
    rows: List[Json] = []
    file_analysis = report.get("file_analysis") or report.get("files") or report.get("apk_files")

    def consider_path(path: str, meta: Any = None) -> None:
        path_str = str(path)
        lowered = path_str.lower()
        if ".so" in lowered or lowered.startswith("lib/") or "/lib/" in lowered:
            rows.append({"path": path_str, "raw": meta})

    if isinstance(file_analysis, dict):
        for path, meta in file_analysis.items():
            consider_path(path, meta)
    elif isinstance(file_analysis, list):
        for item in file_analysis:
            if isinstance(item, dict):
                path = item.get("file") or item.get("path") or item.get("name") or item.get("filename")
                if path:
                    consider_path(path, item)
            else:
                consider_path(str(item), item)
    return rows


def extract_libraries(report: Json) -> List[Json]:
    
    rows: List[Json] = []
    candidate_keys = [
        "libraries",
        "third_party_libs",
        "dependencies",
        "android_libraries",
        "detected_libraries",
        "frameworks",
    ]

    def add(value: Any, source_key: str) -> None:
        if isinstance(value, dict):
            name = value.get("name") or value.get("library") or value.get("title")
            row = dict(value)
            if name:
                row["name"] = name
            row["source_key"] = source_key
            rows.append(row)
        elif isinstance(value, str):
            rows.append({"name": value, "source_key": source_key})
        else:
            rows.append({"name": str(value), "source_key": source_key, "raw": value})

    for key in candidate_keys:
        value = report.get(key)
        if not value:
            continue
        if isinstance(value, dict):
            for lib_name, meta in value.items():
                if isinstance(meta, dict):
                    row = dict(meta)
                    row.setdefault("name", lib_name)
                    row["source_key"] = key
                    rows.append(row)
                else:
                    rows.append({"name": str(lib_name), "source_key": key, "raw": meta})
        elif isinstance(value, list):
            for item in value:
                add(item, key)
        else:
            add(value, key)

    
    for tracker in extract_trackers(report):
        tracker_name = (
            tracker.get("name")
            or tracker.get("tracker")
            or tracker.get("title")
            or tracker.get("company")
            or "unknown_tracker"
        )
        rows.append({
            "name": tracker_name,
            "source_key": "trackers",
            "category": "tracker_or_sdk",
            "raw": tracker,
        })

    for native_lib in extract_native_libraries(report):
        rows.append({
            "name": Path(native_lib.get("path", "unknown_native_lib")).name,
            "path": native_lib.get("path"),
            "source_key": "native_libraries",
            "category": "native_library",
            "raw": native_lib.get("raw"),
        })

    seen = set()
    deduped: List[Json] = []
    for row in rows:
        key = json.dumps(row, sort_keys=True, ensure_ascii=False)
        if key not in seen:
            seen.add(key)
            deduped.append(row)
    return deduped


def extract_urls_and_domains(report: Json) -> Tuple[List[Json], List[Json]]:
    urls: List[Json] = []
    domains: List[Json] = []

    def add_url(item: Any, source_key: str) -> None:
        if isinstance(item, dict):
            row = dict(item)
            row["source_key"] = source_key
            urls.append(row)
        else:
            urls.append({"url": str(item), "source_key": source_key})

    def add_domain(item: Any, source_key: str) -> None:
        if isinstance(item, dict):
            row = dict(item)
            row["source_key"] = source_key
            domains.append(row)
        else:
            domains.append({"domain": str(item), "source_key": source_key})

    for key in ["urls", "firebase_urls"]:
        value = report.get(key)
        if isinstance(value, dict):
            for url, meta in value.items():
                row = {"url": str(url), "source_key": key, "raw": meta}
                urls.append(row)
        elif isinstance(value, list):
            for item in value:
                add_url(item, key)
        elif value:
            add_url(value, key)

    value = report.get("domains")
    if isinstance(value, dict):
        for domain, meta in value.items():
            domains.append({"domain": str(domain), "source_key": "domains", "raw": meta})
    elif isinstance(value, list):
        for item in value:
            add_domain(item, "domains")
    elif value:
        add_domain(value, "domains")

    return urls, domains


def analyze_one_apk(
    client: MobSFClient,
    apk_path: Path,
    output_root: Path,
    *,
    write_raw: bool,
    json_indent: int,
) -> Json:
    apk_path = apk_path.expanduser().resolve()
    if not apk_path.exists():
        raise FileNotFoundError(f"APK not found: {apk_path}")
    if not apk_path.is_file():
        raise FileNotFoundError(f"APK path is not a file: {apk_path}")

    upload_result = client.upload(apk_path)
    scan_hash = upload_result.get("hash")
    if not scan_hash:
        raise MobSFError(f"Upload did not return a hash: {upload_result}")

    scan_result = client.scan(upload_result)
    report = client.report_json(scan_hash)

    metadata = extract_metadata(report, apk_path, upload_result)
    package_or_name = metadata.get("package_name") or metadata.get("app_name") or apk_path.stem
    app_out = output_root / safe_name(str(package_or_name))
    app_out.mkdir(parents=True, exist_ok=True)

    permissions = extract_permissions(report)
    trackers = extract_trackers(report)
    libraries = extract_libraries(report)
    native_libraries = extract_native_libraries(report)
    urls, domains = extract_urls_and_domains(report)

    static_summary = {
        **metadata,
        "output_dir": str(app_out),
        "permissions_total": len(permissions),
        "dangerous_permissions_total": sum(1 for row in permissions if is_dangerous_permission(row)),
        "trackers_total": len(trackers),
        "libraries_total": len(libraries),
        "native_libraries_total": len(native_libraries),
        "urls_total": len(urls),
        "domains_total": len(domains),
        "analysis_status": "ok",
    }

    write_json(app_out / "mobsf_upload.json", upload_result, indent=json_indent)
    write_json(app_out / "mobsf_scan.json", scan_result, indent=json_indent)
    write_json(app_out / "app_metadata.json", metadata, indent=json_indent)
    write_json(app_out / "permissions.json", permissions, indent=json_indent)
    write_csv(app_out / "permissions.csv", permissions)
    write_json(app_out / "trackers.json", trackers, indent=json_indent)
    write_csv(app_out / "trackers.csv", trackers)
    write_json(app_out / "libraries.json", libraries, indent=json_indent)
    write_csv(app_out / "libraries.csv", libraries)
    write_json(app_out / "native_libraries.json", native_libraries, indent=json_indent)
    write_csv(app_out / "native_libraries.csv", native_libraries)
    write_json(app_out / "urls.json", urls, indent=json_indent)
    write_csv(app_out / "urls.csv", urls)
    write_json(app_out / "domains.json", domains, indent=json_indent)
    write_csv(app_out / "domains.csv", domains)
    write_json(app_out / "static_summary.json", static_summary, indent=json_indent)

    if write_raw:
        write_json(app_out / "mobsf_report_raw.json", report, indent=json_indent)

    return static_summary


def read_apps_csv(path: Path, apk_column: str) -> List[Path]:
    with path.open("r", encoding="utf-8-sig", newline="") as fp:
        reader = csv.DictReader(fp)
        if not reader.fieldnames:
            raise ValueError(f"CSV has no header: {path}")
        if apk_column not in reader.fieldnames:
            raise ValueError(
                f"CSV column {apk_column!r} not found. Columns: {', '.join(reader.fieldnames)}"
            )
        apk_paths = []
        for line_no, row in enumerate(reader, start=2):
            raw_path = (row.get(apk_column) or "").strip()
            if not raw_path:
                print(f"[warn] Skipping line {line_no}: empty {apk_column}", file=sys.stderr)
                continue
            apk_paths.append(Path(raw_path))
        return apk_paths


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run MobSF static-only analysis for one APK or a CSV of APKs."
    )
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--apk", type=Path)
    input_group.add_argument(
        "--apps-csv",
        type=Path="CSV containing APK paths. Default expected column: apk_path.",
    )
    parser.add_argument(
        "--apk-column",
        default="apk_path"
    )
    parser.add_argument(
        "--mobsf-url",
        default=os.getenv("MOBSF_URL", "http://127.0.0.1:8000")
    )
    parser.add_argument(
        "--api-key",
        default=os.getenv("MOBSF_API_KEY")
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("results/static")
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=600
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=2
    )
    parser.add_argument(
        "--verify-tls",
        action="store_true"
    )
    parser.add_argument(
        "--no-raw-report",
        action="store_true"
    )
    parser.add_argument(
        "--json-indent",
        type=int,
        default=2
    )
    parser.add_argument(
        "--stop-on-error",
        action="store_true"
    )
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    if not args.api_key:
        print(
            "Error: MobSF API key is required. Pass --api-key or set MOBSF_API_KEY.",
            file=sys.stderr,
        )
        return 2

    if args.apk:
        apk_paths = [args.apk]
    else:
        apk_paths = read_apps_csv(args.apps_csv, args.apk_column)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    client = MobSFClient(
        base_url=args.mobsf_url,
        api_key=args.api_key,
        timeout=args.timeout,
        verify_tls=args.verify_tls,
        retries=args.retries,
    )

    summaries: List[Json] = []
    errors: List[Json] = []

    for index, apk_path in enumerate(apk_paths, start=1):
        print(f"[{index}/{len(apk_paths)}] Static analysis: {apk_path}", flush=True)
        try:
            summary = analyze_one_apk(
                client,
                apk_path,
                args.out_dir,
                write_raw=not args.no_raw_report,
                json_indent=max(args.json_indent, 0),
            )
            summaries.append(summary)
            print(
                f"  ok: {summary.get('package_name') or summary.get('app_name')} "
                f"permissions={summary['permissions_total']} "
                f"libraries={summary['libraries_total']} "
                f"trackers={summary['trackers_total']}",
                flush=True,
            )
        except Exception as exc:  # intentionally broad to keep batch runs alive
            error_row = {
                "apk_path": str(apk_path),
                "analysis_status": "error",
                "error_type": type(exc).__name__,
                "error": str(exc),
            }
            errors.append(error_row)
            summaries.append(error_row)
            print(f"  error: {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
            if args.stop_on_error:
                break

    write_json(args.out_dir / "static_batch_summary.json", summaries)
    write_csv(args.out_dir / "static_batch_summary.csv", summaries)
    write_json(args.out_dir / "static_batch_errors.json", errors)
    write_csv(args.out_dir / "static_batch_errors.csv", errors)

    print(f"\nWrote summary: {args.out_dir / 'static_batch_summary.csv'}")
    if errors:
        print(f"Completed with {len(errors)} error(s). See: {args.out_dir / 'static_batch_errors.csv'}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
