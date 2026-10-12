#!/usr/bin/env python3
"""Generates assets/activity.svg and assets/trophies.svg from the GitHub GraphQL API."""
import datetime as dt
import json
import os
import sys
import urllib.request

LOGIN = os.environ.get("PROFILE_LOGIN") or os.environ.get("GITHUB_REPOSITORY_OWNER", "anaaclra04")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
OUT = os.environ.get("OUT_DIR", "assets")

INK = "#5B3A4A"
MUTED = "#9B7A8A"
PINK = "#E8689B"
SOFT = "#F9A8C9"
BLUSH = "#FFD1DC"
PAPER = "#FFF5F8"

QUERY = """
query($login: String!) {
  user(login: $login) {
    followers { totalCount }
    repositories(ownerAffiliations: OWNER, privacy: PUBLIC) { totalCount }
    contributionsCollection {
      totalCommitContributions
      totalPullRequestContributions
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}
"""


def fetch():
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": LOGIN}}).encode(),
        headers={"Authorization": f"bearer {TOKEN}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        payload = json.load(r)
    if "errors" in payload:
        sys.exit(f"GraphQL error: {payload['errors']}")
    return payload["data"]["user"]


def days_from(user):
    weeks = user["contributionsCollection"]["contributionCalendar"]["weeks"]
    days = [d for w in weeks for d in w["contributionDays"]]
    return sorted(days, key=lambda d: d["date"])


def longest_streak(days):
    best = cur = 0
    for d in days:
        cur = cur + 1 if d["contributionCount"] > 0 else 0
        best = max(best, cur)
    return best


def activity_svg(days, span=30):
    days = days[-span:]
    W, H = 900, 280
    left, right, top, bottom = 56, 28, 56, 48
    cw, ch = W - left - right, H - top - bottom
    counts = [d["contributionCount"] for d in days]
    ymax = max(max(counts), 4)
    step = max(1, -(-ymax // 4))
    ymax = step * 4

    def x(i):
        return left + cw * i / max(len(days) - 1, 1)

    def y(v):
        return top + ch - ch * v / ymax

    pts = [(x(i), y(c)) for i, c in enumerate(counts)]
    line = " ".join(f"{px:.1f},{py:.1f}" for px, py in pts)
    area = f"{left},{top + ch} {line} {x(len(days) - 1):.1f},{top + ch}"

    grid = ""
    for k in range(5):
        v = step * k
        gy = y(v)
        grid += (
            f'<line x1="{left}" y1="{gy:.1f}" x2="{W - right}" y2="{gy:.1f}" stroke="{BLUSH}" stroke-width="1" stroke-dasharray="3 5"/>'
            f'<text x="{left - 12}" y="{gy + 4:.1f}" text-anchor="end" font-size="11" fill="{MUTED}">{v}</text>'
        )

    labels = ""
    for i, d in enumerate(days):
        if i % 5 == 0 or i == len(days) - 1:
            date = dt.date.fromisoformat(d["date"])
            labels += f'<text x="{x(i):.1f}" y="{H - 20}" text-anchor="middle" font-size="11" fill="{MUTED}">{date.strftime("%b %d")}</text>'

    dots = "".join(
        f'<circle cx="{px:.1f}" cy="{py:.1f}" r="3.5" fill="#fff" stroke="{PINK}" stroke-width="2"/>'
        for (px, py), c in zip(pts, counts)
        if c > 0
    )
    total = sum(counts)

    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="'Segoe UI', Arial, sans-serif">
  <defs>
    <linearGradient id="fill" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="{SOFT}" stop-opacity="0.55"/>
      <stop offset="1" stop-color="{SOFT}" stop-opacity="0.04"/>
    </linearGradient>
  </defs>
  <rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="14" fill="{PAPER}" stroke="{BLUSH}"/>
  <text x="{left}" y="32" font-size="16" font-weight="600" fill="{PINK}">contributions · last {len(days)} days</text>
  <text x="{W - right}" y="32" text-anchor="end" font-size="13" fill="{MUTED}">{total} total</text>
  {grid}
  <polygon points="{area}" fill="url(#fill)"/>
  <polyline points="{line}" fill="none" stroke="{PINK}" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round"/>
  {dots}
  {labels}
</svg>
"""


def trophies_svg(user, days):
    cc = user["contributionsCollection"]
    items = [
        (cc["contributionCalendar"]["totalContributions"], "contributions", "last year"),
        (cc["totalCommitContributions"], "commits", "last year"),
        (cc["totalPullRequestContributions"], "pull requests", "last year"),
        (user["repositories"]["totalCount"], "public repos", "total"),
        (longest_streak(days), "day streak", "longest"),
        (sum(1 for d in days if d["contributionCount"] > 0), "active days", "last year"),
    ]
    cw, gap, H = 138, 12, 150
    W = len(items) * cw + (len(items) - 1) * gap
    tones = [PINK, SOFT]
    cards = ""
    for i, (value, label, sub) in enumerate(items):
        cx0 = i * (cw + gap)
        mid = cx0 + cw / 2
        tone = tones[i % 2]
        cards += f"""
  <g>
    <rect x="{cx0 + 0.5}" y="0.5" width="{cw - 1}" height="{H - 1}" rx="14" fill="{PAPER}" stroke="{BLUSH}"/>
    <circle cx="{mid}" cy="40" r="20" fill="{tone}" opacity="0.18"/>
    <path d="M{mid - 8} 32h16v7a8 8 0 0 1-16 0z M{mid - 8} 34h-4a4 4 0 0 0 4 6 M{mid + 8} 34h4a4 4 0 0 1-4 6 M{mid} 47v5 M{mid - 5} 52h10"
          fill="none" stroke="{tone}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
    <text x="{mid}" y="94" text-anchor="middle" font-size="26" font-weight="700" fill="{INK}">{value}</text>
    <text x="{mid}" y="114" text-anchor="middle" font-size="12" font-weight="600" fill="{PINK}">{label}</text>
    <text x="{mid}" y="131" text-anchor="middle" font-size="10.5" fill="{MUTED}">{sub}</text>
  </g>"""
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="'Segoe UI', Arial, sans-serif">{cards}
</svg>
"""


def main():
    user = None if os.environ.get("MOCK") else fetch()
    if os.environ.get("MOCK"):
        base = dt.date.today() - dt.timedelta(days=364)
        import random
        random.seed(4)
        days = [
            {"date": (base + dt.timedelta(days=i)).isoformat(), "contributionCount": random.choice([0, 0, 1, 2, 3, 5, 8])}
            for i in range(365)
        ]
        user = {
            "followers": {"totalCount": 3},
            "repositories": {"totalCount": 12},
            "contributionsCollection": {
                "totalCommitContributions": 210,
                "totalPullRequestContributions": 14,
                "contributionCalendar": {"totalContributions": sum(d["contributionCount"] for d in days), "weeks": [{"contributionDays": days}]},
            },
        }
    days = days_from(user)
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "activity.svg"), "w") as f:
        f.write(activity_svg(days))
    with open(os.path.join(OUT, "trophies.svg"), "w") as f:
        f.write(trophies_svg(user, days))
    print("wrote", OUT)


if __name__ == "__main__":
    main()
