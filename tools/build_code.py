"""Header: typed code that renders a contour map (the terminal tiles are an unused variant).

Usage: uv run --with numpy,contourpy,fonttools,brotli build_code.py <out_dir>
"""
import base64
import io
import re

import numpy as np
from fontTools.subset import Options, Subsetter
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

import build as B
from build import THEMES, OUT, esc, frame, fade_mask, terrain, contours, wrap, text_width

# ---------- mono font ----------
MONO_CHARS = "".join(chr(c) for c in range(32, 127)) + "°↑↓"


def mono_b64(wght):
    f = instantiateVariableFont(TTFont(B.HERE / "fonts/JetBrainsMono.ttf"), {"wght": wght})
    b = io.BytesIO(); f.save(b)
    f = TTFont(io.BytesIO(b.getvalue()))
    o = Options(); o.flavor = "woff2"; o.layout_features = []  # no ligatures, plain code
    s = Subsetter(o); s.populate(text=MONO_CHARS); s.subset(f)
    f.flavor = "woff2"; b = io.BytesIO(); f.save(b)
    return base64.b64encode(b.getvalue()).decode()


MONO_CSS = (f"@font-face{{font-family:MR;src:url(data:font/woff2;base64,{mono_b64(430)}) format('woff2')}}"
            f"@font-face{{font-family:MB;src:url(data:font/woff2;base64,{mono_b64(650)}) format('woff2')}}")
MONO_ADV = 0.6  # JetBrains Mono advance width in em

# syntax colours borrowed from the map legend
SYN = {
    "light": dict(n="#16231C", s="#2F6F96", d="#B23A48", c="#6B7A71", f="#9A6B4C", p="#4C5C53",
                  term="#1C2A23", tink="#E5ECE6", tmut="#9DB1A6", prompt="#D9A47F", teal="#5CC8BE",
                  sep="#5B6B62", yel="#E3C567"),
    "dark": dict(n="#F2F6F2", s="#7DB9DB", d="#EE8A95", c="#8FA398", f="#D9A47F", p="#B5C4BA",
                 term="#0E1612", tink="#E5ECE6", tmut="#9DB1A6", prompt="#D9A47F", teal="#5CC8BE",
                 sep="#5B6B62", yel="#E3C567"),
}


def style(t, th, anim):
    y = SYN[th]
    css = B.FONT_CSS + MONO_CSS + f"""
.c{{fill:none;stroke:{t['contour']};stroke-width:1.1}}
.x{{fill:none;stroke:{t['index']};stroke-width:1.6}}
.w{{fill:{t['water']};stroke:{t['shore']};stroke-width:1.4}}
.t{{font-family:AT;fill:{t['ink']}}}
.b{{font-family:AB;fill:{t['ink']}}}
.ms{{font-family:AS;fill:{t['muted']}}}
.t,.b,.ms{{stroke:{t['paper']};stroke-width:5px;stroke-linejoin:round;paint-order:stroke}}
.code{{font-family:MR}}
.code .n{{fill:{y['n']}}}.code .s{{fill:{y['s']}}}.code .d{{fill:{y['d']}}}
.code .c{{fill:{y['c']};stroke:none}}.code .f{{fill:{y['f']};font-family:MB}}.code .p{{fill:{y['p']}}}
.ln{{font-family:MR;fill:{t['muted']};opacity:.55}}
.term{{font-family:MR;fill:{y['tink']}}}
.term .pr{{fill:{y['prompt']};font-family:MB}}.term .o{{fill:{y['tmut']}}}
.term .tl{{fill:{y['teal']}}}.term .sp{{fill:{y['sep']}}}.term .yl{{fill:{y['yel']}}}.term .bd{{font-family:MB}}
.cover{{transform-box:fill-box;transform-origin:right center;transform:scaleX(0)}}
.cur{{fill:{y['f']}}}
@keyframes draw{{from{{stroke-dashoffset:1}}to{{stroke-dashoffset:0}}}}
@keyframes fade{{from{{opacity:0}}}}
@keyframes type{{from{{transform:scaleX(1)}}to{{transform:scaleX(0)}}}}
@keyframes blink{{50%{{opacity:0}}}}
.cur{{animation:blink 1.1s step-end infinite}}
@media (prefers-reduced-motion:reduce){{.c,.x,.w,.cover,.cur{{animation:none}}}}"""
    if anim:
        css += """
.c,.x{stroke-dasharray:1;animation:draw 2.2s cubic-bezier(.3,.6,.3,1) backwards}
.w{animation:fade 1.4s ease-out backwards}"""
    return f"<style>{css}</style>"


def svg(w, h, t, th, body, defs, title, anim=False):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" '
            f'role="img" aria-label="{esc(title)}"><title>{esc(title)}</title>'
            f"<defs>{style(t, th, anim)}{defs}</defs>"
            f'<rect width="{w}" height="{h}" rx="12" fill="{t["paper"]}"/>{body}</svg>')


def tokens_svg(tokens):
    return "".join(f'<tspan class="{c}">{esc(s)}</tspan>' for s, c in tokens)


def map_layer(w, h, seed, hills, lake, n, delay0, anim=True):
    xs, ys, Z = terrain(w, h, seed=seed, hills=hills, lake=lake)
    lake_level = 0.45 * Z.min() if lake else None
    lines, water = contours(xs, ys, Z, n, lake_level=lake_level, animate=anim)
    if anim:  # shift every contour's delay so the map draws after the code is typed
        lines = [re.sub(r"animation-delay:([\d.]+)s", lambda m: f"animation-delay:{float(m[1]) + delay0:.2f}s", l)
                 for l in lines]
    wstyle = f' style="animation-delay:{delay0 + 1.0:.2f}s"' if anim else ""
    return (xs, ys, Z, "".join(f'<path class="w" d="{d}"{wstyle}/>' for d in water) + "".join(lines))


# ---------- header ----------
CODE = [
    [("role", "n"), ("  = ", "p"), ('"Full-stack & AI software engineer"', "s")],
    [("based", "n"), (" = ", "p"), ('"near Berlin"', "s"), ("  # 52.52° N, 13.40° E", "c")],
    [("since", "n"), (" = ", "p"), ("2023", "d"), ("  # maps first, now LLM apps", "c")],
    [("ships", "n"), (" = ", "p"), ("[", "p"), ('"web"', "s"), (", ", "p"), ('"android"', "s"),
     (", ", "p"), ('"ai"', "s"), ("]", "p")],
    [],
    [("render", "f"), ("(", "p"), ("terrain", "f"), ("(", "p"), ("seed", "n"), ("=", "p"), ("11", "d"), ("))", "p")],
]


def header(th):
    t = THEMES[th]
    w, h = 1200, 360
    size, lh, x0, y0 = 17, 27, 104, 168
    cw = size * MONO_ADV
    per_line, gap = 0.42, 0.12
    t_end = len([l for l in CODE if l]) * (per_line + gap) + 0.3
    xs, ys, Z, terr = map_layer(w, h, 11, dict(n=9, x=(0.62, 1.08), r=(0.08, 0.2)), (0.72, 0.82, 0.08, 0.2),
                                20, t_end)
    sub = Z[:, xs > 0.66 * w]
    iy, ix = np.unravel_index(np.argmax(sub), sub.shape)
    mx, my = xs[xs > 0.66 * w][ix], ys[iy]
    mx, my = min(mx, w - 60), min(max(my, 60), h - 60)
    marker = (f'<g transform="translate({mx:.0f} {my:.0f})" style="animation:fade .6s {t_end + 1.6:.2f}s backwards">'
              f'<path d="M0 -9L8 5H-8Z" fill="{t["paper"]}" stroke="{t["mark"]}" stroke-width="2"/>'
              f'<circle r="1.8" fill="{t["mark"]}" cy="0.5"/></g>')
    body = f'<g mask="url(#k)">{terr}</g>' + marker
    body += f'<text class="t" x="64" y="118" font-size="66" letter-spacing="-1">Danny Kukic</text>'
    k, last = 0, None
    for i, toks in enumerate(CODE):
        y = y0 + i * lh
        body += f'<text class="ln" x="{x0 - 34}" y="{y}" font-size="{size - 2}">{i + 1}</text>'
        if not toks:
            continue
        n = sum(len(s) for s, _ in toks)
        body += f'<text class="code" x="{x0}" y="{y}" font-size="{size}" xml:space="preserve">{tokens_svg(toks)}</text>'
        d = 0.25 + k * (per_line + gap)
        body += (f'<rect class="cover" x="{x0 - 1}" y="{y - size}" width="{n * cw + 4:.0f}" height="{lh - 2}" '
                 f'fill="{t["paper"]}" style="animation:type {per_line}s steps({n}, end) {d:.2f}s backwards"/>')
        k += 1
        last = (x0 + n * cw + 3, y)
    body += f'<rect class="cur" x="{last[0]:.0f}" y="{last[1] - size + 2}" width="{cw:.1f}" height="{size + 2}"/>'
    defs = fade_mask(0.7, 0.45, 0, 1, 0, 0)
    return svg(w, h, t, th, frame(w, h, t) + body, defs,
               "Danny Kukic, full-stack and AI software engineer near Berlin", anim=True)


# ---------- tiles ----------
TILES = [
    ("molecula", "Molecula", "A medicines chatbot that answers with real 3D molecular structures.", 3,
     (0.92, 0.1, 0.1, 0.25),
     [[("$ ", "pr"), ("molecula ask ", "bd"), ('"How does imatinib fight leukemia?"', "")],
      [("  It blocks BCR-ABL, the kinase driving the cancer.", "o")],
      [("  [3D: imatinib in its binding pocket]  [FDA label]", "tl")]]),
    ("ai-interview", "AI Interviewer", "Practise a job interview with a 3D interviewer who has read your CV.", 7,
     None,
     [[("$ ", "pr"), ("interview ", "bd"), ("--company Guugle --cv cv.pdf", "")],
      [("  Q4  How did you measure that 40% latency win?", "o")],
      [("  report  ", "o"), ("7.5/10", "yl"), ("  strongest: system design", "o")]]),
    ("claude-statusline", "claude-statusline", "A compact status line for Claude Code, in bash and PowerShell.", 21,
     (0.9, 0.08, 0.13, 0.22),
     [[("Opus 5.5", "bd"), (" | ", "sp"), ("profile", ""), (" | ", "sp"), ("main* ↑2", ""), (" | ", "sp"),
       ("2h14m ", "o"), ("37%", "tl"), (" | ", "sp"), ("ctx ", "o"), ("64%", "yl")],
      [("Personal", ""), (" | ", "sp"), ("~12 Wh est.", "o")],
      [("> ", "pr")]]),
    ("more", "More on my website", "EasyPointment, PillRemind and two sites for dog businesses.", 17,
     (0.96, 0.5, 0.07, 0.3),
     [[("$ ", "pr"), ("ls ", "bd"), ("dkwebsite.de/projects", "")],
      [("  easypointment/   pillremind/", "tl")],
      [("  toivoa-tassuille/   kennel-unlock/", "tl")]]),
]


def tile(th, slug, name, desc, seed, lake, term):
    t = THEMES[th]
    w, h = 600, 330
    xs, ys, Z = terrain(w, h, seed=seed, hills=dict(n=5, x=(0.8, 1.3), r=(0.1, 0.24)), lake=lake)
    lines, water = contours(xs, ys, Z, 14, lake_level=0.45 * Z.min() if lake else None)
    body = (f'<g mask="url(#k)">' + "".join(f'<path class="w" d="{d}"/>' for d in water)
            + "".join(lines) + "</g>")
    body += f'<text class="t" x="38" y="76" font-size="34" letter-spacing="-0.5">{esc(name)}</text>'
    for i, ln in enumerate(wrap(desc, "B", 20, 500)):
        body += f'<text class="b" x="39" y="{112 + i * 27}" font-size="20">{esc(ln)}</text>'
    bx, by, bw, bh = 26, 168, w - 52, 136
    y = SYN[th]
    body += f'<rect x="{bx}" y="{by}" width="{bw}" height="{bh}" rx="8" fill="{y["term"]}"/>'
    fs = 16
    for i, toks in enumerate(term):
        body += (f'<text class="term" x="{bx + 18}" y="{by + 34 + i * 34}" font-size="{fs}" xml:space="preserve">'
                 + tokens_svg(toks) + "</text>")
    last = term[-1]
    lx = bx + 18 + sum(len(s) for s, _ in last) * fs * MONO_ADV
    body += f'<rect class="cur" x="{lx:.0f}" y="{by + 34 + (len(term) - 1) * 34 - fs + 2}" width="{fs * MONO_ADV:.1f}" height="{fs + 3}"/>'
    defs = fade_mask(1, 0.3, 0, 1, 0.25, 0)
    return svg(w, h, t, th, frame(w, h, t, ticks=False) + body, defs, f"{name}: {desc}")


if __name__ == "__main__":
    for th in THEMES:
        (OUT / f"header-{th}.svg").write_text(header(th))
    for p in sorted(OUT.iterdir()):
        print(f"{p.stat().st_size // 1024:>4} KB  {p.name}")
