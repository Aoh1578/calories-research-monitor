#!/usr/bin/env python
"""Deploy the Calories Research Monitor to GitHub Pages.

The repository root is the research-monitor folder. GitHub Pages is configured
for the `docs/` directory on the default branch.
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "data.json"
DOCS_DATA_PATH = ROOT / "docs" / "data.json"
RUNS_DIR = ROOT / "runs"
REPO_NAME = "calories-research-monitor"


def run(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True)
    if check and proc.returncode != 0:
        raise RuntimeError(
            f"command failed: {' '.join(cmd)}\nexit={proc.returncode}\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
        )
    return proc


def write_deploy_log(status: str, details: dict) -> None:
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "time": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "status": status,
        **details,
    }
    (RUNS_DIR / "deploy-last.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")


def gh_user() -> str:
    proc = run(["gh", "api", "user", "--jq", ".login"])
    return proc.stdout.strip()


def repo_exists(owner: str) -> bool:
    proc = run(["gh", "repo", "view", f"{owner}/{REPO_NAME}"], check=False)
    return proc.returncode == 0


def ensure_git_repo(owner: str) -> None:
    if not (ROOT / ".git").exists():
        run(["git", "init"])
        run(["git", "branch", "-M", "main"])
    remote = run(["git", "remote"], check=False).stdout.split()
    if "origin" not in remote:
        run(["git", "remote", "add", "origin", f"https://github.com/{owner}/{REPO_NAME}.git"])


def ensure_github_repo(owner: str) -> None:
    if not repo_exists(owner):
        run([
            "gh", "repo", "create", f"{owner}/{REPO_NAME}",
            "--public",
            "--description", "Static evidence ledger for the Calories book research monitor.",
        ])


def commit_and_push() -> None:
    run(["git", "add", "."])
    status = run(["git", "status", "--porcelain"]).stdout.strip()
    if status:
        run(["git", "commit", "-m", "chore: update research monitor site"])
    run(["git", "push", "-u", "origin", "main"])


def ensure_pages(owner: str) -> str:
    repo = f"{owner}/{REPO_NAME}"
    # Try to read Pages first. If not enabled, create a docs-folder deployment.
    view = run(["gh", "api", f"repos/{repo}/pages"], check=False)
    if view.returncode != 0:
        create_payload = '{"source":{"branch":"main","path":"/docs"}}'
        create = run([
            "gh", "api", f"repos/{repo}/pages",
            "-X", "POST",
            "-H", "Accept: application/vnd.github+json",
            "--input", "-",
        ], check=False)
        # gh --input - needs stdin, so fall back to shell-free temp file if needed.
        if create.returncode != 0:
            tmp = ROOT / "runs" / "pages-create.json"
            tmp.write_text(create_payload, encoding="utf-8")
            create = run([
                "gh", "api", f"repos/{repo}/pages",
                "-X", "POST",
                "-H", "Accept: application/vnd.github+json",
                "--input", str(tmp),
            ], check=False)
            if create.returncode != 0 and "already exists" not in (create.stderr + create.stdout).lower():
                raise RuntimeError(f"failed to enable GitHub Pages\nstdout:\n{create.stdout}\nstderr:\n{create.stderr}")
    else:
        # Make sure source remains main/docs.
        payload = '{"source":{"branch":"main","path":"/docs"}}'
        tmp = ROOT / "runs" / "pages-update.json"
        tmp.write_text(payload, encoding="utf-8")
        run([
            "gh", "api", f"repos/{repo}/pages",
            "-X", "PUT",
            "-H", "Accept: application/vnd.github+json",
            "--input", str(tmp),
        ], check=False)
    return f"https://{owner}.github.io/{REPO_NAME}/"


def main() -> int:
    try:
        if not DATA_PATH.exists():
            raise FileNotFoundError(DATA_PATH)
        DOCS_DATA_PATH.write_text(DATA_PATH.read_text(encoding="utf-8"), encoding="utf-8")
        owner = gh_user()
        ensure_github_repo(owner)
        ensure_git_repo(owner)
        commit_and_push()
        url = ensure_pages(owner)

        # Save site_url into data after URL is known, then push that tiny update.
        data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
        if data.get("site_url") != url:
            data["site_url"] = url
            DATA_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            DOCS_DATA_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            run(["git", "add", "data/data.json", "docs/data.json"])
            run(["git", "commit", "-m", "chore: record site url"], check=False)
            run(["git", "push", "origin", "main"])

        write_deploy_log("success", {"url": url, "repo": f"{owner}/{REPO_NAME}"})
        print(json.dumps({"success": True, "url": url, "repo": f"{owner}/{REPO_NAME}"}, indent=2))
        return 0
    except Exception as exc:
        write_deploy_log("failed", {"error": str(exc)})
        print(json.dumps({"success": False, "error": str(exc)}, indent=2), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
