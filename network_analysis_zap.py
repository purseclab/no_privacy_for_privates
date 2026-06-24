from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import ipaddress
import json
import os
import re
import signal
import subprocess
import sys
import time
import urllib.parse
from collections import Counter, defaultdict
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

try:
    import requests
except ImportError as exc:
    raise SystemExit("Missing dependency: requests. Install with: pip3 install requests") from exc


DEFAULT_DUMMY_PII: Dict[str, str] = {
    #should match default dummy PII in crawler
}

LOCATION_TERMS = [
    "lat",
    "latitude",
    "lon",
    "lng",
    "long",
    "longitude",
    "geo",
    "geolocation",
    "gps",
    "location",
    "loc",
    "coord",
    "coordinates",
    "altitude",
    "accuracy",
]

LAT_LON_PAIR_RE = re.compile(
    r"(?<![\d.])"
    r"(?P<lat>[-+]?(?:[1-8]?\d(?:\.\d+)?|90(?:\.0+)?))"
    r"\s*[,;| ]\s*"
    r"(?P<lon>[-+]?(?:180(?:\.0+)?|(?:1[0-7]\d|\d{1,2})(?:\.\d+)?))"
    r"(?![\d.])"
)
IPV4_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")

KNOWN_THIRD_PARTY_DOMAIN_HINTS = [
    "google-analytics.com",
    "analytics.google.com",
    "app-measurement.com",
    "firebaseio.com",
    "firebaseapp.com",
    "firebaseremoteconfig.googleapis.com",
    "firebaseinstallations.googleapis.com",
    "crashlytics.com",
    "doubleclick.net",
    "googleadservices.com",
    "googlesyndication.com",
    "admob.com",
    "gstatic.com",
    "googleapis.com",
    "facebook.com",
    "facebook.net",
    "fbcdn.net",
    "onesignal.com",
    "amplitude.com",
    "mixpanel.com",
    "segment.io",
    "segment.com",
    "branch.io",
    "appsflyer.com",
    "adjust.com",
    "kochava.com",
    "braze.com",
    "iterable.com",
    "sentry.io",
    "bugsnag.com",
    "instabug.com",
    "appcenter.ms",
    "flurry.com",
    "inmobi.com",
    "unity3d.com",
    "applovin.com",
    "ironsrc.com",
    "mopub.com",
    "mapbox.com",
    "auth0.com",
    "stripe.com",
    "paypal.com",
    "cloudfront.net",
    "akamaihd.net",
    "huawei.com",
    "hicloud.com",
    "huaweicloud.com",
    "yandex.ru",
    "yandex.net",
    "yandex.com",
]

REQUEST_TEXT_FIELDS = ("url", "method")


@dataclass
class PiiFinding:
    pii_type: str
    encoding: str
    value_preview: str
    method: str
    url: str
    host: str
    request_part: str
    message_index: int


@dataclass
class LocationFinding:
    indicator_type: str
    matched_value: str
    method: str
    url: str
    host: str
    request_part: str
    message_index: int


@dataclass
class DestinationRecord:
    host: str
    count: int
    category: str
    matched_hint: Optional[str]


class ZapClient:
    def __init__(self, base_url: str, api_key: Optional[str] = None, timeout: int = 30):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    def _params(self, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        merged: Dict[str, Any] = {}
        if params:
            merged.update(params)
        if self.api_key:
            merged["apikey"] = self.api_key
        return merged

    def get_json(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        response = requests.get(url, params=self._params(params), timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def get_text(self, path: str, params: Optional[Dict[str, Any]] = None) -> str:
        url = f"{self.base_url}{path}"
        response = requests.get(url, params=self._params(params), timeout=self.timeout)
        response.raise_for_status()
        return response.text

    def check_alive(self) -> None:
        data = self.get_json("/JSON/core/view/version/")
        version = data.get("version", "unknown")
        print(f"[zap] connected to ZAP version {version}")

    def new_session(self, name: Optional[str] = None) -> None:
        params: Dict[str, Any] = {"overwrite": "true"}
        if name:
            params["name"] = name
        self.get_json("/JSON/core/action/newSession/", params=params)
        print("[zap] created a new session")

    def clear_messages_best_effort(self) -> None:
        try:
            self.new_session()
        except Exception as exc:
            print(f"[zap] warning: failed to reset session: {exc}", file=sys.stderr)

    def export_har(self) -> Dict[str, Any]:
        text = self.get_text("/OTHER/core/other/messageHar/")
        return json.loads(text)

    def messages(self, start: int = 0, count: int = 100000) -> Dict[str, Any]:
        return self.get_json("/JSON/core/view/messages/", {"start": str(start), "count": str(count)})

    def root_ca_pem(self) -> str:
        return self.get_text("/OTHER/core/other/rootcert/")


class Adb:
    def __init__(self, serial: Optional[str] = None):
        self.serial = serial

    def cmd(self, args: Sequence[str], check: bool = True, capture: bool = True) -> subprocess.CompletedProcess[str]:
        base = ["adb"]
        if self.serial:
            base += ["-s", self.serial]
        full_cmd = base + list(args)
        return subprocess.run(
            full_cmd,
            text=True,
            stdout=subprocess.PIPE if capture else None,
            stderr=subprocess.PIPE if capture else None,
            check=check,
        )

    def shell(self, args: Sequence[str], check: bool = True, capture: bool = True) -> subprocess.CompletedProcess[str]:
        return self.cmd(["shell"] + list(args), check=check, capture=capture)

    def set_proxy(self, host: str, port: int) -> None:
        proxy = f"{host}:{port}"
        self.shell(["settings", "put", "global", "http_proxy", proxy])
        print(f"[adb] set global HTTP proxy to {proxy}")

    def clear_proxy(self) -> None:
        self.shell(["settings", "put", "global", "http_proxy", ":0"], check=False)
        self.shell(["settings", "delete", "global", "http_proxy"], check=False)
        self.shell(["settings", "delete", "global", "global_http_proxy_host"], check=False)
        self.shell(["settings", "delete", "global", "global_http_proxy_port"], check=False)
        print("[adb] cleared global HTTP proxy")

    def force_stop(self, package: str) -> None:
        self.shell(["am", "force-stop", package], check=False)

    def launch_package(self, package: str) -> None:
        self.cmd(["shell", "monkey", "-p", package, "-c", "android.intent.category.LAUNCHER", "1"], check=True)
        print(f"[adb] launched package {package}")

    def launch_activity(self, package: str, activity: str) -> None:
        component = activity if "/" in activity else f"{package}/{activity}"
        self.shell(["am", "start", "-n", component], check=True)
        print(f"[adb] launched activity {component}")

    def push(self, local: Path, remote: str) -> None:
        self.cmd(["push", str(local), remote], check=True)

    def start_cert_install_intent(self, remote_path: str) -> None:
        # Requires user confirmation on most devices.
        self.shell(
            [
                "am",
                "start",
                "-a",
                "android.credentials.INSTALL",
                "-t",
                "application/x-x509-ca-cert",
                "-d",
                f"file://{remote_path}",
            ],
            check=False,
        )


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def save_json(path: Path, data: Any) -> None:
    ensure_dir(path.parent)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=False)


def save_jsonl(path: Path, rows: Iterable[Dict[str, Any]]) -> None:
    ensure_dir(path.parent)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, sort_keys=False) + "\n")


def save_csv(path: Path, rows: List[Dict[str, Any]], fieldnames: Optional[List[str]] = None) -> None:
    ensure_dir(path.parent)
    if fieldnames is None:
        keys = []
        seen = set()
        for row in rows:
            for key in row.keys():
                if key not in seen:
                    seen.add(key)
                    keys.append(key)
        fieldnames = keys
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def load_dummy_pii(path: Optional[Path]) -> Dict[str, str]:
    if path is None:
        return dict(DEFAULT_DUMMY_PII)
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("dummy PII JSON must be an object mapping pii_type -> value")
    return {str(k): str(v) for k, v in data.items() if v is not None and str(v) != ""}


def pii_variants(value: str) -> Dict[str, str]:
    raw = value.encode("utf-8")
    normalized_no_spaces = re.sub(r"\s+", "", value)
    variants = {
        "plain": value,
        "lower": value.lower(),
        "upper": value.upper(),
        "urlencoded": urllib.parse.quote(value, safe=""),
        "urlencoded_plus": urllib.parse.quote_plus(value),
        "base64": base64.b64encode(raw).decode("ascii"),
        "base64_urlsafe": base64.urlsafe_b64encode(raw).decode("ascii"),
        "md5": hashlib.md5(raw).hexdigest(),
        "sha1": hashlib.sha1(raw).hexdigest(),
        "sha256": hashlib.sha256(raw).hexdigest(),
    }
    if normalized_no_spaces and normalized_no_spaces != value:
        variants["no_spaces"] = normalized_no_spaces
        variants["no_spaces_urlencoded"] = urllib.parse.quote(normalized_no_spaces, safe="")
    return {k: v for k, v in variants.items() if v}


def preview(value: str, keep: int = 8) -> str:
    if len(value) <= keep * 2 + 3:
        return value
    return f"{value[:keep]}...{value[-keep:]}"


def host_from_url(url: str) -> str:
    try:
        return urllib.parse.urlparse(url).hostname or ""
    except Exception:
        return ""


def request_parts_from_har_entry(entry: Dict[str, Any]) -> Dict[str, str]:
    request = entry.get("request", {}) or {}
    parts: Dict[str, str] = {}
    parts["url"] = request.get("url", "") or ""
    parts["method"] = request.get("method", "") or ""
    parts["headers"] = json.dumps(request.get("headers", []), ensure_ascii=False)
    parts["queryString"] = json.dumps(request.get("queryString", []), ensure_ascii=False)
    parts["cookies"] = json.dumps(request.get("cookies", []), ensure_ascii=False)
    post_data = request.get("postData", {}) or {}
    parts["postData"] = post_data.get("text", "") or json.dumps(post_data, ensure_ascii=False)
    return parts


def response_parts_from_har_entry(entry: Dict[str, Any]) -> Dict[str, str]:
    response = entry.get("response", {}) or {}
    content = response.get("content", {}) or {}
    return {
        "response_headers": json.dumps(response.get("headers", []), ensure_ascii=False),
        "response_content": content.get("text", "") or "",
    }


def iter_har_entries(har: Dict[str, Any]) -> Iterable[Tuple[int, Dict[str, Any]]]:
    entries = ((har.get("log") or {}).get("entries") or [])
    for idx, entry in enumerate(entries):
        yield idx, entry


def find_pii_in_har(
    har: Dict[str, Any],
    dummy_pii: Dict[str, str],
    include_responses: bool = False,
) -> List[PiiFinding]:
    pii_lookup: Dict[str, Dict[str, str]] = {
        pii_type: pii_variants(value) for pii_type, value in dummy_pii.items()
    }
    findings: List[PiiFinding] = []

    for idx, entry in iter_har_entries(har):
        request = entry.get("request", {}) or {}
        url = request.get("url", "") or ""
        method = request.get("method", "") or ""
        host = host_from_url(url)
        parts = request_parts_from_har_entry(entry)
        if include_responses:
            parts.update(response_parts_from_har_entry(entry))

        for part_name, blob in parts.items():
            if not blob:
                continue
            blob_lower = blob.lower()
            for pii_type, variants in pii_lookup.items():
                for encoding, encoded_value in variants.items():
                    if not encoded_value:
                        continue
                    haystack = blob_lower if encoding in {"lower"} else blob
                    needle = encoded_value.lower() if encoding == "lower" else encoded_value
                    if needle in haystack:
                        findings.append(
                            PiiFinding(
                                pii_type=pii_type,
                                encoding=encoding,
                                value_preview=preview(encoded_value),
                                method=method,
                                url=url,
                                host=host,
                                request_part=part_name,
                                message_index=idx,
                            )
                        )
    return dedupe_dataclass_list(findings)


def is_public_ipv4(candidate: str) -> bool:
    try:
        ip = ipaddress.ip_address(candidate)
        return bool(ip.version == 4 and ip.is_global)
    except ValueError:
        return False


def find_location_indicators_in_har(
    har: Dict[str, Any],
    include_responses: bool = False,
) -> List[LocationFinding]:
    findings: List[LocationFinding] = []

    for idx, entry in iter_har_entries(har):
        request = entry.get("request", {}) or {}
        url = request.get("url", "") or ""
        method = request.get("method", "") or ""
        host = host_from_url(url)
        parts = request_parts_from_har_entry(entry)
        if include_responses:
            parts.update(response_parts_from_har_entry(entry))

        for part_name, blob in parts.items():
            if not blob:
                continue

            for match in LAT_LON_PAIR_RE.finditer(blob):
                value = match.group(0)
                findings.append(
                    LocationFinding(
                        indicator_type="lat_lon_pair",
                        matched_value=preview(value, 16),
                        method=method,
                        url=url,
                        host=host,
                        request_part=part_name,
                        message_index=idx,
                    )
                )
            blob_lower = blob.lower()
            for term in LOCATION_TERMS:
                if re.search(rf"(?<![a-z0-9_]){re.escape(term)}(?![a-z0-9_])", blob_lower):
                    findings.append(
                        LocationFinding(
                            indicator_type="location_keyword",
                            matched_value=term,
                            method=method,
                            url=url,
                            host=host,
                            request_part=part_name,
                            message_index=idx,
                        )
                    )

            for ip_candidate in IPV4_RE.findall(blob):
                if is_public_ipv4(ip_candidate):
                    findings.append(
                        LocationFinding(
                            indicator_type="public_ip_value",
                            matched_value=ip_candidate,
                            method=method,
                            url=url,
                            host=host,
                            request_part=part_name,
                            message_index=idx,
                        )
                    )

    return dedupe_dataclass_list(findings)


def dedupe_dataclass_list(items: List[Any]) -> List[Any]:
    seen = set()
    unique = []
    for item in items:
        data = tuple(sorted(asdict(item).items()))
        if data not in seen:
            seen.add(data)
            unique.append(item)
    return unique


def read_domains_csv(value: Optional[str]) -> List[str]:
    if not value:
        return []
    path = Path(value)
    if path.exists():
        domains = []
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    domains.append(normalize_domain(line))
        return domains
    return [normalize_domain(x) for x in value.split(",") if x.strip()]


def normalize_domain(domain: str) -> str:
    domain = domain.strip().lower()
    domain = domain.removeprefix("http://").removeprefix("https://")
    domain = domain.split("/")[0]
    domain = domain.strip(".")
    return domain


def domain_matches(host: str, domain_or_hint: str) -> bool:
    host = normalize_domain(host)
    hint = normalize_domain(domain_or_hint)
    if not host or not hint:
        return False
    return host == hint or host.endswith("." + hint) or hint in host


def classify_destination(host: str, first_party_domains: Sequence[str]) -> Tuple[str, Optional[str]]:
    if not host:
        return "unknown", None
    for domain in first_party_domains:
        if domain_matches(host, domain):
            return "first_party", domain
    for hint in KNOWN_THIRD_PARTY_DOMAIN_HINTS:
        if domain_matches(host, hint):
            return "known_third_party_service", hint
    return "unknown_external", None


def summarize_destinations(har: Dict[str, Any], first_party_domains: Sequence[str]) -> List[DestinationRecord]:
    counts: Counter[str] = Counter()
    for _, entry in iter_har_entries(har):
        url = ((entry.get("request") or {}).get("url") or "")
        host = host_from_url(url)
        if host:
            counts[host] += 1
    records = []
    for host, count in counts.most_common():
        category, hint = classify_destination(host, first_party_domains)
        records.append(DestinationRecord(host=host, count=count, category=category, matched_hint=hint))
    return records


def run_external_crawler(
    crawler_script: Path,
    package: str,
    duration: int,
    out_dir: Path,
    activity: Optional[str] = None,
    fill_pii: bool = False,
    extra_args: Optional[List[str]] = None,
) -> int:
    cmd = [sys.executable, str(crawler_script), "--package", package, "--duration", str(duration), "--output", str(out_dir)]
    if activity:
        cmd += ["--activity", activity]
    if fill_pii:
        cmd.append("--fill-pii")
    if extra_args:
        cmd.extend(extra_args)
    print(f"[crawler] running: {' '.join(cmd)}")
    proc = subprocess.run(cmd)
    print(f"[crawler] exited with code {proc.returncode}")
    return int(proc.returncode)


def install_zap_cert_best_effort(zap: ZapClient, adb: Adb, out_dir: Path) -> None:
    cert_pem = zap.root_ca_pem()
    cert_path = out_dir / "zap_root_ca.cer"
    cert_path.write_text(cert_pem, encoding="utf-8")
    remote = "/sdcard/Download/zap_root_ca.cer"
    adb.push(cert_path, remote)
    adb.start_cert_install_intent(remote)


def wait_with_progress(seconds: int) -> None:
    start = time.time()
    next_print = 0
    while True:
        elapsed = int(time.time() - start)
        if elapsed >= seconds:
            break
        if elapsed >= next_print:
            remaining = seconds - elapsed
            print(f"[capture] {remaining}s remaining")
            next_print += 30
        time.sleep(1)


def count_har_entries(har: Dict[str, Any]) -> int:
    return len((har.get("log") or {}).get("entries") or [])


def dataclass_rows(items: Iterable[Any]) -> List[Dict[str, Any]]:
    return [asdict(item) for item in items]


def build_summary(
    har: Dict[str, Any],
    pii_findings: List[PiiFinding],
    location_findings: List[LocationFinding],
    destination_records: List[DestinationRecord],
    started_at: float,
    finished_at: float,
    args: argparse.Namespace,
) -> Dict[str, Any]:
    category_counts = Counter(record.category for record in destination_records)
    pii_counts = Counter(f.pii_type for f in pii_findings)
    pii_host_counts = Counter(f.host for f in pii_findings)
    loc_counts = Counter(f.indicator_type for f in location_findings)
    return {
        "package": args.package,
        "activity": args.activity,
        "started_at_epoch": started_at,
        "finished_at_epoch": finished_at,
        "duration_seconds": round(finished_at - started_at, 2),
        "har_entry_count": count_har_entries(har),
        "unique_destination_hosts": len(destination_records),
        "destination_category_counts": dict(category_counts),
        "pii_finding_count": len(pii_findings),
        "pii_type_counts": dict(pii_counts),
        "pii_destination_host_counts": dict(pii_host_counts),
        "location_indicator_count": len(location_findings),
        "location_indicator_type_counts": dict(loc_counts),
        "include_responses": bool(args.include_responses),
        "first_party_domains": read_domains_csv(args.first_party_domains),
        "zap_url": args.zap_url,
        "proxy_was_set": bool(args.set_proxy),
    }


def parse_extra_args(raw: Optional[str]) -> List[str]:
    if not raw:
        return []
    return raw.split()


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Capture and analyze Android app network traffic through OWASP ZAP.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--package", required=True)
    parser.add_argument("--activity")
    parser.add_argument("--duration", type=int, default=300)
    parser.add_argument("--out-dir", required=True, type=Path)

    parser.add_argument("--zap-url", default=os.getenv("ZAP_URL", "http://127.0.0.1:8080"))
    parser.add_argument("--zap-api-key", default=os.getenv("ZAP_API_KEY"))
    parser.add_argument("--new-session", action="store_true")

    parser.add_argument("--adb-serial")
    parser.add_argument("--set-proxy", action="store_true")
    parser.add_argument("--proxy-host", default="10.0.2.2")
    parser.add_argument("--proxy-port", type=int, default=8080)
    parser.add_argument("--clear-proxy-on-exit", action="store_true")
    parser.add_argument("--install-zap-cert", action="store_true")

    parser.add_argument("--no-launch", action="store_true")
    parser.add_argument("--force-stop-first", action="store_true")

    parser.add_argument("--crawler-script", type=Path)
    parser.add_argument("--crawler-fill-pii", action="store_true")
    parser.add_argument("--crawler-extra-args")

    parser.add_argument("--dummy-pii-json", type=Path)
    parser.add_argument("--include-responses", action="store_true")
    parser.add_argument("--first-party-domains")

    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    ensure_dir(args.out_dir)

    zap = ZapClient(args.zap_url, api_key=args.zap_api_key)
    adb = Adb(args.adb_serial)
    dummy_pii = load_dummy_pii(args.dummy_pii_json)

    started_at = time.time()
    save_json(args.out_dir / "dummy_pii_used.json", dummy_pii)

    try:
        zap.check_alive()
        if args.new_session:
            zap.new_session(name=f"{args.package}-{int(started_at)}")

        if args.install_zap_cert:
            install_zap_cert_best_effort(zap, adb, args.out_dir)
            try:
                input()
            except EOFError:
                pass

        if args.set_proxy:
            adb.set_proxy(args.proxy_host, args.proxy_port)

        if args.force_stop_first:
            adb.force_stop(args.package)

        if not args.no_launch and not args.crawler_script:
            if args.activity:
                adb.launch_activity(args.package, args.activity)
            else:
                adb.launch_package(args.package)

        if args.crawler_script:
            crawler_out = args.out_dir / "ui_crawler"
            run_external_crawler(
                crawler_script=args.crawler_script,
                package=args.package,
                duration=args.duration,
                out_dir=crawler_out,
                activity=args.activity,
                fill_pii=args.crawler_fill_pii,
                extra_args=parse_extra_args(args.crawler_extra_args),
            )
        else:
            wait_with_progress(args.duration)

        har = zap.export_har()
        messages = zap.messages()
        finished_at = time.time()

        save_json(args.out_dir / "network_flows.har", har)
        save_json(args.out_dir / "zap_messages.json", messages)

        pii_findings = find_pii_in_har(har, dummy_pii, include_responses=args.include_responses)
        location_findings = find_location_indicators_in_har(har, include_responses=args.include_responses)
        first_party_domains = read_domains_csv(args.first_party_domains)
        destination_records = summarize_destinations(har, first_party_domains)

        pii_rows = dataclass_rows(pii_findings)
        location_rows = dataclass_rows(location_findings)
        destination_rows = dataclass_rows(destination_records)

        save_json(args.out_dir / "transmitted_pii.json", pii_rows)
        save_csv(args.out_dir / "transmitted_pii.csv", pii_rows)
        save_json(args.out_dir / "location_indicators.json", location_rows)
        save_csv(args.out_dir / "location_indicators.csv", location_rows)
        save_json(args.out_dir / "destination_summary.json", destination_rows)
        save_csv(args.out_dir / "destination_summary.csv", destination_rows)

        summary = build_summary(
            har=har,
            pii_findings=pii_findings,
            location_findings=location_findings,
            destination_records=destination_records,
            started_at=started_at,
            finished_at=finished_at,
            args=args,
        )
        save_json(args.out_dir / "network_summary.json", summary)

        print("[done] wrote network analysis outputs to", args.out_dir)
        print(json.dumps(summary, indent=2))
        return 0

    except KeyboardInterrupt:
        print("\n[abort] interrupted", file=sys.stderr)
        return 130
    except Exception as exc:
        save_json(args.out_dir / "network_error.json", {"error": str(exc), "type": type(exc).__name__})
        print(f"[error] {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    finally:
        if args.clear_proxy_on_exit:
            try:
                adb.clear_proxy()
            except Exception as exc:
                print(f"[adb] warning: failed to clear proxy: {exc}", file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
