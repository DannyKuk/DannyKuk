"""Project tiles (map sheets) for the DannyKuk profile README.

Usage: uv run --with numpy,contourpy,fonttools,brotli build.py <out_dir>
"""
import base64
import io
import sys
from pathlib import Path

import contourpy
import numpy as np
from fontTools.subset import Options, Subsetter
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

HERE = Path(__file__).parent
OUT = Path(sys.argv[1])
OUT.mkdir(parents=True, exist_ok=True)

THEMES = {
    "light": dict(paper="#E8EEE6", frame="#C9D3C6", contour="#CDAE94", index="#A57A5C",
                  water="#C3D8E3", shore="#4F86A8", ink="#16231C", muted="#3E4D45", mark="#B23A48"),
    "dark": dict(paper="#16211C", frame="#2A3832", contour="#2F4439", index="#4C6B5B",
                 water="#1B3442", shore="#4F8DB0", ink="#F2F6F2", muted="#C3D2C8", mark="#EE8A95"),
}

# ---------- fonts ----------
CHARS = "".join(chr(c) for c in range(32, 127)) + "°’–"


def font_instance(wdth, wght):
    f = TTFont(HERE / "fonts/Archivo.ttf")
    f = instantiateVariableFont(f, {"wdth": wdth, "wght": wght})
    return f


def font_b64(font):
    f = TTFont(io.BytesIO(_save(font)))
    opts = Options()
    opts.flavor = "woff2"
    opts.layout_features = ["kern", "liga"]
    s = Subsetter(opts)
    s.populate(text=CHARS)
    s.subset(f)
    f.flavor = "woff2"
    return base64.b64encode(_save(f)).decode()


def _save(f):
    b = io.BytesIO()
    f.save(b)
    return b.getvalue()


FONTS = {
    "T": font_instance(125, 760),  # titles, expanded
    "B": font_instance(100, 470),  # body
    "S": font_instance(100, 600),  # small strong
}
FONT_CSS = "".join(
    f"@font-face{{font-family:A{k};src:url(data:font/woff2;base64,{font_b64(f)}) format('woff2')}}"
    for k, f in FONTS.items()
)


def text_width(s, key, size):
    f = FONTS[key]
    cmap, hmtx, upm = f.getBestCmap(), f["hmtx"], f["head"].unitsPerEm
    return sum(hmtx[cmap.get(ord(c), cmap[32])][0] for c in s) * size / upm


def wrap(s, key, size, width):
    lines, cur = [], ""
    for w in s.split():
        t = (cur + " " + w).strip()
        if cur and text_width(t, key, size) > width:
            lines.append(cur)
            cur = w
        else:
            cur = t
    lines.append(cur)
    return lines


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ---------- terrain ----------
def terrain(w, h, seed, hills, lake=None, step=4):
    rng = np.random.default_rng(seed)
    xs, ys = np.arange(0, w + step, step), np.arange(0, h + step, step)
    X, Y = np.meshgrid(xs, ys)
    Z = np.zeros_like(X, dtype=float)
    for _ in range(hills["n"]):
        cx = rng.uniform(*hills["x"]) * w
        cy = rng.uniform(-0.1, 1.1) * h
        sx, sy = rng.uniform(*hills["r"]) * w, rng.uniform(*hills["r"]) * w * rng.uniform(0.5, 1.0)
        Z += rng.uniform(0.5, 1.0) * np.exp(-(((X - cx) / sx) ** 2 + ((Y - cy) / sy) ** 2))
    # gentle ridges for organic wobble
    for _ in range(6):
        k, ph = rng.uniform(0.004, 0.012), rng.uniform(0, 6.3)
        Z += 0.06 * np.sin(k * X + ph + 0.6 * np.sin(k * 1.7 * Y))
    if lake:
        cx, cy, rx, ry = lake
        dx, dy = (X - cx * w) / (rx * w), (Y - cy * h) / (ry * h)
        th = np.arctan2(dy, dx)
        a, b = rng.uniform(0, 6.3, 2)
        wobble = 1 + 0.28 * np.sin(2 * th + a) + 0.14 * np.sin(5 * th + b)  # bays and headlands
        Z -= 2.6 * np.exp(-((dx ** 2 + dy ** 2) * wobble) ** 1.3)
    return xs, ys, Z


def path_d(line, closed=False):
    p = np.round(line, 1)
    if len(p) < 3:
        return ""
    d = [f"M{p[0][0]:g} {p[0][1]:g}"]
    for i in range(1, len(p) - 1):
        mx, my = (p[i] + p[i + 1]) / 2
        d.append(f"Q{p[i][0]:g} {p[i][1]:g} {mx:.1f} {my:.1f}")
    d.append(f"L{p[-1][0]:g} {p[-1][1]:g}")
    if closed:
        d.append("Z")
    return "".join(d)


def contours(xs, ys, Z, n_levels, lake_level=None, animate=False, min_len=12):
    gen = contourpy.contour_generator(xs, ys, Z, line_type="Separate", fill_type="OuterOffset")
    lo = lake_level if lake_level is not None else Z.min()
    levels = np.linspace(lo, Z.max(), n_levels + 2)[1:-1]
    out = []
    for i, lv in enumerate(levels):
        cls = "x" if i % 5 == 4 else "c"
        for ln in gen.lines(lv):
            if len(ln) < min_len:
                continue
            d = path_d(ln)
            if not d:
                continue
            attrs = f'class="{cls}" d="{d}"'
            if animate:
                attrs += f' pathLength="1" style="animation-delay:{0.05 * i:.2f}s"'
            out.append(f"<path {attrs}/>")
    water = []
    if lake_level is not None:
        polys, offsets = gen.filled(Z.min() - 1, lake_level)
        for pts, offs in zip(polys, offsets):
            for a, b in zip(offs[:-1], offs[1:]):
                d = path_d(pts[a:b], closed=True)
                if d:
                    water.append(d)
    return out, water


def style(t, animate):
    css = FONT_CSS + f"""
.c{{fill:none;stroke:{t['contour']};stroke-width:1.1}}
.x{{fill:none;stroke:{t['index']};stroke-width:1.6}}
.w{{fill:{t['water']};stroke:{t['shore']};stroke-width:1.4}}
.t{{font-family:AT;fill:{t['ink']}}}
.b{{font-family:AB;fill:{t['ink']}}}
.m{{font-family:AB;fill:{t['muted']}}}
.s{{font-family:AS;fill:{t['muted']}}}
.t,.b,.m,.s{{stroke:{t['paper']};stroke-width:5px;stroke-linejoin:round;paint-order:stroke}}"""
    if animate:
        css += """
.c,.x{stroke-dasharray:1;animation:draw 2.2s cubic-bezier(.3,.6,.3,1) backwards}
.w{animation:fade 1.6s .9s ease-out backwards}
@keyframes draw{from{stroke-dashoffset:1}to{stroke-dashoffset:0}}
@keyframes fade{from{opacity:0}}
@media (prefers-reduced-motion:reduce){.c,.x,.w{animation:none}}"""
    return f"<style>{css}</style>"


def frame(w, h, t, ticks=True):
    """Map neatline with graticule ticks."""
    inset = 14
    parts = [f'<rect x="{inset}" y="{inset}" width="{w - 2 * inset}" height="{h - 2 * inset}" '
             f'fill="none" stroke="{t["frame"]}" stroke-width="1"/>']
    if ticks:
        for x in range(inset + 50, w - inset, 50):
            ln = 7 if (x - inset) % 200 == 0 else 4
            parts.append(f'<path d="M{x} {inset}v{ln}M{x} {h - inset}v-{ln}" stroke="{t["frame"]}"/>')
        for y in range(inset + 50, h - inset, 50):
            ln = 7 if (y - inset) % 200 == 0 else 4
            parts.append(f'<path d="M{inset} {y}h{ln}M{w - inset} {y}h-{ln}" stroke="{t["frame"]}"/>')
    return "".join(parts)


def fade_mask(mid, x1, y1, x2, y2, lo):
    return (f'<linearGradient id="g" x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}">'
            f'<stop offset="0" stop-color="#fff" stop-opacity="{lo}"/>'
            f'<stop offset="{mid}" stop-color="#fff" stop-opacity="1"/></linearGradient>'
            '<mask id="k"><rect width="100%" height="100%" fill="url(#g)"/></mask>')


def svg(w, h, t, body, defs, animate, title):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" '
            f'role="img" aria-label="{esc(title)}"><title>{esc(title)}</title>'
            f"<defs>{style(t, animate)}{defs}</defs>"
            f'<rect width="{w}" height="{h}" rx="12" fill="{t["paper"]}"/>{body}</svg>')


# ---------- header ----------
def header(theme):
    t = THEMES[theme]
    w, h = 1200, 360
    xs, ys, Z = terrain(w, h, seed=11, hills=dict(n=9, x=(0.58, 1.08), r=(0.08, 0.2)),
                        lake=(0.7, 0.8, 0.09, 0.22))
    lake_level = 0.45 * Z.min()
    lines, water = contours(xs, ys, Z, 22, lake_level=lake_level, animate=True)
    # survey marker on the highest point right of the text block
    sub = Z[:, xs > 0.6 * w]
    iy, ix = np.unravel_index(np.argmax(sub), sub.shape)
    mx, my = xs[xs > 0.6 * w][ix], ys[iy]
    mx, my = min(mx, w - 230), min(max(my, 70), h - 70)
    marker = (f'<g transform="translate({mx:.0f} {my:.0f})">'
              f'<path d="M0 -9L8 5H-8Z" fill="{t["paper"]}" stroke="{t["mark"]}" stroke-width="2"/>'
              f'<circle r="1.8" fill="{t["mark"]}" cy="0.5"/>'
              f'<text class="s" x="14" y="5" font-size="16">52.52° N, 13.40° E</text></g>')
    terrain_g = (f'<g mask="url(#k)">' + "".join(f'<path class="w" d="{d}"/>' for d in water)
                 + "".join(lines) + "</g>")
    text = (f'<text class="t" x="64" y="168" font-size="74" letter-spacing="-1">Danny Kukic</text>'
            f'<text class="b" x="66" y="214" font-size="25">Full-stack &amp; AI software engineer near Berlin</text>'
            f'<text class="m" x="66" y="252" font-size="19">Web platforms, Android apps and apps on language models,</text>'
            f'<text class="m" x="66" y="278" font-size="19">from the database to the screen.</text>')
    defs = fade_mask(0.62, 0, 0, 1, 0, 0.1)
    return svg(w, h, t, frame(w, h, t) + terrain_g + text + marker, defs, True,
               "Danny Kukic, full-stack and AI software engineer near Berlin")


# ---------- project tiles ----------
PROJECTS = [
    ("molecula", "Molecula",
     "A medicines chatbot that answers with real 3D molecular structures, citing FDA drug labels.",
     "Python, FastAPI, LangChain, Next.js", 3),
    ("ai-interview", "AI Interviewer",
     "Practise a job interview with a 3D interviewer who has read your CV, then get a scored report.",
     "Python, FastAPI, LangChain, three.js", 7),
    ("claude-statusline", "claude-statusline",
     "A compact status line for Claude Code: git state, rate limits, context usage and an energy estimate.",
     "Bash, PowerShell", 21),
    ("more", "More on my website",
     "EasyPointment, online booking for clinics. PillRemind, a medication alarm for Android. Two sites for dog businesses.",
     "Nuxt, FastAPI, Kotlin, Directus", 17),
]


LAKES = [(0.92, 0.88, 0.11, 0.24), None, (0.9, 0.08, 0.13, 0.22), (0.96, 0.5, 0.07, 0.3)]


def tile(theme, slug, name, desc, stack, seed, lake):
    t = THEMES[theme]
    w, h = 600, 300
    xs, ys, Z = terrain(w, h, seed=seed, hills=dict(n=5, x=(0.78, 1.3), r=(0.1, 0.26)),
                        lake=lake)
    lake_level = 0.45 * Z.min() if lake else None
    lines, water = contours(xs, ys, Z, 14, lake_level=lake_level)
    terrain_g = (f'<g mask="url(#k)">' + "".join(f'<path class="w" d="{d}"/>' for d in water)
                 + "".join(lines) + "</g>")
    size = 36 if text_width(name, "T", 36) < 520 else 30
    body = f'<text class="t" x="40" y="88" font-size="{size}" letter-spacing="-0.5">{esc(name)}</text>'
    for i, ln in enumerate(wrap(desc, "B", 22, 480)):
        body += f'<text class="b" x="41" y="{134 + i * 31}" font-size="22">{esc(ln)}</text>'
    body += f'<text class="s" x="41" y="{h - 38}" font-size="19">{esc(stack)}</text>'
    defs = fade_mask(1, 0.3, 0, 1, 0.25, 0)
    return svg(w, h, t, frame(w, h, t, ticks=False) + terrain_g + body, defs, False, f"{name}: {desc}")


if __name__ == "__main__":
    for th in THEMES:
        for (slug, name, desc, stack, seed), lake in zip(PROJECTS, LAKES):
            (OUT / f"{slug}-{th}.svg").write_text(tile(th, slug, name, desc, stack, seed, lake))
    for p in sorted(OUT.iterdir()):
        print(f"{p.stat().st_size // 1024:>4} KB  {p.name}")
