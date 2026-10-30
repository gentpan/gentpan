"""Dependency-free, theme-aware SVG charts for GitHub's script-free README."""
from html import escape
PALETTE = {"Swift": "ECA36D", "TypeScript": "5486B8", "JavaScript": "D5B45B",
           "PHP": "9485B8", "Go": "60A8AA", "Python": "83AC8E", "Vue": "78B6A3",
           "HTML": "C98976", "Ruby": "BD7E8D", "Other": "9AA6B4"}


def start(width, height, title, description):
    return [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
            f'<title id="title">{escape(title)}</title><desc id="desc">{escape(description)}</desc>',
            '<style>text{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;fill:#334155}.muted{fill:#738196}.rule{fill:none;stroke:#d8dee4}.bartrack{fill:#e5eaf0}@media(prefers-color-scheme:dark){text{fill:#e1e8f0}.muted{fill:#93a4b8}.rule{stroke:#30363d}.bartrack{fill:#2b3645}}</style>']


def text(x, y, value, size=14, extra=""):
    return f'<text x="{x}" y="{y}" font-size="{size}" {extra}>{escape(str(value))}</text>'


def metrics(contributions, year, repos, stars, followers):
    items = [(f"CONTRIBUTIONS · {year}", contributions, "GitHub contribution calendar"),
             ("PUBLIC REPOSITORIES", repos, "Personal + owned organizations"),
             ("PROJECT STARS", stars, "Personal + owned organizations"),
             ("FOLLOWERS", followers, "GitHub community")]
    svg = start(1080, 156, "GitHub overview", "; ".join(f"{a}: {b:,}" for a,b,_ in items))
    svg += ['<path class="rule" d="M0 1H1080M0 155H1080M540 48V134"/>',
            text(0, 30, f"DEVELOPMENT / {year}", 12, 'font-weight="700" letter-spacing="2"')]
    for i, (label, value, subtitle) in enumerate(items):
        x = (i // 2) * 540
        y = 72 + (i % 2) * 44
        svg += [text(x, y, label, 12, 'class="muted"'),
                text(x+510, y, f"{value:,}", 17, 'text-anchor="end" font-weight="700"')]
    svg += [text(0, 145, "PUBLIC DATA · PERSONAL + OWNED ORGANIZATIONS", 10, 'class="muted" letter-spacing="1"'),
            text(1080, 145, "GITHUB CONTRIBUTION CALENDAR", 10, 'text-anchor="end" class="muted" letter-spacing="1"')]
    return "\n".join(svg + ['</svg>'])


def distribution(languages, time_bins):
    total = sum(languages.values())
    commit_total = sum(time_bins.values())
    svg = start(1080, 306, "Languages and commit rhythm",
                "Repository primary languages: " + ", ".join(f"{k} {v}" for k,v in languages.items()) +
                ". Commit rhythm in UTC: " + ", ".join(f"{k} {v}" for k,v in time_bins.items()))
    svg += ['<path class="rule" d="M0 1H1080M0 305H1080M540 22V282"/>',
            text(0, 34, "LANGUAGES", 13, 'font-weight="700" letter-spacing="2"'),
            text(0, 56, "PRIMARY LANGUAGE / PUBLIC PERSONAL REPOSITORIES", 10, 'class="muted"'),
            text(570, 34, "COMMIT RHYTHM / UTC", 13, 'font-weight="700" letter-spacing="2"'),
            text(570, 56, "ATTRIBUTED PUBLIC COMMITS", 10, 'class="muted"')]
    rows = languages.most_common()
    if len(rows) > 8:
        rows = rows[:7] + [("Other", sum(v for _,v in rows[7:]))]
    for i, (language, count) in enumerate(rows):
        y = 88 + i * 27
        percent = count / total * 100 if total else 0
        color = PALETTE.get(language, PALETTE['Other'])
        svg += [f'<rect x="0" y="{y-9}" width="8" height="8" fill="#{color}"/>',
                text(20, y, language, 12),
                text(282, y, f"{count:>2}", 12, 'text-anchor="end" class="muted"'),
                f'<rect class="bartrack" x="310" y="{y-7}" width="140" height="6"/>',
                f'<rect x="310" y="{y-7}" width="{140*percent/100:.3f}" height="6" fill="#{color}"/>',
                text(510, y, f"{percent:>4.1f}%", 11, 'text-anchor="end" class="muted"')]
    colors = ['9CBFCB', '83B0C3', '5486B8', '8D85B3']
    for i, (name, count) in enumerate(time_bins.items()):
        y = 90 + i * 48
        label = name.split(' ', 1)[-1].upper()
        percent = count / commit_total * 100 if commit_total else 0
        svg += [text(570, y, label, 12),
                text(1080, y, f"{count:,} / {percent:.1f}%", 12, 'text-anchor="end" class="muted"'),
                f'<rect class="bartrack" x="570" y="{y+11}" width="510" height="6"/>',
                f'<rect x="570" y="{y+11}" width="{510*percent/100:.3f}" height="6" fill="#{colors[i]}"/>']
    svg += [text(0, 292, "EXCLUDES FORKS AND REPOSITORIES WITHOUT A LANGUAGE", 10, 'class="muted"'),
            text(570, 292, "06–12 / 12–18 / 18–24 / 00–06 · DEFAULT BRANCHES", 10, 'class="muted"')]
    return "\n".join(svg + ['</svg>'])
