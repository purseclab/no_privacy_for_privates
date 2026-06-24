
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

try:
    from com.dtmilano.android.viewclient import ViewClient 
except Exception as exc:  
    print(
        "Could not import AndroidViewClient. Install it with:\n"
        "    pip3 install androidviewclient\n\n"
        f"Original import error: {exc}",
        file=sys.stderr,
    )
    raise


# ---------- PII configuration ----------

PII_KEYWORDS: Dict[str, Sequence[str]] = {
    "email": ("email", "e-mail", "mail address"),
    "name": ("name", "first name", "last name", "full name", "middle name", "preferred name"),
    "phone": ("phone", "mobile", "telephone", "cell", "contact number"),
    "address": ("address", "street", "city", "state", "zip", "zipcode", "postal", "postcode"),
    "dob": ("dob", "date of birth", "birth date", "birthday"),
    "gender": ("gender", "sex"),
    "age": ("age",),
    "military_base": ("base", "installation", "post", "fort", "camp", "barracks", "duty station"),
    "branch": (
        "branch", "army", "navy", "air force", "marine", "marines", "coast guard", "space force",
        "usaf", "usmc", "usn", "uscg",
    ),
    "rank": ("rank", "grade", "pay grade", "rate"),
    "unit": ("unit", "command", "squadron", "battalion", "brigade", "company", "platoon"),
    "dod_id": ("dod id", "edipi", "military id", "service number"),
}

DUMMY_PII: Dict[str, str] = {
   #put one for each PII
}

# Terms that usually lead outside the app, alter data, perform purchases, or log out.
DEFAULT_BLOCKLIST = {
    "delete", "remove", "logout", "log out", "sign out", "purchase", "buy", "subscribe", "payment",
    "pay", "order", "checkout", "share", "call", "dial", "sms", "message", "email us", "send email",
    "map", "directions", "rate us", "review", "facebook", "twitter", "instagram", "youtube",
    "privacy policy", "terms", "terms of service", "report", "submit", "send", "confirm", "save",
}

SAFE_POSITIVE_TERMS = {
    "next", "continue", "more", "menu", "settings", "profile", "account", "edit", "add", "search",
    "login", "log in", "sign in", "register", "create account", "get started", "start", "skip", "ok",
    "yes", "allow", "while using", "only this time",
}

INPUT_CLASS_TERMS = ("EditText", "TextInputEditText", "AutoCompleteTextView", "SearchView")
CLICKABLE_CLASS_TERMS = (
    "Button", "ImageButton", "TextView", "CheckedTextView", "RadioButton", "CheckBox", "Switch",
    "Spinner", "ImageView", "CardView", "LinearLayout", "RelativeLayout", "ConstraintLayout", "RecyclerView",
)


# ---------- Data classes ----------

@dataclass
class ViewRecord:
    unique_id: str
    view_id: Optional[str]
    klass: Optional[str]
    text: Optional[str]
    content_desc: Optional[str]
    tag: Optional[str]
    bounds: Optional[Any]
    center: Optional[Any]
    enabled: Optional[bool]
    clickable: Optional[bool]
    focusable: Optional[bool]
    scrollable: Optional[bool]
    raw_attrs: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PiiFinding:
    pii_types: List[str]
    source: str  # field | label | nearby_label | prefilled_value
    view: ViewRecord
    matched_text: str
    screen_signature: str
    timestamp: float
    dummy_value_used: Optional[str] = None


@dataclass
class ActionRecord:
    timestamp: float
    action: str
    view_unique_id: Optional[str]
    view_text: Optional[str]
    view_id: Optional[str]
    success: bool
    error: Optional[str] = None


def run(cmd: Sequence[str], timeout: int = 20, check: bool = True) -> str:
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=timeout)
    if check and proc.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(cmd)}\nstdout={proc.stdout}\nstderr={proc.stderr}")
    return proc.stdout.strip()


def adb(serial: Optional[str], *args: str, timeout: int = 20, check: bool = True) -> str:
    cmd = ["adb"]
    if serial:
        cmd += ["-s", serial]
    cmd += list(args)
    return run(cmd, timeout=timeout, check=check)


def shell_quote_for_adb_input(text: str) -> str:
    text = text.replace(" ", "%s")
    text = re.sub(r"[^A-Za-z0-9@._%+\-]", "", text)
    return text


def normalize(s: Optional[str]) -> str:
    if not s:
        return ""
    s = s.strip().lower()
    s = re.sub(r"\s+", " ", s)
    return s


def to_bool(value: Any) -> Optional[bool]:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    value_s = str(value).strip().lower()
    if value_s in {"true", "1", "yes"}:
        return True
    if value_s in {"false", "0", "no"}:
        return False
    return None


def get_attr(view: Any, *names: str) -> Any:
    mp = getattr(view, "map", {}) or {}
    for name in names:
        if name in mp:
            return mp[name]
    wanted = {n.lower().replace("-", "").replace(":", "") for n in names}
    for key, value in mp.items():
        key_norm = str(key).lower().replace("-", "").replace(":", "")
        if key_norm in wanted or any(key_norm.endswith(w) for w in wanted):
            return value
    return None


def safe_call(obj: Any, method: str, default: Any = None) -> Any:
    fn = getattr(obj, method, None)
    if not callable(fn):
        return default
    try:
        return fn()
    except Exception:
        return default


def view_to_record(view: Any) -> ViewRecord:
    raw_attrs = dict(getattr(view, "map", {}) or {})
    klass = safe_call(view, "getClass") or get_attr(view, "class", "className")
    text = safe_call(view, "getText") or get_attr(view, "text", "mText")
    content_desc = safe_call(view, "getContentDescription") or get_attr(view, "content-desc", "contentDescription")
    view_id = safe_call(view, "getId") or get_attr(view, "resource-id", "resourceId", "id", "mID")
    unique_id = safe_call(view, "getUniqueId") or view_id or hashlib.sha1(json.dumps(raw_attrs, sort_keys=True).encode()).hexdigest()
    bounds = safe_call(view, "getBounds") or safe_call(view, "getCoords") or get_attr(view, "bounds")
    center = safe_call(view, "getCenter")
    tag = safe_call(view, "getTag") or get_attr(view, "tag")
    return ViewRecord(
        unique_id=str(unique_id),
        view_id=str(view_id) if view_id is not None else None,
        klass=str(klass) if klass is not None else None,
        text=str(text) if text is not None else None,
        content_desc=str(content_desc) if content_desc is not None else None,
        tag=str(tag) if tag is not None else None,
        bounds=bounds,
        center=center,
        enabled=to_bool(get_attr(view, "enabled", "isEnabled", "mEnabled")),
        clickable=to_bool(get_attr(view, "clickable", "isClickable", "mClickable")),
        focusable=to_bool(get_attr(view, "focusable", "focused", "isFocusable", "mFocusable")),
        scrollable=to_bool(get_attr(view, "scrollable", "isScrollable")),
        raw_attrs=raw_attrs,
    )


def all_text_for_record(r: ViewRecord) -> str:
    return " ".join(x for x in [r.text, r.content_desc, r.view_id, r.tag, r.klass] if x)


def pii_matches(text: str) -> List[str]:
    text_l = normalize(text)
    hits: List[str] = []
    for pii_type, keywords in PII_KEYWORDS.items():
        for kw in keywords:
            kw_l = normalize(kw)
            if re.search(rf"(?<![a-z0-9]){re.escape(kw_l)}(?![a-z0-9])", text_l):
                hits.append(pii_type)
                break
    return sorted(set(hits))


def is_input_record(r: ViewRecord) -> bool:
    klass = r.klass or ""
    if any(term in klass for term in INPUT_CLASS_TERMS):
        return True
    raw = r.raw_attrs
    password = to_bool(get_attr_from_map(raw, "password"))
    if password:
        return True
    return False


def get_attr_from_map(mp: Dict[str, Any], *names: str) -> Any:
    for name in names:
        if name in mp:
            return mp[name]
    wanted = {n.lower().replace("-", "").replace(":", "") for n in names}
    for key, value in mp.items():
        key_norm = str(key).lower().replace("-", "").replace(":", "")
        if key_norm in wanted or any(key_norm.endswith(w) for w in wanted):
            return value
    return None


def is_clickable_candidate(r: ViewRecord) -> bool:
    if r.enabled is False:
        return False
    if r.clickable is True:
        return True
    klass = r.klass or ""
    text = all_text_for_record(r)
    if any(term in klass for term in CLICKABLE_CLASS_TERMS) and (r.text or r.content_desc or r.view_id):
        return True
    if any(term in normalize(text) for term in SAFE_POSITIVE_TERMS):
        return True
    return False


def should_skip_action(r: ViewRecord, allow_submit: bool) -> bool:
    text_l = normalize(all_text_for_record(r))
    if not text_l:
        return True
    if allow_submit:
        blocklist = DEFAULT_BLOCKLIST - {"submit", "send", "confirm", "save"}
    else:
        blocklist = DEFAULT_BLOCKLIST
    return any(term in text_l for term in blocklist)


def signature(records: Sequence[ViewRecord]) -> str:
    pieces = []
    for r in records:
        txt = re.sub(r"\d+", "#", normalize(r.text))[:60]
        pieces.append("|".join([normalize(r.klass), normalize(r.view_id), txt, normalize(r.content_desc)]))
    blob = "\n".join(sorted(set(pieces)))
    return hashlib.sha256(blob.encode("utf-8", errors="ignore")).hexdigest()[:16]


def iter_tree(root: Any) -> Iterable[Any]:
    stack = [root]
    seen: Set[int] = set()
    while stack:
        node = stack.pop()
        obj_id = id(node)
        if obj_id in seen:
            continue
        seen.add(obj_id)
        yield node
        children = safe_call(node, "getChildren", []) or []
        for child in reversed(children):
            stack.append(child)

class AndroidViewClientCrawler:
    def __init__(
        self,
        package: str,
        output_dir: Path,
        activity: Optional[str] = None,
        serial: Optional[str] = None,
        duration: int = 300,
        max_depth: int = 4,
        max_states: int = 80,
        sleep: float = 1.0,
        fill_pii: bool = False,
        allow_submit: bool = False,
        reset_app: bool = False,
    ) -> None:
        self.package = package
        self.activity = activity
        self.output_dir = output_dir
        self.serial = serial
        self.duration = duration
        self.max_depth = max_depth
        self.max_states = max_states
        self.sleep = sleep
        self.fill_pii = fill_pii
        self.allow_submit = allow_submit
        self.reset_app = reset_app

        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.snapshots_path = self.output_dir / "ui_snapshots.jsonl"
        self.actions_path = self.output_dir / "actions.jsonl"
        self.findings: List[PiiFinding] = []
        self.actions: List[ActionRecord] = []
        self.seen_signatures: Set[str] = set()

        self.device = None
        self.vc = None
        self.serialno = None
        self.started_at = 0.0

    def connect(self) -> None:
        self.device, self.serialno = ViewClient.connectToDeviceOrExit(serialno=self.serial)
        self.vc = ViewClient(self.device, self.serialno, autodump=False)

    def launch(self) -> None:
        if self.reset_app:
            adb(self.serialno, "shell", "pm", "clear", self.package, timeout=30, check=False)
        component = self.activity or self.package
        if "/" in component:
            adb(self.serialno, "shell", "am", "start", "-n", component, timeout=20)
        else:
            adb(self.serialno, "shell", "monkey", "-p", self.package, "-c", "android.intent.category.LAUNCHER", "1", timeout=20)
        time.sleep(self.sleep)

    def dump_records(self) -> Tuple[str, List[ViewRecord], List[Any]]:
        assert self.vc is not None
        self.vc.dump(sleep=self.sleep)
        root = self.vc.getRoot()

        raw_views = list(iter_tree(root))
        try:
            raw_views.extend(list((self.vc.getViewsById() or {}).values()))
        except Exception:
            pass

        dedup: Dict[str, Any] = {}
        for v in raw_views:
            r = view_to_record(v)
            dedup[r.unique_id] = v
        records = [view_to_record(v) for v in dedup.values()]
        sig = signature(records)
        return sig, records, list(dedup.values())

    def write_snapshot(self, sig: str, records: Sequence[ViewRecord], depth: int) -> None:
        payload = {
            "timestamp": time.time(),
            "package": self.package,
            "depth": depth,
            "screen_signature": sig,
            "views": [asdict(r) for r in records],
        }
        with self.snapshots_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")

    def log_action(self, action: ActionRecord) -> None:
        self.actions.append(action)
        with self.actions_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(action), ensure_ascii=False) + "\n")

    def detect_pii_fields(self, sig: str, records: Sequence[ViewRecord]) -> List[PiiFinding]:
        findings: List[PiiFinding] = []
        last_label_text = ""
        last_label_hits: List[str] = []

        for r in records:
            metadata = all_text_for_record(r)
            hits = pii_matches(metadata)
            if hits:
                source = "field" if is_input_record(r) else "label"
                findings.append(PiiFinding(
                    pii_types=hits,
                    source=source,
                    view=r,
                    matched_text=metadata,
                    screen_signature=sig,
                    timestamp=time.time(),
                ))

            if is_input_record(r) and not hits and last_label_hits:
                findings.append(PiiFinding(
                    pii_types=last_label_hits,
                    source="nearby_label",
                    view=r,
                    matched_text=last_label_text,
                    screen_signature=sig,
                    timestamp=time.time(),
                ))

            if not is_input_record(r) and (r.text or r.content_desc):
                last_label_text = metadata
                last_label_hits = hits

            value_text = " ".join(x for x in [r.text, r.content_desc] if x)
            prefilled = []
            if re.search(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}", value_text):
                prefilled.append("email")
            if re.search(r"(?:\+?1[\s\-.]?)?(?:\(?\d{3}\)?[\s\-.]?)\d{3}[\s\-.]?\d{4}", value_text):
                prefilled.append("phone")
            if prefilled:
                findings.append(PiiFinding(
                    pii_types=sorted(set(prefilled)),
                    source="prefilled_value",
                    view=r,
                    matched_text=value_text,
                    screen_signature=sig,
                    timestamp=time.time(),
                ))

        return findings

    def fill_detected_inputs(self, raw_views: Sequence[Any], findings: Sequence[PiiFinding]) -> None:
        if not self.fill_pii:
            return
        by_uid = {view_to_record(v).unique_id: v for v in raw_views}
        filled_uids: Set[str] = set()
        for finding in findings:
            r = finding.view
            if r.unique_id in filled_uids or not is_input_record(r):
                continue
            pii_type = next((t for t in finding.pii_types if t in DUMMY_PII), None)
            if not pii_type:
                continue
            dummy_value = DUMMY_PII[pii_type]
            view = by_uid.get(r.unique_id)
            if view is None:
                continue
            try:
                set_text = getattr(view, "setText", None)
                if callable(set_text):
                    set_text(dummy_value)
                else:
                    view.touch()
                    time.sleep(0.3)
                    adb(self.serialno, "shell", "input", "keyevent", "KEYCODE_CTRL_A", check=False)
                    adb(self.serialno, "shell", "input", "text", shell_quote_for_adb_input(dummy_value), check=False)
                finding.dummy_value_used = dummy_value
                filled_uids.add(r.unique_id)
                time.sleep(0.2)
            except Exception as exc:
                self.log_action(ActionRecord(
                    timestamp=time.time(),
                    action="fill_text_failed",
                    view_unique_id=r.unique_id,
                    view_text=r.text,
                    view_id=r.view_id,
                    success=False,
                    error=str(exc),
                ))

    def candidates(self, records: Sequence[ViewRecord]) -> List[ViewRecord]:
        items = []
        seen: Set[str] = set()
        for r in records:
            if r.unique_id in seen:
                continue
            seen.add(r.unique_id)
            if is_input_record(r):
                continue
            if not is_clickable_candidate(r):
                continue
            if should_skip_action(r, allow_submit=self.allow_submit):
                continue
            items.append(r)
        items.sort(key=lambda r: (
            0 if (r.text or r.content_desc) else 1,
            0 if r.clickable else 1,
            len(all_text_for_record(r)),
        ))
        return items[:12]

    def touch_view_by_uid(self, raw_views: Sequence[Any], uid: str) -> bool:
        for v in raw_views:
            if view_to_record(v).unique_id == uid:
                v.touch()
                return True
        return False

    def press_back(self) -> None:
        try:
            adb(self.serialno, "shell", "input", "keyevent", "KEYCODE_BACK", timeout=10, check=False)
        except Exception:
            pass
        time.sleep(self.sleep)

    def scroll_once(self) -> None:
        width, height = 1080, 1920
        try:
            display = getattr(self.vc, "display", {}) or {}
            width = int(display.get("width", width))
            height = int(display.get("height", height))
        except Exception:
            pass
        x = width // 2
        adb(self.serialno, "shell", "input", "swipe", str(x), str(int(height * 0.78)), str(x), str(int(height * 0.28)), "400", check=False)
        time.sleep(self.sleep)

    def explore(self, depth: int = 0) -> None:
        if time.time() - self.started_at > self.duration:
            return
        if len(self.seen_signatures) >= self.max_states:
            return
        if depth > self.max_depth:
            return

        sig, records, raw_views = self.dump_records()
        self.write_snapshot(sig, records, depth)

        new_screen = sig not in self.seen_signatures
        self.seen_signatures.add(sig)

        findings = self.detect_pii_fields(sig, records)
        self.findings.extend(findings)
        self.fill_detected_inputs(raw_views, findings)

        if not new_screen and depth > 0:
            return


        for candidate in self.candidates(records):
            if time.time() - self.started_at > self.duration or len(self.seen_signatures) >= self.max_states:
                return
            ok = False
            err = None
            try:
                ok = self.touch_view_by_uid(raw_views, candidate.unique_id)
                time.sleep(self.sleep)
            except Exception as exc:
                err = str(exc)
            self.log_action(ActionRecord(
                timestamp=time.time(),
                action="touch",
                view_unique_id=candidate.unique_id,
                view_text=candidate.text or candidate.content_desc,
                view_id=candidate.view_id,
                success=ok,
                error=err,
            ))
            if ok:
                self.explore(depth + 1)
                self.press_back()
                try:
                    sig, records, raw_views = self.dump_records()
                except Exception:
                    self.launch()
                    sig, records, raw_views = self.dump_records()

        if depth <= 1:
            self.scroll_once()
            sig2, records2, raw_views2 = self.dump_records()
            self.write_snapshot(sig2, records2, depth)
            if sig2 not in self.seen_signatures:
                self.seen_signatures.add(sig2)
                findings2 = self.detect_pii_fields(sig2, records2)
                self.findings.extend(findings2)
                self.fill_detected_inputs(raw_views2, findings2)

    def finalize(self) -> None:
        unique: Dict[Tuple[str, str, Tuple[str, ...], str], PiiFinding] = {}
        for f in self.findings:
            key = (f.screen_signature, f.view.unique_id, tuple(f.pii_types), f.source)
            unique[key] = f
        report = [asdict(f) for f in unique.values()]
        (self.output_dir / "pii_fields.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        summary = {
            "package": self.package,
            "screens_seen": len(self.seen_signatures),
            "pii_findings": len(report),
            "actions": len(self.actions),
            "duration_seconds": round(time.time() - self.started_at, 2),
            "output_dir": str(self.output_dir),
        }
        (self.output_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print(json.dumps(summary, indent=2))

    def run(self) -> None:
        self.started_at = time.time()
        self.connect()
        self.launch()
        try:
            self.explore(depth=0)
        finally:
            self.finalize()

def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="AndroidViewClient UI crawler for PII field discovery")
    p.add_argument("--package", required=True)
    p.add_argument("--activity")
    p.add_argument("--serial")
    p.add_argument("--output", required=True, type=Path)
    p.add_argument("--duration", type=int, default=300)
    p.add_argument("--max-depth", type=int, default=4)
    p.add_argument("--max-states", type=int, default=80)
    p.add_argument("--sleep", type=float, default=1.0)
    p.add_argument("--fill-pii", action="store_true")
    p.add_argument("--allow-submit", action="store_true")
    p.add_argument("--reset-app", action="store_true")
    return p.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    crawler = AndroidViewClientCrawler(
        package=args.package,
        activity=args.activity,
        serial=args.serial,
        output_dir=args.output,
        duration=args.duration,
        max_depth=args.max_depth,
        max_states=args.max_states,
        sleep=args.sleep,
        fill_pii=args.fill_pii,
        allow_submit=args.allow_submit,
        reset_app=args.reset_app,
    )
    crawler.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
