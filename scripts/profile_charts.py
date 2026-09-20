"""Dependency-free, theme-aware SVG charts for GitHub's script-free README."""
from html import escape
from math import pi

PALETTE = {"Swift": "ECA36D", "TypeScript": "5486B8", "JavaScript": "D5B45B",
           "PHP": "9485B8", "Go": "60A8AA", "Python": "83AC8E", "Vue": "78B6A3",
           "HTML": "C98976", "Ruby": "BD7E8D", "Other": "9AA6B4"}


def start(width, height, title, description):
    return [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
            f'<title id="title">{escape(title)}</title><desc id="desc">{escape(description)}</desc>',
            '<style>text{font-family:system-ui,-apple-system,sans-serif;fill:#334155}.muted{fill:#738196}.card{fill:#f6f8fa;stroke:#e8edf2}.track{fill:none;stroke:#e5eaf0}.bartrack{fill:#e5eaf0}@media(prefers-color-scheme:dark){text{fill:#e1e8f0}.muted{fill:#93a4b8}.card{fill:#161e29;stroke:#2b3645}.track{stroke:#2b3645}.bartrack{fill:#2b3645}}</style>']


def text(x, y, value, size=14, extra=""):
    return f'<text x="{x}" y="{y}" font-size="{size}" {extra}>{escape(str(value))}</text>'


def metrics(contributions, year, repos, stars, followers):
    items = [(f"CONTRIBUTIONS · {year}", contributions, "GitHub contribution calendar"),
             ("PUBLIC REPOSITORIES", repos, "gentpan + QuotaBar"),
             ("PROJECT STARS", stars, "Public non-fork repositories"),
             ("FOLLOWERS", followers, "GitHub community")]
    svg = start(1080, 124, "GitHub overview", "; ".join(f"{a}: {b:,}" for a,b,_ in items))
    for i, (label, value, subtitle) in enumerate(items):
        x = i * 274
        svg += [f'<rect class="card" x="{x+1}" y="1" width="256" height="122" rx="14"/>',
                text(x+20, 28, label, 12, 'class="muted" letter-spacing="0.7"'),
                text(x+20, 72, f"{value:,}", 34, 'font-weight="650"'),
                text(x+20, 102, subtitle, 11, 'class="muted"')]
    return "\n".join(svg + ['</svg>'])


def distribution(languages, time_bins):
    total = sum(languages.values())
    commit_total = sum(time_bins.values())
    svg = start(1080, 348, "Languages and commit rhythm",
                "Repository primary languages: " + ", ".join(f"{k} {v}" for k,v in languages.items()) +
                ". Commit rhythm in UTC: " + ", ".join(f"{k} {v}" for k,v in time_bins.items()))
    svg += ['<rect class="card" x="1" y="1" width="526" height="346" rx="16"/>',
            '<rect class="card" x="545" y="1" width="534" height="346" rx="16"/>',
            text(26, 38, "Languages", 21, 'font-weight="600"'),
            text(26, 62, "Primary language per public personal repository", 12, 'class="muted"'),
            text(570, 38, "Commit rhythm", 21, 'font-weight="600"'),
            text(570, 62, "Attributed public commits · UTC", 12, 'class="muted"')]
    radius = 78
    circumference = 2 * pi * radius
    svg += [f'<circle class="track" cx="130" cy="196" r="{radius}" stroke-width="25"/>']
    offset = 0
    rows = languages.most_common()
    if len(rows) > 8:
        rows = rows[:7] + [("Other", sum(v for _,v in rows[7:]))]
    for i, (language, count) in enumerate(rows):
        length = count / total * circumference if total else 0
        color = PALETTE.get(language, PALETTE['Other'])
        svg += [f'<circle cx="130" cy="196" r="{radius}" fill="none" stroke="#{color}" stroke-width="25" stroke-dasharray="{max(0,length-2):.4f} {circumference-max(0,length-2):.4f}" stroke-dashoffset="{-offset:.4f}" transform="rotate(-90 130 196)"><title>{escape(language)}: {count} repositories</title></circle>']
        offset += length
        y = 106 + i * 27
        svg += [f'<rect x="244" y="{y-10}" width="9" height="9" rx="3" fill="#{color}"/>',
                text(264, y, language, 14),
                text(496, y, f"{count} · {count/total*100:.1f}%" if total else "0", 13, 'text-anchor="end" class="muted"')]
    svg += [text(130, 196, total, 36, 'text-anchor="middle" font-weight="650"'),
            text(130, 220, "repositories", 13, 'text-anchor="middle" class="muted"')]
    colors = ['9CBFCB', '83B0C3', '5486B8', '8D85B3']
    for i, (name, count) in enumerate(time_bins.items()):
        y = 110 + i * 55
        label = name.split(' ', 1)[-1]
        percent = count / commit_total * 100 if commit_total else 0
        svg += [text(570, y, label, 14),
                text(1051, y, f"{count:,} · {percent:.1f}%", 13, 'text-anchor="end" class="muted"'),
                f'<rect class="bartrack" x="570" y="{y+12}" width="481" height="10" rx="5"/>',
                f'<rect x="570" y="{y+12}" width="{481*percent/100:.3f}" height="10" rx="5" fill="#{colors[i]}"/>']
    svg += [text(26, 327, "Excludes forks and repositories without a language", 11, 'class="muted"'),
            text(570, 327, "06–12 / 12–18 / 18–24 / 00–06 · default branches", 11, 'class="muted"')]
    return "\n".join(svg + ['</svg>'])
