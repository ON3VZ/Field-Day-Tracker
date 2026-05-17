"""
setup_github_pages.py
=====================
One-time setup script — run this ONCE from your local PC.

What it does
------------
1. Creates the gh-pages branch (from main)
2. Pushes a "coming soon" placeholder index.html to gh-pages
3. Changes GitHub Pages source to gh-pages branch
4. Prints the live URL

Run
---
    python setup_github_pages.py

You will be prompted for your GitHub token.
The token needs: Contents = Read+Write  (fine-grained, scoped to this repo)
"""

import base64
import getpass
import json
import sys
import urllib.error
import urllib.request

REPO    = "ON3VZ/Field-Day-Tracker"
BRANCH  = "gh-pages"
API     = "https://api.github.com"


def api(method, token, path, body=None):
    url  = API + path
    data = json.dumps(body).encode() if body else None
    req  = urllib.request.Request(url, data=data, method=method, headers={
        "Authorization":        f"Bearer {token}",
        "Accept":               "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent":           "N1MM-FDT-Setup/1.0",
        "Content-Type":         "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            raw = r.read()
            return json.loads(raw) if raw else {}, r.status
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        return json.loads(raw) if raw else {}, e.code


PLACEHOLDER = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="refresh" content="60">
<title>Field Day Tracker — Live</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: "Segoe UI", system-ui, sans-serif;
    background: #1e3a5f; color: #fff;
    min-height: 100vh; display: flex;
    align-items: center; justify-content: center;
  }
  .card {
    text-align: center; padding: 48px 32px;
    background: rgba(255,255,255,.08);
    border-radius: 16px; max-width: 440px;
  }
  h1 { font-size: 1.8rem; margin: 16px 0 8px; }
  p  { color: #aac4e0; line-height: 1.6; }
  .badge {
    display: inline-block; background: #2a5298;
    padding: 4px 14px; border-radius: 20px;
    font-size: .8rem; margin-top: 24px; color: #aac4e0;
  }
</style>
</head>
<body>
<div class="card">
  <div style="font-size:4rem">📻</div>
  <h1>Field Day Tracker</h1>
  <p>
    The live station matrix will appear here<br>
    once the field day starts and the first<br>
    publish is triggered from the desktop app.
  </p>
  <div class="badge">🔄 Auto-refresh every 60 seconds</div>
</div>
</body>
</html>"""


def main():
    print()
    print("=" * 52)
    print("  N1MM Field Day Tracker — GitHub Pages Setup")
    print("=" * 52)
    print()
    print(f"  Repository: {REPO}")
    print()

    token = getpass.getpass("  Paste your GitHub token (hidden): ").strip()
    if not token:
        print("[ERROR] No token entered.")
        sys.exit(1)

    print()
    print("  Checking token access...")
    d, s = api("GET", token, f"/repos/{REPO}")
    if s != 200:
        print(f"[ERROR] Cannot access repo ({s}): {d.get('message', '')}")
        sys.exit(1)
    default = d.get("default_branch", "main")
    print(f"  ✅  Repo: {d['full_name']}  (default branch: {default})")

    # Get HEAD SHA of default branch
    d2, _ = api("GET", token, f"/repos/{REPO}/branches/{default}")
    sha = d2["commit"]["sha"]
    print(f"  ✅  HEAD SHA: {sha[:12]}...")

    # Create gh-pages branch if needed
    d3, s3 = api("GET", token, f"/repos/{REPO}/branches/{BRANCH}")
    if s3 == 200:
        print(f"  ✅  Branch '{BRANCH}' already exists")
    else:
        d4, s4 = api("POST", token, f"/repos/{REPO}/git/refs", {
            "ref": f"refs/heads/{BRANCH}",
            "sha": sha,
        })
        if s4 == 201:
            print(f"  ✅  Created branch '{BRANCH}'")
        else:
            print(f"[ERROR] Could not create branch ({s4}): {d4.get('message','')}")
            sys.exit(1)

    # Push placeholder index.html
    b64 = base64.b64encode(PLACEHOLDER.encode()).decode()
    d5, s5 = api("GET", token,
                 f"/repos/{REPO}/contents/index.html?ref={BRANCH}")
    body = {
        "message": "Setup: GitHub Pages live matrix placeholder",
        "content": b64,
        "branch":  BRANCH,
    }
    if s5 == 200:
        body["sha"] = d5.get("sha")

    d6, s6 = api("PUT", token, f"/repos/{REPO}/contents/index.html", body)
    if s6 in (200, 201):
        print(f"  ✅  Pushed index.html to '{BRANCH}'")
    else:
        print(f"[ERROR] Could not push index.html ({s6}): {d6.get('message','')}")
        sys.exit(1)

    # Enable / update GitHub Pages to use gh-pages branch
    d7, s7 = api("GET", token, f"/repos/{REPO}/pages")
    if s7 == 200:
        # Already enabled — update source
        d8, s8 = api("PUT", token, f"/repos/{REPO}/pages", {
            "source": {"branch": BRANCH, "path": "/"},
        })
        url = d7.get("html_url", f"https://on3vz.github.io/Field-Day-Tracker/")
        print(f"  ✅  GitHub Pages source updated to '{BRANCH}'")
    else:
        d9, s9 = api("POST", token, f"/repos/{REPO}/pages", {
            "source": {"branch": BRANCH, "path": "/"},
        })
        url = d9.get("html_url", f"https://on3vz.github.io/Field-Day-Tracker/")
        if s9 in (201, 409):
            print(f"  ✅  GitHub Pages enabled on '{BRANCH}'")
        else:
            print(f"  ⚠️   Pages API returned {s9} — set manually if needed")

    print()
    print("=" * 52)
    print(f"  🌐  Live URL: {url}")
    print("=" * 52)
    print()
    print("  Next steps:")
    print("  1. Wait 1-2 minutes for GitHub to deploy")
    print(f"  2. Visit: {url}")
    print("  3. In the app: Tools → Settings → 📡 Publish tab")
    print(f"     - Paste your token")
    print(f"     - Repository: {REPO}")
    print(f"     - Enable auto-publish")
    print()


if __name__ == "__main__":
    main()
