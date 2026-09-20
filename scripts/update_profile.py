"""Build public GitHub metrics and optional WakaTime metrics without a PAT.

Run locally with an authenticated gh CLI, or set GH_TOKEN in GitHub Actions.
Only explicit public repository endpoints are queried. No private data is used.
"""

import base64
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import html
import json
import os
from pathlib import Path
import subprocess
import time
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
OWNER = "gentpan"
ORG = "QuotaBar"
NOW = datetime.now(timezone.utc)


def github(path, payload=None):
    token = os.environ.get("GH_TOKEN")
    for attempt in range(3):
        try:
            if token:
                request = Request(
                    "https://api.github.com/" + path,
                    data=json.dumps(payload).encode() if payload else None,
                    headers={"Authorization": "Bearer " + token,
                             "Accept": "application/vnd.github+json",
                             "User-Agent": "gentpan-profile",
                             "Content-Type": "application/json"},
                )
                with urlopen(request, timeout=60) as response:
                    result = json.load(response)
            else:
                command = ["gh", "api", path]
                if payload:
                    command += ["--input", "-"]
                result = json.loads(subprocess.run(
                    command, input=json.dumps(payload) if payload else None,
                    text=True, capture_output=True, check=True,
                ).stdout)
            if isinstance(result, dict) and result.get("errors"):
                raise RuntimeError("GitHub GraphQL returned errors")
            return result
        except (HTTPError, URLError, subprocess.CalledProcessError):
            if attempt == 2:
                raise RuntimeError("GitHub request failed: " + path) from None
            time.sleep(2 ** attempt)


def repositories(path):
    result = []
    page = 1
    while True:
        batch = github(f"{path}?per_page=100&page={page}")
        result.extend(r for r in batch if not r["private"] and not r["fork"])
        if len(batch) < 100:
            return result
        page += 1


def history(repo, author_id):
    query = """query($owner:String!,$name:String!,$author:ID!,$cursor:String) {
      repository(owner:$owner,name:$name) {
        defaultBranchRef { target { ... on Commit {
          history(first:100,after:$cursor,author:{id:$author}) {
            pageInfo {hasNextPage endCursor}
            nodes {oid committedDate additions deletions}
          }
        } } }
      }
    }"""
    cursor = None
    rows = []
    while True:
        result = github("graphql", {"query": query, "variables": {
            "owner": repo["owner"]["login"], "name": repo["name"],
            "author": author_id, "cursor": cursor,
        }})["data"]["repository"]
        if not result:
            raise RuntimeError("Repository disappeared during update")
        branch = result["defaultBranchRef"]
        if not branch:
            break
        data = branch["target"]["history"]
        rows.extend(data["nodes"])
        if not data["pageInfo"]["hasNextPage"]:
            break
        cursor = data["pageInfo"]["endCursor"]
    return repo, rows


def bar(value, total):
    percentage = value / total * 100 if total else 0
    blocks = round(percentage / 4)
    return "█" * blocks + "░" * (25 - blocks), percentage


def code_table(rows, total, unit):
    output = ["```text"]
    for name, count in rows:
        blocks, percent = bar(count, total)
        output.append(f"{name:<20} {count:>7,} {unit:<7} {blocks}  {percent:6.2f} %")
    return "\n".join(output + ["```"])


def badge(label, message, color="2874C6"):
    def encode(value):
        return quote(str(value).replace("-", "--").replace("_", "__"), safe="")
    return f"![{label}: {message}](https://img.shields.io/badge/{encode(label)}-{encode(message)}-{color}?style=flat-square)"


def waka():
    key = os.environ.get("WAKATIME_API_KEY")
    if not key:
        return badge("Code Time", "Not connected", "667085"), (
            "```text\n💬 Programming Languages\nWakaTime 未连接，暂无编码时长数据。\n\n"
            "🔥 Editors\nWakaTime 未连接，暂无编辑器使用数据。\n```"
        )

    def fetch(path):
        request = Request("https://wakatime.com/api/v1/users/current/" + path,
                          headers={"Authorization": "Basic " + base64.b64encode(
                              (key + ":").encode()).decode()})
        with urlopen(request, timeout=60) as response:
            return json.load(response)["data"]

    try:
        stats = fetch("stats/last_7_days")
        total = fetch("all_time_since_today")
        output = ["```text"]
        for title, field in [("💬 Programming Languages", "languages"), ("🔥 Editors", "editors")]:
            output.append(title)
            rows = stats.get(field, [])
            if not rows:
                output.append("No Activity Tracked This Week")
            for row in rows[:8]:
                blocks, _ = bar(row["percent"], 100)
                output.append(f'{row["name"]:<20} {row["text"]:<19} {blocks}  {row["percent"]:6.2f} %')
            output.append("")
        output.append("```")
        return badge("Code Time", total.get("text", "Calculating")), "\n".join(output)
    except (HTTPError, URLError, KeyError):
        return badge("Code Time", "Unavailable", "667085"), (
            "> WakaTime 数据暂时不可用；GitHub 统计仍正常更新。"
        )


def timeline(commits):
    """Quarterly additions/deletions grouped by the repository's primary language."""
    values = defaultdict(lambda: defaultdict(lambda: [0, 0]))
    for row, language in commits.values():
        date = datetime.fromisoformat(row["committedDate"].replace("Z", "+00:00"))
        quarter = f"{date.year} Q{(date.month - 1) // 3 + 1}"
        values[quarter][language][0] += row["additions"]
        values[quarter][language][1] += row["deletions"]
    quarters = sorted(values)
    languages = sorted({language for data in values.values() for language in data})
    palette = {"Swift": "F28C45", "TypeScript": "3B82D0", "JavaScript": "D6AE28",
               "PHP": "8B79BF", "Go": "2FA6AD", "Python": "57A56B", "Vue": "42B88C",
               "HTML": "D87760", "Ruby": "C95D6C", "Other": "8993A3"}
    w, h, baseline, extent = 1080, 520, 244, 142
    left, right = 100, 830
    maximum = max([sum(pair[i] for pair in data.values())
                   for data in values.values() for i in (0, 1)] or [1]) or 1
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" role="img" aria-labelledby="title desc">',
           '<title id="title">Code Timeline · gentpan</title>',
           '<desc id="desc">Public default-branch commits attributed to gentpan. Additions above zero, deletions below zero; grouped by repository primary language.</desc>',
           '<style>text{font-family:system-ui,-apple-system,sans-serif;fill:#334155}.muted{fill:#64748b}.grid{stroke:#e4e9f0}.bg{fill:#f8fafc}@media(prefers-color-scheme:dark){text{fill:#e2e8f0}.muted{fill:#94a3b8}.grid{stroke:#303b4c}.bg{fill:#161e2b}}</style>',
           '<rect class="bg" width="1080" height="520" rx="20"/>',
           '<text x="32" y="42" font-size="22" font-weight="650">Code Timeline</text>',
           '<text class="muted" x="32" y="68" font-size="13">Lines added / deleted · by repository language</text>']
    for fraction in (-1, -0.5, 0, 0.5, 1):
        y = baseline - fraction * extent
        number = round(maximum * fraction)
        label = f"{number / 1_000_000:.1f}M" if abs(number) >= 1_000_000 else f"{number / 1000:.1f}k" if abs(number) >= 1000 else str(number)
        svg += [f'<path class="grid" d="M{left} {y}H{right}"/>',
                f'<text class="muted" x="88" y="{y+4}" text-anchor="end" font-size="12">{label}</text>']
    step = (right - left) / max(1, len(quarters))
    width = min(48, step * 0.55)
    for index, quarter in enumerate(quarters):
        x = left + step * (index + 0.5)
        up = down = 0
        for language in languages:
            added, deleted = values[quarter].get(language, [0, 0])
            for amount, offset, negative in [(added, up, False), (deleted, down, True)]:
                height = amount / maximum * extent
                y = baseline + offset if negative else baseline - offset - height
                svg.append(f'<rect x="{x-width/2:.2f}" y="{y:.2f}" width="{width:.2f}" height="{height:.2f}" fill="#{palette.get(language, "8993A3")}"><title>{html.escape(quarter + " · " + language)}: {"-" if negative else "+"}{amount:,} lines</title></rect>')
            up += added / maximum * extent
            down += deleted / maximum * extent
        svg.append(f'<text class="muted" x="{x:.2f}" y="416" text-anchor="middle" font-size="12">{quarter}</text>')
    for i, language in enumerate(languages):
        y = 112 + i * 25
        svg += [f'<rect x="874" y="{y-11}" width="11" height="11" rx="3" fill="#{palette.get(language, "8993A3")}"/>',
                f'<text x="896" y="{y}" font-size="13">{html.escape(language)}</text>']
    if not commits:
        svg.append('<text x="440" y="220" text-anchor="middle">No attributed public commits found</text>')
    svg += [f'<text class="muted" x="32" y="465" font-size="12">{len(commits):,} attributed commits · full available default-branch history · SHA deduplicated</text>',
            '<text class="muted" x="32" y="488" font-size="12">Includes generated / imported lines. Repository language is not a per-file language analysis.</text>', '</svg>']
    return "\n".join(svg)


def main():
    profile = github("users/" + OWNER)
    own = repositories("users/" + OWNER + "/repos")
    org = repositories("orgs/" + ORG + "/repos")
    all_repos = own + org
    year_start = f"{NOW.year}-01-01T00:00:00Z"
    query = """query($login:String!,$from:DateTime!) { user(login:$login) {
      id contributionsCollection(from:$from) { contributionCalendar { totalContributions } }
    } }"""
    user = github("graphql", {"query": query, "variables": {"login": OWNER, "from": year_start}})["data"]["user"]
    commits = {}
    with ThreadPoolExecutor(max_workers=4) as pool:
        for repo, rows in pool.map(lambda r: history(r, user["id"]), all_repos):
            for row in rows:
                commits.setdefault(row["oid"], (row, repo["language"] or "Other"))
    time_bins = Counter({"🌞 Morning": 0, "🌆 Daytime": 0, "🌃 Evening": 0, "🌙 Night": 0})
    for row, _ in commits.values():
        hour = datetime.fromisoformat(row["committedDate"].replace("Z", "+00:00")).hour
        name = "🌞 Morning" if 6 <= hour < 12 else "🌆 Daytime" if 12 <= hour < 18 else "🌃 Evening" if 18 <= hour < 24 else "🌙 Night"
        time_bins[name] += 1
    languages = Counter(r["language"] for r in own if r["language"])
    code_badge, weekly = waka()
    stars = sum(r["stargazers_count"] for r in all_repos)
    storage_mb = sum(r["size"] for r in own) / 1024
    contributions = user["contributionsCollection"]["contributionCalendar"]["totalContributions"]
    headline = "I'm an Early 🐤" if time_bins["🌞 Morning"] + time_bins["🌆 Daytime"] >= time_bins["🌃 Evening"] + time_bins["🌙 Night"] else "I'm a Night 🦉"
    if not commits:
        headline = "Commit activity"
    top_language = languages.most_common(1)[0][0] if languages else "—"
    section = f"""{code_badge}
{badge("Profile Views", "Not tracked", "667085")}
{badge("Public project stars", f"{stars:,}")}

### 🐱 My GitHub Data

> 📦 **{storage_mb:,.1f} MB** · 个人公开仓库大小合计（GitHub API）
>
> 🏆 **{contributions:,} Contributions in {NOW.year}** · GitHub 贡献日历
>
> 📜 **{profile['public_repos']} Public Repositories** · gentpan
>
> 🧩 **{len(org)} Public Repositories** · QuotaBar
>
> ⭐ **{stars:,} Stars** · 个人与 QuotaBar 公开非 Fork 仓库合计
>
> 👥 **{profile['followers']} Followers**

### {headline}

{code_table(time_bins.items(), len(commits), 'commits')}

<sub>按 UTC 划分：Morning 06–12、Daytime 12–18、Evening 18–24、Night 00–06。统计公开仓库默认分支中 GitHub 归属到 gentpan 的提交。</sub>

### 📊 This Week I Spent My Time On

{weekly}

### I Mostly Code in {top_language}

{code_table(languages.most_common(), sum(languages.values()), 'repos')}

<sub>按个人公开非 Fork 仓库的主要语言计数；排除未识别语言的仓库。不是编码时长或熟练度。</sub>

### Timeline

![按季度与仓库主要语言统计的代码增删](assets/code-timeline.svg?v={NOW.strftime('%Y%m%d%H%M')})

<details>
<summary>数据口径与连接状态</summary>

- GitHub 数据每天自动更新；项目 Star 徽章由 Shields.io 缓存刷新。
- 提交与 Timeline 覆盖 gentpan 和 QuotaBar 的公开非 Fork 仓库，只计默认分支中 GitHub 归属到 gentpan 的提交，按 SHA 去重；未关联账号的提交不计入。
- Timeline 上方为新增行、下方为删除行，按仓库当前主要语言分组，包含导入和生成文件，不代表净代码量或工作时长。
- 私有仓库数量、账号存储额度和访问次数不从公开数据猜测；Profile Views 当前未追踪。
- WakaTime 连接后显示真实 Code Time、最近 7 天语言与编辑器统计。未连接时保留状态说明。

</details>

<sub>Last updated on {NOW.strftime('%Y-%m-%d %H:%M UTC')}</sub>"""
    readme_path = ROOT / "README.md"
    readme = readme_path.read_text()
    start, end = "<!--START_SECTION:waka-->", "<!--END_SECTION:waka-->"
    if readme.count(start) != 1 or readme.count(end) != 1:
        raise RuntimeError("Expected exactly one stats section")
    before, rest = readme.split(start)
    _, after = rest.split(end)
    chart = timeline(commits)
    (ROOT / "assets" / "code-timeline.svg").write_text(chart)
    readme_path.write_text(before + start + "\n" + section + "\n" + end + after)
    print(f"Updated profile: {len(all_repos)} public repositories, {len(commits)} attributed commits, {contributions} annual contributions.")


if __name__ == "__main__":
    main()
