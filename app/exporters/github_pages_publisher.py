"""
app/exporters/github_pages_publisher.py
=========================================
Publishes the field day matrix as a GitHub Pages site using the
GitHub REST API (no git installation required).

How it works
------------
1. Generate the matrix HTML via :mod:`app.exporters.html_exporter`.
2. Base64-encode the HTML content.
3. Use the GitHub Contents API to create or update ``index.html`` on
   the ``gh-pages`` branch of the configured repository.
4. If the ``gh-pages`` branch does not exist it is created automatically
   from the repo's default branch.

Rate limits
-----------
The GitHub API allows 5 000 authenticated requests per hour.
Publishing once every 2 minutes = 30 calls/hour — well within limits.

Token requirements
------------------
The token needs **only**:
  - Repository: Contents → Read and Write
  (Fine-grained token scoped to the single Field Day Tracker repo)

Public API
----------
GHPagesPublisher.publish(token, repo, fieldday, stations, matrix, settings)
    → PublishResult

GHPagesPublisher.validate_token(token, repo)
    → (ok: bool, message: str)
"""

from __future__ import annotations

import base64
import json
import logging
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone

from app.core.models import AppSettings, FieldDay, Station, StationBandStatus
from app.exporters.html_exporter import HTMLExporter

log = logging.getLogger(__name__)

_API_BASE   = "https://api.github.com"
_GH_BRANCH  = "gh-pages"
_INDEX_PATH = "index.html"
_USER_AGENT = "N1MM-FieldDay-Tracker/1.0"


@dataclass
class PublishResult:
    success: bool
    url: str = ""
    message: str = ""
    timestamp_utc: str = ""


class GHPagesPublisher:
    """Stateless GitHub Pages publisher."""

    @classmethod
    def publish(
        cls,
        token: str,
        repo: str,
        fieldday: FieldDay,
        stations: list[Station],
        matrix: dict[tuple[str, str], StationBandStatus],
        settings: AppSettings | None = None,
        refresh_seconds: int = 60,
    ) -> PublishResult:
        """Generate the matrix HTML and push it to gh-pages.

        Parameters
        ----------
        token:
            Plaintext GitHub personal access token (decrypt before calling).
        repo:
            Repository in ``owner/name`` format, e.g. ``ON3VZ/Field-Day-Tracker``.
        fieldday / stations / matrix / settings:
            Current field day data.
        refresh_seconds:
            Auto-refresh interval embedded in the HTML page.

        Returns
        -------
        PublishResult
        """
        if not token or not repo:
            return PublishResult(
                success=False,
                message="Token or repository not configured.",
            )

        # ── Generate HTML ────────────────────────────────────────────────────
        import tempfile, pathlib
        with tempfile.TemporaryDirectory() as tmp:
            html_path = pathlib.Path(tmp) / "index.html"
            result = HTMLExporter.export(
                html_path, fieldday, stations, matrix, settings, refresh_seconds
            )
            if not result.success:
                return PublishResult(success=False,
                                     message=f"HTML generation failed: {result.error}")
            html_bytes = html_path.read_bytes()

        html_b64 = base64.b64encode(html_bytes).decode("ascii")

        try:
            # ── Ensure gh-pages branch exists ────────────────────────────────
            cls._ensure_branch(token, repo)

            # ── Get existing file SHA (required for update) ──────────────────
            sha = cls._get_file_sha(token, repo, _INDEX_PATH)

            # ── Push the file ────────────────────────────────────────────────
            ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
            commit_msg = f"Field Day update: {fieldday.name} @ {ts}"

            body: dict = {
                "message": commit_msg,
                "content": html_b64,
                "branch": _GH_BRANCH,
            }
            if sha:
                body["sha"] = sha  # required to update existing file

            cls._api_put(
                token, repo,
                f"/repos/{repo}/contents/{_INDEX_PATH}",
                body,
            )

            # ── Derive the Pages URL ─────────────────────────────────────────
            owner, repo_name = repo.split("/", 1)
            pages_url = f"https://{owner.lower()}.github.io/{repo_name}/"

            log.info("Published to GitHub Pages: %s", pages_url)
            return PublishResult(
                success=True,
                url=pages_url,
                message=f"Published successfully at {ts}",
                timestamp_utc=datetime.now(timezone.utc).isoformat(),
            )

        except _APIError as exc:
            log.error("GitHub API error: %s", exc)
            return PublishResult(success=False, message=str(exc))
        except Exception as exc:  # noqa: BLE001
            log.error("Unexpected publish error: %s", exc)
            return PublishResult(success=False, message=f"Unexpected error: {exc}")

    @classmethod
    def validate_token(cls, token: str, repo: str) -> tuple[bool, str]:
        """Check that the token can access the repository.

        Returns
        -------
        (ok, message)
        """
        if not token or not repo:
            return False, "Token and repository are required."
        try:
            data = cls._api_get(token, f"/repos/{repo}")
            name = data.get("full_name", repo)
            return True, f"✅  Access confirmed for: {name}"
        except _APIError as exc:
            return False, str(exc)
        except Exception as exc:  # noqa: BLE001
            return False, f"Connection error: {exc}"

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @classmethod
    def _ensure_branch(cls, token: str, repo: str) -> None:
        """Create the gh-pages branch if it does not exist."""
        # Check if branch exists
        try:
            cls._api_get(token, f"/repos/{repo}/branches/{_GH_BRANCH}")
            return  # already exists
        except _APIError as exc:
            if "404" not in str(exc):
                raise

        # Get the SHA of the default branch HEAD
        repo_data = cls._api_get(token, f"/repos/{repo}")
        default_branch = repo_data.get("default_branch", "main")
        branch_data = cls._api_get(
            token, f"/repos/{repo}/branches/{default_branch}"
        )
        sha = branch_data["commit"]["sha"]

        # Create the gh-pages branch
        cls._api_post(token, f"/repos/{repo}/git/refs", {
            "ref": f"refs/heads/{_GH_BRANCH}",
            "sha": sha,
        })
        log.info("Created gh-pages branch in %s", repo)

    @classmethod
    def _get_file_sha(
        cls, token: str, repo: str, file_path: str
    ) -> str | None:
        """Return the blob SHA of an existing file, or None if not found."""
        try:
            data = cls._api_get(
                token,
                f"/repos/{repo}/contents/{file_path}?ref={_GH_BRANCH}",
            )
            return data.get("sha")
        except _APIError as exc:
            if "404" in str(exc):
                return None
            raise

    @classmethod
    def _api_get(cls, token: str, path: str) -> dict:
        url = _API_BASE + path
        req = urllib.request.Request(
            url,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": _USER_AGENT,
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise _APIError(f"HTTP {exc.code}: {body[:200]}") from exc
        except urllib.error.URLError as exc:
            raise _APIError(f"Network error: {exc.reason}") from exc

    @classmethod
    def _api_post(cls, token: str, path: str, body: dict) -> dict:
        return cls._api_request("POST", token, path, body)

    @classmethod
    def _api_put(cls, token: str, repo: str, path: str, body: dict) -> dict:
        return cls._api_request("PUT", token, path, body)

    @classmethod
    def _api_request(
        cls, method: str, token: str, path: str, body: dict
    ) -> dict:
        url = _API_BASE + path if path.startswith("/") else path
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            method=method,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "Content-Type": "application/json",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": _USER_AGENT,
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as exc:
            body_text = exc.read().decode("utf-8", errors="replace")
            raise _APIError(f"HTTP {exc.code}: {body_text[:300]}") from exc
        except urllib.error.URLError as exc:
            raise _APIError(f"Network error: {exc.reason}") from exc


class _APIError(Exception):
    """Raised when the GitHub API returns an error."""
