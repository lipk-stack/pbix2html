#!/usr/bin/env python3
"""Download a corpus of publicly published PBIX files for testing pbix2html.

Replaces the five near-identical inline workflow scripts that previously
lived under .github/workflows/. Discovery is tiered:

  1. microsoft/powerbi-desktop-samples (official Microsoft samples), then
  2. optionally (--allow-search) other public GitHub repositories found via
     the repository search API.

Files are deduplicated by git blob SHA and by content SHA-256, verified
against the expected blob size, and written alongside manifest.json,
manifest.csv, corpus-summary.json, and events.json.

Authentication: set GH_TOKEN (or GITHUB_TOKEN) to raise API rate limits;
unauthenticated runs are limited to 60 core / 10 search requests per hour
and will usually fail for larger targets.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import pathlib
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

API_VERSION = "2022-11-28"
USER_AGENT = "pbix2html-corpus-builder/3.0"
SEARCH_QUERIES = [
    "pbix powerbi in:name,description,readme",
    '"power bi" dashboard pbix in:name,description,readme',
    "powerbi-dashboard in:name,description,readme",
]
OFFICIAL_REPO = ("microsoft", "powerbi-desktop-samples", None)  # None = default branch
MAX_TREE_REQUESTS = 55
DOWNLOAD_ATTEMPTS = 3


def api_headers(token: str) -> dict:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": USER_AGENT,
        "X-GitHub-Api-Version": API_VERSION,
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def get_json(url: str, token: str, timeout: int = 90):
    request = urllib.request.Request(url, headers=api_headers(token))
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.load(response)


def safe_name(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("._")
    return cleaned[:140] or "sample.pbix"


def raw_url(owner: str, repo: str, ref: str, path: str) -> str:
    return (
        f"https://raw.githubusercontent.com/{owner}/{repo}/"
        f"{urllib.parse.quote(ref, safe='')}/{urllib.parse.quote(path, safe='/')}"
    )


class CorpusBuilder:
    def __init__(self, args: argparse.Namespace, token: str):
        self.args = args
        self.token = token
        self.out = pathlib.Path(args.out)
        self.out.mkdir(parents=True, exist_ok=True)
        self.manifest: list[dict] = []
        self.events: list[dict] = []
        self.seen_blob: set = set()
        self.seen_sha256: set = set()
        self.candidate_count = 0

    def log_event(self, **fields) -> None:
        self.events.append(fields)

    def done(self) -> bool:
        return len(self.manifest) >= self.args.target

    def tree_candidates(self, owner: str, repo: str, ref: str, source_class: str) -> list[dict]:
        tree_url = (
            f"https://api.github.com/repos/{owner}/{repo}/git/trees/"
            f"{urllib.parse.quote(ref, safe='')}?recursive=1"
        )
        tree = get_json(tree_url, self.token)
        if tree.get("truncated"):
            self.log_event(stage="tree", repository=f"{owner}/{repo}", error="recursive tree truncated")
        found = []
        for node in tree.get("tree", []):
            path = node.get("path", "")
            size = int(node.get("size") or 0)
            if (
                node.get("type") == "blob"
                and path.lower().endswith(".pbix")
                and self.args.min_size <= size <= self.args.max_size
                and node.get("sha") not in self.seen_blob
            ):
                found.append(
                    {
                        "repository": f"{owner}/{repo}",
                        "ref": ref,
                        "path": path,
                        "size": size,
                        "git_blob_sha": node.get("sha"),
                        "source_url": raw_url(owner, repo, ref, path),
                        "source_class": source_class,
                    }
                )
        found.sort(key=lambda item: (item["size"], item["path"].lower()))
        self.candidate_count += len(found)
        return found

    def try_download(self, candidate: dict) -> bool:
        blob = candidate.get("git_blob_sha")
        if blob and blob in self.seen_blob:
            return False
        ordinal = len(self.manifest) + 1
        file_name = f"{ordinal:03d}__{safe_name(pathlib.PurePosixPath(candidate['path']).name)}"
        dest = self.out / file_name
        for attempt in range(1, DOWNLOAD_ATTEMPTS + 1):
            try:
                digest, total = self._download_once(candidate["source_url"], dest)
                expected = int(candidate.get("size") or 0)
                if expected and total != expected:
                    raise RuntimeError(f"size mismatch expected={expected} actual={total}")
                if total < self.args.min_size:
                    raise RuntimeError(f"file too small ({total} bytes), possible Git LFS pointer")
                if digest in self.seen_sha256:
                    dest.unlink(missing_ok=True)
                    if blob:
                        self.seen_blob.add(blob)
                    return False
                with dest.open("rb") as fh:
                    zip_like = fh.read(4).startswith(b"PK")
                self.manifest.append(
                    {
                        "index": ordinal,
                        "local_file": file_name,
                        "repository": candidate["repository"],
                        "ref": candidate["ref"],
                        "path": candidate["path"],
                        "source_url": candidate["source_url"],
                        "size": total,
                        "git_blob_sha": blob,
                        "sha256": digest,
                        "zip_like": zip_like,
                        "source_class": candidate["source_class"],
                    }
                )
                self.seen_sha256.add(digest)
                if blob:
                    self.seen_blob.add(blob)
                print(
                    f"ACCEPT {ordinal:03d}/{self.args.target} "
                    f"{candidate['repository']}::{candidate['path']} ({total} bytes)",
                    flush=True,
                )
                return True
            except Exception as exc:  # noqa: BLE001 - every failure is logged and retried
                dest.unlink(missing_ok=True)
                self.log_event(
                    stage="download",
                    repository=candidate["repository"],
                    path=candidate["path"],
                    attempt=attempt,
                    error=f"{type(exc).__name__}: {exc}",
                )
                time.sleep(attempt)
        return False

    def _download_once(self, url: str, dest: pathlib.Path) -> tuple[str, int]:
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        digest = hashlib.sha256()
        total = 0
        with urllib.request.urlopen(request, timeout=300) as response, dest.open("wb") as fh:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                fh.write(chunk)
                digest.update(chunk)
                total += len(chunk)
                if total > self.args.max_size:
                    raise RuntimeError("download exceeded max size")
        return digest.hexdigest(), total

    def search_repositories(self) -> list[tuple[str, str]]:
        repositories: list[tuple[str, str]] = []
        seen = {f"{OFFICIAL_REPO[0]}/{OFFICIAL_REPO[1]}"}
        for query in SEARCH_QUERIES:
            url = "https://api.github.com/search/repositories?" + urllib.parse.urlencode(
                {"q": query, "sort": "updated", "order": "desc", "per_page": 100}
            )
            try:
                payload = get_json(url, self.token)
            except Exception as exc:  # noqa: BLE001
                self.log_event(stage="search", query=query, error=f"{type(exc).__name__}: {exc}")
                continue
            for item in payload.get("items", []):
                full_name = item.get("full_name")
                if isinstance(full_name, str) and full_name not in seen and not item.get("fork"):
                    seen.add(full_name)
                    repositories.append((full_name, item.get("default_branch") or "main"))
            time.sleep(2)
        return repositories

    def default_branch(self, owner: str, repo: str) -> str:
        info = get_json(f"https://api.github.com/repos/{owner}/{repo}", self.token)
        return info.get("default_branch") or "main"

    def build(self) -> None:
        owner, repo, ref = OFFICIAL_REPO
        try:
            ref = ref or self.default_branch(owner, repo)
            for candidate in self.tree_candidates(owner, repo, ref, "official-microsoft"):
                if self.done():
                    break
                self.try_download(candidate)
        except Exception as exc:  # noqa: BLE001
            self.log_event(stage="tree", repository=f"{owner}/{repo}", error=f"{type(exc).__name__}: {exc}")

        if not self.done() and self.args.allow_search:
            tree_requests = 0
            for full_name, branch in self.search_repositories():
                if self.done() or tree_requests >= MAX_TREE_REQUESTS:
                    break
                repo_owner, repo_name = full_name.split("/", 1)
                tree_requests += 1
                try:
                    candidates = self.tree_candidates(repo_owner, repo_name, branch, "public-github")
                except urllib.error.HTTPError as exc:
                    self.log_event(stage="tree", repository=full_name, error=f"HTTPError: {exc.code} {exc.reason}")
                    if exc.code in (403, 429):
                        time.sleep(5)
                    continue
                except Exception as exc:  # noqa: BLE001
                    self.log_event(stage="tree", repository=full_name, error=f"{type(exc).__name__}: {exc}")
                    continue
                for candidate in candidates:
                    if self.done():
                        break
                    self.try_download(candidate)

    def verify(self) -> None:
        for item in self.manifest:
            path = self.out / item["local_file"]
            actual = hashlib.sha256(path.read_bytes()).hexdigest()
            if actual != item["sha256"]:
                raise SystemExit(f"hash verification failed: {path}")

    def write_outputs(self) -> dict:
        (self.out / "manifest.json").write_text(json.dumps(self.manifest, indent=2), encoding="utf-8")
        if self.manifest:
            with (self.out / "manifest.csv").open("w", newline="", encoding="utf-8") as fh:
                writer = csv.DictWriter(fh, fieldnames=list(self.manifest[0].keys()))
                writer.writeheader()
                writer.writerows(self.manifest)
        summary = {
            "target": self.args.target,
            "selected_count": len(self.manifest),
            "distinct_sha256_count": len(self.seen_sha256),
            "candidate_count": self.candidate_count,
            "total_bytes": sum(item["size"] for item in self.manifest),
            "zip_like_count": sum(1 for item in self.manifest if item["zip_like"]),
            "official_microsoft_count": sum(
                1 for item in self.manifest if item["source_class"] == "official-microsoft"
            ),
            "public_github_count": sum(
                1 for item in self.manifest if item["source_class"] == "public-github"
            ),
            "event_count": len(self.events),
        }
        (self.out / "corpus-summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        (self.out / "events.json").write_text(json.dumps(self.events, indent=2), encoding="utf-8")
        return summary


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--target", type=int, default=25, help="number of files to collect (default: 25)")
    parser.add_argument("--out", default="corpus", help="output directory (default: corpus)")
    parser.add_argument("--min-size", type=int, default=10_000, help="minimum blob size in bytes")
    parser.add_argument("--max-size", type=int, default=75_000_000, help="maximum blob size in bytes")
    parser.add_argument(
        "--allow-search",
        action="store_true",
        help="also search public GitHub repositories beyond the official Microsoft samples",
    )
    parser.add_argument(
        "--best-effort",
        action="store_true",
        help="exit 0 even if fewer than --target files were collected",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN") or ""
    if not token:
        print("WARNING: no GH_TOKEN/GITHUB_TOKEN set; GitHub API rate limits will be severe", file=sys.stderr)

    builder = CorpusBuilder(args, token)
    builder.build()
    builder.verify()
    summary = builder.write_outputs()
    print(json.dumps(summary, indent=2))

    if len(builder.manifest) < args.target and not args.best_effort:
        print(
            f"ERROR: collected {len(builder.manifest)}/{args.target} files "
            "(use --best-effort to tolerate a partial corpus)",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
