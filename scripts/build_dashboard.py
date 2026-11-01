#!/usr/bin/env python3
"""
Builds assets/dashboard.svg - the profile dashboard for github.com/moneshram.

Design reference: dark "profile hub" layout (near-black canvas #0B0D10,
#14171C cards, #39D353 green accent), left identity sidebar + right grid.

All numbers are LIVE (GitHub REST API + contributions calendar + avatar).
Re-run any time to refresh:  python3 scripts/build_dashboard.py
"""
import base64
import io
import json
import os
import re
import sys
import urllib.request
from datetime import datetime

LOGIN = os.environ.get("GH_LOGIN", "moneshram")
OUT = os.environ.get("OUT", "assets/dashboard.svg")
UA = {"User-Agent": "profile-dashboard-builder", "Accept": "application/vnd.github+json"}

# ---------------------------------------------------------------- palette
BG = "#0B0D10"
CARD = "#14171C"
CARD_HI = "#191D23"
BORDER = "#232830"
TXT = "#E6EDF3"
MUTED = "#8B949E"
DIM = "#6E7681"
GREEN = "#39D353"
GREEN_DK = "#0E4429"
L0, L1, L2, L3, L4 = "#161B22", "#0E4429", "#006D32", "#26A641", "#39D353"
SANS = "'Inter','Segoe UI',-apple-system,BlinkMacSystemFont,Helvetica,Arial,sans-serif"
MONO = "'SF Mono',ui-monospace,'JetBrains Mono',Menlo,Consolas,monospace"

W = 880
PAD = 20
H = 748

# ---------------------------------------------------------------- data
def get(url, raw=False):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read() if raw else json.loads(r.read())


def fetch_all():
    user = get(f"https://api.github.com/users/{LOGIN}")
    repos = get(f"https://api.github.com/users/{LOGIN}/repos?per_page=100&sort=updated")

    langs = {}
    for r in repos:
        for k, v in get(f"https://api.github.com/repos/{LOGIN}/{r['name']}/languages").items():
            langs[k] = langs.get(k, 0) + v

    html = get(f"https://github.com/users/{LOGIN}/contributions", raw=True).decode("utf-8", "ignore")
    cells = re.findall(r'data-date="(\d{4}-\d{2}-\d{2})"[^>]*?data-level="(\d)"', html)
    if not cells:
        pairs = re.findall(r'data-level="(\d)"[^>]*?data-date="(\d{4}-\d{2}-\d{2})"', html)
        cells = [(d, l) for l, d in pairs]
    total = re.search(r'([\d,]+)\s+contributions?\s+in the last year', html)
    total = int(total.group(1).replace(",", "")) if total else 0

    avatar = get(user["avatar_url"], raw=True)
    try:
        from PIL import Image
        im = Image.open(io.BytesIO(avatar)).convert("RGB").resize((200, 200), Image.LANCZOS)
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=88, optimize=True)
        avatar = buf.getvalue()
        mime = "jpeg"
    except Exception:
        mime = "png"

    return {
        "user": user, "repos": repos, "langs": langs,
        "cells": cells, "total": total,
        "avatar": base64.b64encode(avatar).decode(), "mime": mime,
    }


# ---------------------------------------------------------------- drawing
def esc(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
             .replace('"', "&quot;"))


def tw(s, size, bold=False):
    """Rough text width - good enough to prevent overflow."""
    return len(s) * size * (0.56 if bold else 0.53)


def fit(s, size, maxw, bold=False):
    if tw(s, size, bold) <= maxw:
        return s
    out = s
    while out and tw(out + "\u2026", size, bold) > maxw:
        out = out[:-1]
    return out.rstrip() + "\u2026"


class S:
    def __init__(self):
        self.p = []

    def add(self, *chunks):
        self.p.extend(chunks)

    def rect(self, x, y, w, h, fill=CARD, r=10, stroke=BORDER, sw=1):
        st = f' stroke="{stroke}" stroke-width="{sw}"' if stroke else ""
        self.add(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" '
                 f'rx="{r}" ry="{r}" fill="{fill}"{st}/>')

    def text(self, x, y, s, size=12, fill=TXT, weight=400, anchor="start",
             mono=False, ls=None, opacity=None, maxw=None):
        if maxw:
            s = fit(s, size, maxw, weight >= 600)
        a = f' font-family="{MONO if mono else SANS}"'
        l = f' letter-spacing="{ls}"' if ls else ""
        o = f' opacity="{opacity}"' if opacity else ""
        self.add(f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" fill="{fill}" '
                 f'font-weight="{weight}" text-anchor="{anchor}"{a}{l}{o}>{esc(s)}</text>')

    def svg(self):
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
                f'viewBox="0 0 {W} {H}" role="img" aria-label="Monesh - GitHub profile dashboard">\n'
                + "\n".join(self.p) + "\n</svg>\n")


# ---------------------------------------------------------------- icons
def icon(d, x, y, size=12, color=GREEN, sw=1.6, fill="none"):
    return (f'<g transform="translate({x},{y}) scale({size/24:.3f})">'
            f'<path d="{d}" fill="{fill}" stroke="{color}" stroke-width="{sw}" '
            f'stroke-linecap="round" stroke-linejoin="round"/></g>')

I_PIN = "M12 21s7-6.2 7-11a7 7 0 1 0-14 0c0 4.8 7 11 7 11z M12 10.5a1.6 1.6 0 1 0 0-.1z"
I_CAP = "M2 8.5 12 4l10 4.5-10 4.5z M5 11v5c0 1.7 3.1 3 7 3s7-1.3 7-3v-5"
I_CAL = "M4 6h16v14H4z M8 3v4 M16 3v4 M4 10h16"
I_ARROW = "M13 5l7 7-7 7 M20 12H4"
I_STAR = "M12 3.5l2.7 5.6 6.1.8-4.5 4.3 1.1 6.1-5.4-2.9-5.4 2.9 1.1-6.1L3.2 9.9l6.1-.8z"
I_REFRESH = "M20 12a8 8 0 1 1-2.3-5.6 M20 4v4h-4"
I_REPO = "M4 4h6v6H4z M14 4h6v6h-6z M9 20h6 M4 14h6v6H4z"


# ---------------------------------------------------------------- build
def build(d):
    user, repos, langs, cells, total = d["user"], d["repos"], d["langs"], d["cells"], d["total"]
    s = S()

    stars = sum(r["stargazers_count"] for r in repos)
    n_repos = user["public_repos"]
    followers = user["followers"]
    following = user["following"]
    joined = datetime.strptime(user["created_at"], "%Y-%m-%dT%H:%M:%SZ")
    joined_lbl = joined.strftime("%b %Y")

    # language shares
    tot_bytes = sum(langs.values()) or 1
    ranked = sorted(langs.items(), key=lambda kv: -kv[1])
    top = ranked[:5]
    rest = sum(v for _, v in ranked[5:])
    if rest:
        top.append(("Other", rest))
    lang_rows = [(n, v / tot_bytes * 100) for n, v in top]

    s.add(f'<rect width="{W}" height="{H}" fill="{BG}"/>')

    # ---------------- top bar
    s.add(f'<rect x="{PAD}" y="16" width="26" height="26" rx="7" fill="{GREEN}"/>')
    s.text(PAD + 13, 34.5, "M", 14, "#07120A", 800, "middle")
    s.text(PAD + 36, 34, "MONESH", 14.5, TXT, 700, ls="0.14em")
    s.text(PAD + 122, 34, "GitHub Profile Dashboard", 11.5, MUTED)
    s.add(f'<circle cx="{W-PAD-96}" cy="29" r="3.5" fill="{GREEN}"/>')
    s.text(W - PAD, 33, f"live · {datetime.now():%b %Y}", 11, DIM, anchor="end")

    # ================= LEFT SIDEBAR =================
    LX, LY, LW = PAD, 70, 248
    LH = 448
    s.rect(LX, LY, LW, LH)
    cx = LX + LW / 2

    # avatar (circular clip)
    ax, ay, ar = cx, 128, 44
    s.add(f'<defs><clipPath id="av"><circle cx="{ax}" cy="{ay}" r="{ar}"/></clipPath></defs>')
    s.add(f'<circle cx="{ax}" cy="{ay}" r="{ar+3}" fill="none" stroke="{GREEN}" '
          f'stroke-opacity="0.55" stroke-width="2"/>')
    s.add(f'<image x="{ax-ar}" y="{ay-ar}" width="{ar*2}" height="{ar*2}" '
          f'clip-path="url(#av)" preserveAspectRatio="xMidYMid slice" '
          f'href="data:image/{d["mime"]};base64,{d["avatar"]}"/>')

    s.text(cx, 200, user.get("name") or LOGIN, 21, TXT, 700, "middle", maxw=LW - 28)
    s.text(cx, 220, "@" + LOGIN, 12.5, MUTED, 400, "middle")

    # follow button
    bw, bh = 108, 30
    s.add(f'<rect x="{cx-bw/2}" y="232" width="{bw}" height="{bh}" rx="15" fill="{GREEN}"/>')
    s.text(cx, 252, "Follow", 12.5, "#07120A", 700, "middle")

    # role chips
    chips = ["MCA Student", "AI / ML", "Full-Stack", "Big Data", "Chennai, IN"]
    cxp, cyp, ch, gap = LX + 14, 276, 22, 6
    maxx = LX + LW - 14
    for c in chips:
        cw = tw(c, 10.5) + 14
        if cxp + cw > maxx:
            cxp, cyp = LX + 14, cyp + ch + gap
        s.add(f'<rect x="{cxp}" y="{cyp}" width="{cw:.1f}" height="{ch}" rx="11" '
              f'fill="{CARD_HI}" stroke="{BORDER}"/>')
        s.text(cxp + cw / 2, cyp + 14.5, c, 10.5, MUTED, 500, "middle")
        cxp += cw + gap

    # meta rows
    meta_y = cyp + ch + 22
    s.add(f'<line x1="{LX+14}" y1="{meta_y-14}" x2="{LX+LW-14}" y2="{meta_y-14}" '
          f'stroke="{BORDER}"/>')
    rows = [
        (I_PIN, user.get("location") or "Chennai, India"),
        (I_CAP, "SCSVMV \u00b7 MCA 2025\u201327"),
        (I_CAL, f"Joined {joined_lbl}"),
    ]
    for i, (ic, label) in enumerate(rows):
        y = meta_y + i * 24
        s.add(icon(ic, LX + 16, y - 2, 13, GREEN))
        s.text(LX + 38, y + 8, label, 11.5, MUTED, maxw=LW - 58)

    # counts footer
    fy = LY + LH - 58
    s.add(f'<line x1="{LX+14}" y1="{fy}" x2="{LX+LW-14}" y2="{fy}" stroke="{BORDER}"/>')
    cols = [(n_repos, "Repos"), (followers, "Followers"), (following, "Following")]
    colw = (LW - 28) / 3
    for i, (v, lab) in enumerate(cols):
        ccx = LX + 14 + colw * i + colw / 2
        s.text(ccx, fy + 26, str(v), 16, TXT, 700, "middle", mono=True)
        s.text(ccx, fy + 42, lab.upper(), 8.5, DIM, 600, "middle", ls="0.09em")

    # ---------------- secondary card: currently building + links
    by0, bh = 530, 198
    s.rect(LX, by0, LW, bh)
    s.text(LX + 16, by0 + 28, "CURRENTLY BUILDING", 8.5, GREEN, 700, ls="0.11em")
    s.text(LX + 16, by0 + 50, "NeuroRisk AI", 13, TXT, 700, maxw=LW - 32)
    s.text(LX + 16, by0 + 68, "Stroke-risk classification", 10, MUTED, maxw=LW - 32)
    s.text(LX + 16, by0 + 82, "from clinical + demographic data", 10, MUTED, maxw=LW - 32)
    for i, c in enumerate(["React", "TypeScript", "Flask"]):
        w_ = tw(c, 9) + 12
        s.add(f'<rect x="{LX+16+i*(w_+5):.1f}" y="{by0+92}" width="{w_:.1f}" height="18" '
              f'rx="5" fill="{CARD_HI}" stroke="{BORDER}"/>')
        s.text(LX + 16 + i * (w_ + 5) + w_ / 2, by0 + 104.5, c, 9, MUTED, 500, "middle")

    s.add(f'<line x1="{LX+16}" y1="{by0+124}" x2="{LX+LW-16}" y2="{by0+124}" stroke="{BORDER}"/>')
    s.text(LX + 16, by0 + 144, "LINKS", 8.5, DIM, 700, ls="0.11em")
    links = [("GitHub", "github.com/" + LOGIN), ("LinkedIn", "in/monesh-v"), ("Site", "moneshram.github.io")]
    lx_, ly_ = LX + 16, by0 + 154
    for name, url in links:
        w_ = tw(name, 9.5) + 16
        s.add(f'<rect x="{lx_}" y="{ly_}" width="{w_:.1f}" height="22" rx="6" '
              f'fill="{CARD_HI}" stroke="{BORDER}"/>')
        s.text(lx_ + w_ / 2, ly_ + 14.5, name, 9.5, TXT, 500, "middle")
        lx_ += w_ + 6

    # ================= RIGHT COLUMN =================
    RX, RW = 284, 576
    s.rect(RX, 70, RW, 72)
    s.text(RX + 20, 104, "Welcome to your dashboard", 17.5, TXT, 700)
    s.text(RX + 20, 124, f"Your GitHub activity at a glance \u00b7 public data as of {datetime.now():%b %d, %Y}",
           11.5, MUTED)
    s.add(icon(I_REFRESH, RX + RW - 40, 92, 16, DIM))

    # ---------------- stat cards
    sy, sh = 154, 84
    cw = (RW - 3 * 10) / 4
    stats = [(n_repos, "Total Repos"), (stars, "All Stars"),
             (followers, "Followers"), (total, "Contributions")]
    for i, (v, lab) in enumerate(stats):
        x = RX + i * (cw + 10)
        s.rect(x, sy, cw, sh)
        s.text(x + 14, sy + 24, lab.upper(), 8.5, DIM, 600, ls="0.09em")
        s.text(x + 14, sy + 56, f"{v:,}", 25, TXT, 700, mono=True)
        s.add(f'<rect x="{x+14}" y="{sy+66}" width="22" height="2.5" rx="1.25" fill="{GREEN}"/>')

    # ---------------- contributions heatmap
    cy0 = 250
    s.rect(RX, cy0, RW, 186)
    s.text(RX + 20, cy0 + 26, "Contributions in the last 12 months", 13, TXT, 600)
    s.text(RX + RW - 20, cy0 + 26, f"{total:,} total", 11, MUTED, anchor="end")

    weeks = [cells[i:i + 7] for i in range(0, len(cells), 7)]
    cs_, gapc = 8, 2
    grid_w = len(weeks) * (cs_ + gapc) - gapc
    gx = RX + (RW - grid_w) / 2
    gy = cy0 + 46

    # month labels (suppress labels closer than 26px)
    lastm, lastx = None, -99
    for wi, wk in enumerate(weeks):
        if not wk:
            continue
        mo = int(wk[0][0][5:7])
        x = gx + wi * (cs_ + gapc)
        if mo != lastm and x - lastx >= 26:
            s.text(x, gy - 5, datetime(2000, mo, 1).strftime("%b"), 8.5, DIM, 500)
            lastx, lastm = x, mo
        elif mo != lastm:
            lastm = mo

    for wi, wk in enumerate(weeks):
        for di, (_, lvl) in enumerate(wk):
            col = [L0, L1, L2, L3, L4][int(lvl)]
            s.add(f'<rect x="{gx+wi*(cs_+gapc):.1f}" y="{gy+di*(cs_+gapc):.1f}" '
                  f'width="{cs_}" height="{cs_}" rx="2" fill="{col}"/>')

    ly = cy0 + 152
    s.text(RX + 20, ly + 9, "Less", 9.5, DIM)
    for i in range(5):
        s.add(f'<rect x="{RX+54+i*13}" y="{ly}" width="8" height="8" rx="2" '
              f'fill="{[L0, L1, L2, L3, L4][i]}"/>')
    s.text(RX + 54 + 5 * 13 + 6, ly + 9, "More", 9.5, DIM)
    s.text(RX + RW - 20, ly + 9, "github.com/" + LOGIN, 9.5, DIM, anchor="end")

    # ---------------- tech stack + languages
    ty, th = 448, 136
    tw_ = 344
    s.rect(RX, ty, tw_, th)
    s.text(RX + 18, ty + 26, "Tech Stack & Languages", 12.5, TXT, 600)
    stack = ["Python", "TypeScript", "React", "Flask", "Node.js", "SQLite",
             "Java", "Hadoop", "Hive", "Scikit-learn", "Git", "MapReduce"]
    px, py, ph, pg = RX + 18, ty + 38, 21, 6
    pmax = RX + tw_ - 18
    for c in stack:
        pw = tw(c, 10) + 16
        if px + pw > pmax:
            px, py = RX + 18, py + ph + pg
        s.add(f'<rect x="{px}" y="{py}" width="{pw:.1f}" height="{ph}" rx="6" '
              f'fill="{CARD_HI}" stroke="{BORDER}"/>')
        s.add(f'<circle cx="{px+8}" cy="{py+ph/2}" r="2" fill="{GREEN}" opacity="0.8"/>')
        s.text(px + 14, py + 14, c, 10, MUTED, 500)
        px += pw + pg

    lx = RX + tw_ + 10
    lw = RW - tw_ - 10
    s.rect(lx, ty, lw, th)
    s.text(lx + 16, ty + 26, "Most Used", 12.5, TXT, 600)
    s.text(lx + 16, ty + 40, "by code volume", 9.5, DIM)

    dcx, dcy, dr, dsw = lx + 62, ty + 88, 30, 11
    colors = [GREEN, "#58A6FF", "#D29922", "#BC8CFF", "#8B949E", "#30363D"]
    import math
    circ = 2 * math.pi * dr
    off = 0.0
    s.add(f'<circle cx="{dcx}" cy="{dcy}" r="{dr}" fill="none" stroke="{CARD_HI}" stroke-width="{dsw}"/>')
    for i, (name, pct) in enumerate(lang_rows):
        seg = circ * pct / 100
        s.add(f'<circle cx="{dcx}" cy="{dcy}" r="{dr}" fill="none" stroke="{colors[i % len(colors)]}" '
              f'stroke-width="{dsw}" stroke-dasharray="{seg-2:.2f} {circ-seg+2:.2f}" '
              f'stroke-dashoffset="{-off:.2f}" transform="rotate(-90 {dcx} {dcy})" '
              f'stroke-linecap="butt"/>')
        off += seg
    s.text(dcx, dcy + 4, f"{lang_rows[0][1]:.0f}%", 11, TXT, 700, "middle", mono=True)
    s.text(dcx, dcy + 15, lang_rows[0][0][:10], 7.5, DIM, 500, "middle")

    for i, (name, pct) in enumerate(lang_rows):
        ry = ty + 62 + i * 12.5
        s.add(f'<circle cx="{lx+104}" cy="{ry-3}" r="3" fill="{colors[i % len(colors)]}"/>')
        s.text(lx + 112, ry, fit(name, 9.5, 62), 9.5, MUTED)
        s.text(lx + lw - 14, ry, f"{pct:.1f}%", 9.5, DIM, 500, "end", mono=True)

    # ---------------- notable projects
    py0, ph0 = 596, 132
    s.rect(RX, py0, RW, ph0)
    s.text(RX + 18, py0 + 26, "Notable Projects", 12.5, TXT, 600)
    s.text(RX + RW - 18, py0 + 26, "3 repositories", 10, DIM, anchor="end")

    picks = []
    for want in ("NeuroRisk-AI", "movie-rating-analytics", "moneshram.github.io"):
        for r in repos:
            if r["name"] == want:
                picks.append(r)
    for r in repos:
        if len(picks) >= 3:
            break
        if r not in picks and r["name"] != LOGIN:
            picks.append(r)

    for i, r in enumerate(picks[:3]):
        y = py0 + 46 + i * 28
        s.add(icon(I_REPO, RX + 18, y - 9, 12, GREEN))
        s.text(RX + 38, y, fit(r["name"], 11.5, 200, True), 11.5, TXT, 600)
        lang = r.get("language") or "\u2014"
        s.text(RX + 246, y, "\u25cf " + lang, 9.5, MUTED)
        s.text(RX + RW - 18, y, f"\u2605 {r['stargazers_count']}", 9.5, DIM, anchor="end", mono=True)
        desc = (r.get("description") or "").replace("**", "")
        s.text(RX + 38, y + 12, fit(desc, 9.5, RW - 130), 9.5, DIM)

    return s.svg()


if __name__ == "__main__":
    data = fetch_all()
    svg = build(data)
    os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"wrote {OUT}  ({len(svg)/1024:.1f} KB)  "
          f"| repos={data['user']['public_repos']} contributions={data['total']} "
          f"langs={len(data['langs'])}")
