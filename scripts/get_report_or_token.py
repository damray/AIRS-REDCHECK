#!/usr/bin/env python3
"""Fetch an AIRS Red Team bearer token, list scan reports, and download one.

Usage:
    export TSG_ID=... CLIENT_ID=... CLIENT_SECRET=...
    python scripts/get_token.py [--debug]

    # Download the selected report as CSV instead of JSON:
    python scripts/get_token.py --csv

    # Print only the raw bearer token (capturable into a variable):
    python scripts/get_token.py --token-only

With 1Password:
    op run --env-file=.env.oauth -- python scripts/get_token.py
    TOKEN=$(op run --env-file=.env.oauth -- python scripts/get_token.py --token-only)
"""

import base64
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime

TOKEN_URL = "https://auth.apps.paloaltonetworks.com/oauth2/access_token"
API_BASE = "https://api.sase.paloaltonetworks.com/ai-red-teaming/data-plane"

DEBUG = "--debug" in sys.argv
TOKEN_ONLY = "--token-only" in sys.argv
FILE_FORMAT = "CSV" if "--csv" in sys.argv else "JSON"
REPORTS_DIR = "reports"


def _log(msg: str) -> None:
    print(msg, flush=True)


def _debug(msg: str) -> None:
    if DEBUG:
        print(f"  [debug] {msg}", flush=True)


def _decode_jwt_claims(token: str) -> dict:
    """Decode a JWT payload without verifying the signature (diagnostic only)."""
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)  # pad to multiple of 4
        return json.loads(base64.urlsafe_b64decode(payload))
    except (IndexError, ValueError, json.JSONDecodeError):
        return {}


# ── helpers ──────────────────────────────────────────────────────────────────

def _require_env(*names: str) -> dict[str, str]:
    vals = {n: os.environ.get(n, "") for n in names}
    missing = [n for n, v in vals.items() if not v]
    if missing:
        _log(f"Error: missing env vars: {', '.join(missing)}")
        sys.exit(1)
    return vals


def _api_get(path: str, token: str, params: dict | None = None) -> dict:
    url = f"{API_BASE}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)

    req = urllib.request.Request(url, method="GET")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/json")

    _debug(f"GET {url}")

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            _debug(f"Response {resp.status}")
            body = json.loads(resp.read())
            if DEBUG:
                preview = json.dumps(body, indent=2)[:500]
                _debug(f"Body preview: {preview}")
            return body
    except urllib.error.HTTPError as e:
        body = e.read().decode() if e.fp else ""
        _log(f"\nAPI error {e.code} on GET {path}: {body}")
        _debug(f"Response headers: {dict(e.headers)}")
        sys.exit(1)


def _api_get_bytes(path: str, token: str, params: dict | None = None) -> tuple[bytes, str]:
    """GET returning raw bytes (for file downloads that may be JSON or CSV).

    Follows redirects (urllib does this by default), matching `curl -L`, since the
    download endpoint may redirect to a signed storage URL.
    """
    url = f"{API_BASE}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)

    req = urllib.request.Request(url, method="GET")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/json")

    _debug(f"GET {url}")

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            _debug(f"Response {resp.status} content-type={resp.headers.get('content-type')}")
            return resp.read(), resp.headers.get("content-type", "")
    except urllib.error.HTTPError as e:
        body = e.read().decode() if e.fp else ""
        _log(f"\nAPI error {e.code} on GET {path}: {body}")
        _debug(f"Response headers: {dict(e.headers)}")
        sys.exit(1)


def _safe_name(text: str) -> str:
    """Turn a scan name into a filesystem-safe filename fragment."""
    keep = [c if c.isalnum() or c in "-_." else "_" for c in text.strip()]
    cleaned = "".join(keep).strip("_")
    return (cleaned or "scan")[:80]


# ── steps ────────────────────────────────────────────────────────────────────

def get_token() -> str:
    env = _require_env("TSG_ID", "CLIENT_ID", "CLIENT_SECRET")
    tsg_id = env["TSG_ID"]
    data = urllib.parse.urlencode({
        "grant_type": "client_credentials",
        "scope": f"tsg_id:{tsg_id}",
    }).encode()
    creds = base64.b64encode(
        f"{env['CLIENT_ID']}:{env['CLIENT_SECRET']}".encode()
    ).decode()

    req = urllib.request.Request(TOKEN_URL, data=data, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    req.add_header("Authorization", f"Basic {creds}")

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        err = e.read().decode() if e.fp else ""
        _log(f"Token error HTTP {e.code}: {err}")
        sys.exit(1)

    token = body.get("access_token", "")
    expires = body.get("expires_in", "?")
    if not token:
        _log("Error: no access_token in response")
        _log(json.dumps(body, indent=2))
        sys.exit(1)

    if not TOKEN_ONLY:
        _log(f"✓ Token acquired (expires in {expires}s)")
    if DEBUG:
        claims = _decode_jwt_claims(token)
        interesting = {
            k: claims.get(k)
            for k in ("scope", "scp", "roles", "access", "aud", "iss", "sub", "client_id", "tenant", "subdomain")
            if k in claims
        }
        _debug(f"Token claims: {json.dumps(interesting, indent=2)}")
        _debug(f"All claim keys: {sorted(claims.keys())}")
    return token


def list_scans(token: str) -> list[dict]:
    _log("\nFetching scan list …")
    scans: list[dict] = []
    skip = 0
    limit = 50
    while True:
        data = _api_get("/v1/scan", token, {"limit": limit, "skip": skip})
        items = data if isinstance(data, list) else data.get("items") or data.get("scans") or data.get("data") or []
        if not items:
            break
        scans.extend(items)
        if len(items) < limit:
            break
        skip += limit

    if not scans:
        _log("No scans found in this tenant.")
        sys.exit(0)

    return scans


def display_scans(scans: list[dict]) -> None:
    _log(f"\n{'#':<4} {'UUID':<38} {'Type':<9} {'Status':<11} {'Name  (created)'}")
    _log("─" * 110)
    for i, s in enumerate(scans, 1):
        uuid = s.get("uuid") or "?"
        job_type = s.get("job_type") or "?"
        status = s.get("status") or "?"
        name = s.get("name") or ""
        created = s.get("created_at") or ""
        if created:
            try:
                dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                created = dt.astimezone().strftime("%Y-%m-%d %H:%M")
            except (ValueError, TypeError):
                pass
            name = f"{name}  ({created})" if name else created
        _log(f"{i:<4} {str(uuid):<38} {str(job_type):<9} {str(status):<11} {name}")


def pick_scan(scans: list[dict]) -> dict:
    while True:
        try:
            choice = input(f"\nSelect a scan [1-{len(scans)}] (q to quit): ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            sys.exit(0)
        if choice.lower() == "q":
            sys.exit(0)
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(scans):
                return scans[idx]
        except ValueError:
            pass
        _log("Invalid selection, try again.")


def download_report(token: str, scan: dict) -> None:
    """Download the full attack-detail report via the unified download endpoint.

    GET /v1/report/{job_id}/download?file_format=JSON|CSV works for STATIC,
    DYNAMIC, and CUSTOM scans. The response is a ZIP archive containing
    report_summary.json plus the import-ready attack detail (attacks.json /
    .csv). We save the archive and extract its files into a per-scan folder.
    """
    job_id = scan.get("uuid")
    job_type = (scan.get("job_type") or "?").upper()
    name = scan.get("name") or job_id

    _log(f"\nDownloading {job_type} report '{name}' as {FILE_FORMAT} …")
    body, ctype = _api_get_bytes(
        f"/v1/report/{job_id}/download", token, {"file_format": FILE_FORMAT}
    )

    os.makedirs(REPORTS_DIR, exist_ok=True)
    stem = _safe_name(name)

    is_zip = "zip" in ctype.lower() or body[:4] == b"PK\x03\x04"
    if is_zip:
        zip_path = _unique_path(os.path.join(REPORTS_DIR, f"{stem}.zip"))
        with open(zip_path, "wb") as f:
            f.write(body)
        # Reuse the (possibly suffixed) zip stem so all files share one name.
        out_stem = os.path.splitext(os.path.basename(zip_path))[0]
        extracted = _extract_zip(zip_path, REPORTS_DIR, out_stem)
        for path, count in extracted:
            suffix = f" — {count} records" if count is not None else ""
            _log(f"✓ Saved {path}{suffix}")
        _log(f"  (raw archive kept at {zip_path})")
        return

    # Fallback: endpoint returned the file directly (not zipped).
    ext = "csv" if FILE_FORMAT == "CSV" else "json"
    path = _unique_path(os.path.join(REPORTS_DIR, f"{stem}.{ext}"))
    with open(path, "wb") as f:
        f.write(body)
    _log(f"✓ Saved {path} (content-type={ctype}, {os.path.getsize(path):,} bytes)")


def _member_filename(member: str, stem: str) -> str:
    """Map a ZIP member to a scan-name-based filename.

    attacks.json        -> <scan name>.json        (import-ready detail)
    report_summary.json -> <scan name>_summary.json
    anything else        -> <scan name>_<member>
    """
    base = os.path.basename(member)
    root, ext = os.path.splitext(base)
    if root == "attacks":
        return f"{stem}{ext}"
    if root == "report_summary":
        return f"{stem}_summary{ext}"
    return f"{stem}_{base}"


def _extract_zip(zip_path: str, dest_dir: str, stem: str) -> list[tuple[str, int | None]]:
    """Extract a report ZIP, renaming members after the scan name.

    Returns (output_path, record_count) for each extracted file.
    """
    import zipfile

    results: list[tuple[str, int | None]] = []
    with zipfile.ZipFile(zip_path) as zf:
        for member in zf.namelist():
            if member.endswith("/"):
                continue
            out_path = _unique_path(
                os.path.join(dest_dir, _member_filename(member, stem))
            )
            with zf.open(member) as src, open(out_path, "wb") as dst:
                dst.write(src.read())
            count = None
            if out_path.endswith(".json"):
                try:
                    with open(out_path) as f:
                        count = _count_records(json.load(f))
                except (json.JSONDecodeError, OSError):
                    pass
            results.append((out_path, count))
    return results


def _unique_path(path: str) -> str:
    """Return `path`, or `path` with a _2/_3/... suffix if it already exists."""
    if not os.path.exists(path):
        return path
    root, ext = os.path.splitext(path)
    i = 2
    while os.path.exists(f"{root}_{i}{ext}"):
        i += 1
    return f"{root}_{i}{ext}"


def _count_records(data) -> int | None:
    """Best-effort count of attack records in a downloaded JSON report."""
    if isinstance(data, list):
        return len(data)
    if isinstance(data, dict):
        for key in ("data", "attacks", "items", "results", "streams"):
            if isinstance(data.get(key), list):
                return len(data[key])
    return None


# ── main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    token = get_token()

    if TOKEN_ONLY:
        # Print only the raw bearer token on stdout so it can be captured,
        # e.g. TOKEN=$(op run ... -- python get_token.py --token-only)
        print(token)
        return

    scans = list_scans(token)
    display_scans(scans)
    scan = pick_scan(scans)
    download_report(token, scan)


if __name__ == "__main__":
    main()
