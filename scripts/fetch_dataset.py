#!/usr/bin/env python3
"""Download a dataset into a project and record exactly what was retrieved.

The manifest this script writes (<project>/data/manifest.json) is the only
acceptable evidence that data was collected. If a download is not in the
manifest, it did not happen - report it as "not collected" and give the student
the manual steps instead.

Usage:
    python fetch_dataset.py kaggle:blastchar/telco-customer-churn \
        --project ./churn-project --id ibm-telco-churn \
        --name "Telco Customer Churn" --publisher "IBM sample data (Kaggle mirror)" \
        --landing-page https://www.kaggle.com/datasets/blastchar/telco-customer-churn \
        --license "Data files (c) Original Authors" \
        --provenance simulated --provenance-note "IBM says: fictional telco company"

    python fetch_dataset.py https://example.org/data/file.csv --project ./p --id my-data

What to pass as the source (one or more):
    https://...            any direct file or API URL
    kaggle:owner/slug      public Kaggle dataset (no login needed; competitions do need one)
    zenodo:<record id>     every file in an open Zenodo record
    hf:owner/name          tabular/archive files in a public Hugging Face dataset repo

Safety behaviour:
  * refuses files over --max-mb (default 300) unless you raise the limit
  * rejects HTML pages that come back instead of data (login walls, landing pages)
  * extracts zip/tar archives (nested ones too) without letting paths escape
  * never executes anything it downloads

Standard library only.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import sys
import tarfile
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

USER_AGENT = "Mozilla/5.0 (compatible; dataset-research/1.0)"
TIMEOUT = 120
CHUNK = 1024 * 256
PROVENANCE_CHOICES = ["actual", "anonymized", "simulated", "synthetic", "unverified"]
HF_DATA_EXT = (".csv", ".tsv", ".json", ".jsonl", ".parquet", ".xlsx", ".xls", ".zip", ".gz", ".txt")
ARCHIVE_DEPTH = 3


class FetchError(Exception):
    pass


def now_utc() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def safe_name(name: str) -> str:
    name = urllib.parse.unquote(name or "").strip().replace("\\", "/").rsplit("/", 1)[-1]
    name = re.sub(r'[<>:"|?*\x00-\x1f]', "_", name).strip(" .")
    return name[:150] or "download.bin"


def get_json(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return json.loads(resp.read().decode("utf-8", "replace"))


def expand_source(src: str) -> list[tuple[str, str | None]]:
    """Turn a shorthand reference into a list of (url, suggested_filename)."""
    if src.startswith("kaggle:"):
        ref = src.split(":", 1)[1].strip().strip("/")
        if ref.count("/") != 1:
            raise FetchError(f"Kaggle reference must look like kaggle:owner/slug, got {src!r}")
        return [(f"https://www.kaggle.com/api/v1/datasets/download/{ref}", ref.split("/")[1] + ".zip")]
    if src.startswith("zenodo:"):
        rec = src.split(":", 1)[1].strip()
        data = get_json(f"https://zenodo.org/api/records/{rec}")
        files = data.get("files") or []
        if not files:
            raise FetchError(f"Zenodo record {rec} lists no open files (restricted or metadata-only).")
        out = []
        for f in files:
            link = (f.get("links") or {}).get("self") or f"https://zenodo.org/api/records/{rec}/files/{f.get('key')}/content"
            out.append((link, f.get("key")))
        return out
    if src.startswith("hf:"):
        ds = src.split(":", 1)[1].strip().strip("/")
        info = get_json(f"https://huggingface.co/api/datasets/{ds}")
        if info.get("gated"):
            raise FetchError(f"Hugging Face dataset {ds} is gated: the student must log in and accept its terms.")
        paths = [s.get("rfilename") for s in (info.get("siblings") or []) if s.get("rfilename")]
        data_paths = [p for p in paths if p.lower().endswith(HF_DATA_EXT) and not p.lower().endswith("readme.txt")]
        if not data_paths:
            raise FetchError(f"No tabular or archive files found in Hugging Face dataset {ds}. Files: {paths[:15]}")
        return [(f"https://huggingface.co/datasets/{ds}/resolve/main/{urllib.parse.quote(p)}", p.replace("/", "__"))
                for p in data_paths]
    if re.match(r"^https?://", src):
        return [(src, None)]
    raise FetchError(f"Don't know how to fetch {src!r}. Use a URL, kaggle:owner/slug, zenodo:<id> or hf:owner/name.")


def looks_like_html(head: bytes) -> bool:
    sniff = head[:600].lstrip().lower()
    return sniff.startswith(b"<!doctype html") or sniff.startswith(b"<html") or b"<head" in sniff[:300]


def download(url: str, dest_dir: Path, suggested: str | None, max_bytes: int, allow_html: bool) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
    try:
        resp = urllib.request.urlopen(req, timeout=TIMEOUT)
    except urllib.error.HTTPError as exc:
        hint = ""
        if exc.code in (401, 403):
            hint = " - the source wants a login or permission; give the student manual download steps instead"
        elif exc.code == 404:
            hint = " - the link is dead or wrong; do not cite it as a working download link"
        elif exc.code == 429:
            hint = " - rate limited; wait a bit and retry once"
        raise FetchError(f"HTTP {exc.code} {exc.reason}{hint}") from None
    except Exception as exc:
        raise FetchError(f"{type(exc).__name__}: {exc}") from None

    with resp:
        ctype = resp.headers.get("Content-Type") or ""
        length = resp.headers.get("Content-Length")
        if length and length.isdigit() and int(length) > max_bytes:
            raise FetchError(
                f"file is {int(length) / 1e6:.0f} MB, over the {max_bytes / 1e6:.0f} MB limit. "
                "Raise --max-mb if the user agrees, or point the student at the link."
            )
        name = suggested
        cd = resp.headers.get("Content-Disposition") or ""
        m = re.search(r"filename\*=(?:UTF-8'')?([^;]+)", cd, re.I) or re.search(r'filename="?([^";]+)"?', cd, re.I)
        if m and not name:
            name = m.group(1)
        if not name:
            name = urllib.parse.urlparse(resp.geturl()).path.rsplit("/", 1)[-1] or urllib.parse.urlparse(url).path.rsplit("/", 1)[-1]
        name = safe_name(name)
        if "." not in name:
            low = ctype.lower()
            ext = (".csv" if "csv" in low else ".json" if "json" in low else ".zip" if "zip" in low
                   else ".xlsx" if "spreadsheetml" in low else ".parquet" if "parquet" in low else "")
            name += ext

        dest_dir.mkdir(parents=True, exist_ok=True)
        target = dest_dir / name
        tmp = dest_dir / (name + ".part")
        sha = hashlib.sha256()
        total = 0
        head = b""
        try:
            with open(tmp, "wb") as fh:
                while True:
                    chunk = resp.read(CHUNK)
                    if not chunk:
                        break
                    if not head:
                        head = chunk[:1024]
                    total += len(chunk)
                    if total > max_bytes:
                        raise FetchError(f"download passed the {max_bytes / 1e6:.0f} MB limit and was stopped.")
                    sha.update(chunk)
                    fh.write(chunk)
        except Exception:
            tmp.unlink(missing_ok=True)
            raise

        if total == 0:
            tmp.unlink(missing_ok=True)
            raise FetchError("the server returned an empty file.")
        html = looks_like_html(head) or "text/html" in ctype.lower()
        if html and not allow_html and not name.lower().endswith((".html", ".htm")):
            tmp.unlink(missing_ok=True)
            raise FetchError(
                "got a web page instead of a data file (a landing page, login wall or cookie notice). "
                "This is not a download link: find the real file URL, or give the student manual steps."
            )
        os.replace(tmp, target)
        return {
            "requested_url": url,
            "final_url": resp.geturl().split("?")[0] if "X-Goog-" in resp.geturl() else resp.geturl(),
            "http_status": resp.status,
            "content_type": ctype,
            "saved_as": name,
            "bytes": total,
            "sha256": sha.hexdigest(),
            "retrieved_at_utc": now_utc(),
        }


def _inside(base: Path, target: Path) -> bool:
    try:
        target.resolve().relative_to(base.resolve())
        return True
    except ValueError:
        return False


def _archive_kind(path: Path) -> str | None:
    low = path.name.lower()
    if low.endswith(".zip") and zipfile.is_zipfile(path):
        return "zip"
    if low.endswith((".tar.gz", ".tgz", ".tar")) and tarfile.is_tarfile(path):
        return "tar"
    return None


def _is_junk(member: str) -> bool:
    """Finder/Explorer leftovers that archives carry around; never data."""
    base = member.replace("\\", "/").rsplit("/", 1)[-1]
    return "__MACOSX/" in member or base in (".DS_Store", "Thumbs.db", "desktop.ini") or base.startswith("._")


def extract_archives(folder: Path, budget_bytes: int) -> list[str]:
    """Extract zip/tar archives under folder, including archives inside archives.

    Paths that would escape the dataset folder are skipped, and anything whose
    uncompressed size exceeds budget_bytes is left alone (zip-bomb guard).
    """
    notes: list[str] = []
    done: set[Path] = set()
    for _ in range(ARCHIVE_DEPTH):
        pending = [p for p in sorted(folder.rglob("*")) if p.is_file() and p not in done and _archive_kind(p)]
        if not pending:
            break
        for arc in pending:
            done.add(arc)
            label = arc.relative_to(folder).as_posix()
            sub_dir = arc.parent / re.sub(r"\.(zip|tar\.gz|tgz|tar)$", "", arc.name, flags=re.I)
            try:
                if _archive_kind(arc) == "zip":
                    with zipfile.ZipFile(arc) as zf:
                        infos = [i for i in zf.infolist() if not i.is_dir() and not _is_junk(i.filename)]
                        size = sum(i.file_size for i in infos)
                        if size > budget_bytes:
                            notes.append(f"{label}: NOT extracted, {size / 1e6:.0f} MB uncompressed is over the limit.")
                            continue
                        # one loose file -> put it beside the archive; otherwise use a sub-folder
                        single = len(infos) == 1 and "/" not in infos[0].filename.strip("/")
                        target_dir = arc.parent if single else sub_dir
                        target_dir.mkdir(parents=True, exist_ok=True)
                        count = 0
                        for info in infos:
                            if not _inside(target_dir, target_dir / info.filename):
                                notes.append(f"{label}: skipped unsafe path {info.filename!r}")
                                continue
                            zf.extract(info, target_dir)
                            count += 1
                        notes.append(f"{label}: extracted {count} file(s)")
                else:
                    with tarfile.open(arc) as tf:
                        members = [m for m in tf.getmembers() if m.isfile()]
                        size = sum(m.size for m in members)
                        if size > budget_bytes:
                            notes.append(f"{label}: NOT extracted, {size / 1e6:.0f} MB uncompressed is over the limit.")
                            continue
                        sub_dir.mkdir(parents=True, exist_ok=True)
                        try:
                            tf.extractall(sub_dir, filter="data")
                        except TypeError:  # Python too old for the filter argument
                            for m in members:
                                if _inside(sub_dir, sub_dir / m.name):
                                    tf.extract(m, sub_dir)
                        notes.append(f"{label}: extracted {len(members)} file(s)")
            except Exception as exc:
                notes.append(f"{label}: could not extract ({type(exc).__name__}: {exc})")
    return notes


def list_files(folder: Path) -> list[dict]:
    files = []
    for p in sorted(folder.rglob("*")):
        if p.is_file() and not p.name.endswith(".part"):
            files.append({"path": p.relative_to(folder).as_posix(), "bytes": p.stat().st_size})
    return files


def load_manifest(path: Path) -> dict:
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            shutil.copy2(path, path.with_suffix(".json.corrupt"))
    return {
        "about": "Written by fetch_dataset.py. Each entry is a download that really happened. Do not edit counts or hashes by hand.",
        "datasets": {},
        "failed_attempts": [],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Download dataset files into <project>/data/raw/<id>/ and log them.")
    ap.add_argument("sources", nargs="+", help="URL(s) or kaggle:owner/slug, zenodo:<id>, hf:owner/name")
    ap.add_argument("--project", required=True, help="Project folder (data/ is created inside it).")
    ap.add_argument("--id", required=True, help="Short folder-safe id for this dataset, e.g. olist-ecommerce")
    ap.add_argument("--name", help="Dataset title as the publisher writes it.")
    ap.add_argument("--publisher", help="Organisation or person that published it.")
    ap.add_argument("--landing-page", help="Human-readable source page that was opened and checked.")
    ap.add_argument("--license", help="Licence or terms as stated on the source page.")
    ap.add_argument("--provenance", choices=PROVENANCE_CHOICES, default="unverified",
                    help="actual | anonymized | simulated | synthetic | unverified (default until proven).")
    ap.add_argument("--provenance-note", help="The evidence for that class, ideally a quote from the source page.")
    ap.add_argument("--max-mb", type=float, default=300, help="Refuse larger downloads (default 300).")
    ap.add_argument("--no-extract", action="store_true", help="Keep archives as they are.")
    ap.add_argument("--allow-html", action="store_true", help="Keep HTML responses (only when a web page IS the data).")
    args = ap.parse_args()

    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    ds_id = re.sub(r"[^a-z0-9._-]+", "-", args.id.lower()).strip("-")
    if not ds_id:
        print("--id must contain letters or digits.", file=sys.stderr)
        return 2
    project = Path(args.project)
    data_dir = project / "data"
    dest = data_dir / "raw" / ds_id
    manifest_path = data_dir / "manifest.json"
    manifest = load_manifest(manifest_path)
    max_bytes = int(args.max_mb * 1024 * 1024)

    downloads, failures = [], []
    for src in args.sources:
        try:
            targets = expand_source(src)
        except Exception as exc:
            failures.append({"source": src, "error": str(exc), "attempted_at_utc": now_utc(), "dataset_id": ds_id})
            print(f"FAILED  {src}\n        {exc}")
            continue
        for url, suggested in targets:
            try:
                rec = download(url, dest, suggested, max_bytes, args.allow_html)
                rec["source_ref"] = src
                downloads.append(rec)
                print(f"OK      {rec['saved_as']}  {rec['bytes']:,} bytes  sha256={rec['sha256'][:16]}…")
            except Exception as exc:
                failures.append({"source": src, "url": url, "error": str(exc),
                                 "attempted_at_utc": now_utc(), "dataset_id": ds_id})
                print(f"FAILED  {url}\n        {exc}")

    notes: list[str] = []
    if downloads and not args.no_extract:
        notes = extract_archives(dest, budget_bytes=max(max_bytes * 10, 2 * 1024**3))
        for n in notes:
            print(f"        {n}")

    data_dir.mkdir(parents=True, exist_ok=True)
    if not downloads and dest.is_dir() and not any(dest.iterdir()):
        dest.rmdir()  # nothing arrived: leave no empty folder that could be mistaken for collected data
    if downloads:
        entry = manifest["datasets"].get(ds_id, {"downloads": []})
        for key, val in (("name", args.name), ("publisher", args.publisher), ("landing_page", args.landing_page),
                         ("license", args.license), ("provenance_note", args.provenance_note)):
            if val:
                entry[key] = val
        if args.provenance != "unverified" or "provenance" not in entry:
            entry["provenance"] = args.provenance
        entry["folder"] = f"data/raw/{ds_id}"
        seen = {d["sha256"] for d in downloads}
        entry["downloads"] = [d for d in entry.get("downloads", []) if d.get("sha256") not in seen] + downloads
        entry["archive_notes"] = notes
        entry["files"] = list_files(dest)
        entry["last_fetched_utc"] = now_utc()
        manifest["datasets"][ds_id] = entry
    manifest.setdefault("failed_attempts", []).extend(failures)
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    print()
    if downloads:
        files = manifest["datasets"][ds_id]["files"]
        print(f"Collected {len(downloads)} download(s) into {dest}")
        for f in files[:40]:
            print(f"  {f['path']}  ({f['bytes']:,} bytes)")
        if len(files) > 40:
            print(f"  … and {len(files) - 40} more")
        if manifest["datasets"][ds_id].get("provenance") == "unverified":
            print("Provenance is still 'unverified'. Read the source page and re-run with --provenance once you know.")
    if failures:
        print(f"{len(failures)} attempt(s) failed and were logged under failed_attempts. "
              "Report these as NOT collected and give manual steps.")
    print(f"Manifest: {manifest_path}")
    return 0 if downloads and not failures else (1 if not downloads else 3)


if __name__ == "__main__":
    sys.exit(main())
