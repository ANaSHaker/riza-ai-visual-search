"""Generates render.json (custom `html` images for the kit renderer).

Run:  python build_render.py && node D:/shaker-github/_kit/render.mjs render.json
"""

import json
import pathlib

GOLD, BEIGE, SKY, MINT = "#C9A15A", "#EAD7B4", "#7DD3FC", "#A7F3D0"

CSS = f"""
.card2{{background:#ffffff0d;border:1px solid #ffffff1f;border-radius:22px;backdrop-filter:blur(6px)}}
.mono{{font-family:ui-monospace,'Cascadia Code',Consolas,monospace}}
.lbl{{position:absolute;top:-30px;left:-2px;font-size:15px;font-weight:700;padding:3px 10px;border-radius:8px;background:{GOLD};color:#1a1306;white-space:nowrap}}
.bx{{position:absolute;border:2.5px dashed {GOLD};border-radius:12px}}
.arrow{{font-size:40px;color:{GOLD};opacity:.9}}
.tile{{border-radius:14px;background:linear-gradient(160deg,#ffffff22,#ffffff08);border:1px solid #ffffff22;position:relative;height:92px}}
.tile b{{position:absolute;right:8px;bottom:8px;font-size:14px;padding:2px 8px;border-radius:99px;background:#0009;color:{BEIGE}}}
.node{{border-radius:20px;padding:22px 24px;background:#ffffff0b;border:1px solid #ffffff22}}
.node h3{{font-size:28px;font-weight:800;margin-bottom:10px}}
.node li{{font-size:20px;opacity:.86;margin:6px 0 6px 18px;line-height:1.35}}
.tag{{display:inline-block;font-size:14px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;padding:4px 10px;border-radius:8px;margin-bottom:12px}}
.edge{{font-size:16px;opacity:.8;text-align:center;line-height:1.3}}
.step{{flex:1;border-radius:20px;padding:24px 20px;background:#ffffff0b;border:1px solid #ffffff22;display:flex;flex-direction:column;gap:12px;position:relative}}
.step .n{{width:44px;height:44px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-weight:800;font-size:22px;background:{GOLD};color:#1a1306}}
.step h4{{font-size:24px;font-weight:800}}
.step p{{font-size:19px;opacity:.85;line-height:1.4}}
.step code{{white-space:nowrap;font-family:ui-monospace,Consolas,monospace;font-size:15px;color:{BEIGE};background:#ffffff12;padding:1px 6px;border-radius:6px}}
"""

PHOTO = f"""
<div style="position:relative;width:180px;height:250px;border-radius:18px;background:linear-gradient(170deg,#3a2f22,#1c1712);border:1px solid #ffffff22;flex:none">
  <div style="position:absolute;left:52px;top:14px;width:76px;height:76px;border-radius:50%;background:#ffffff10"></div>
  <div class="bx" style="left:30px;top:84px;width:120px;height:118px"><span class="lbl">&#128087; Dress</span></div>
  <div class="bx" style="left:56px;top:208px;width:70px;height:32px;border-color:{BEIGE}"></div>
  <div style="position:absolute;bottom:-34px;left:0;right:0;text-align:center;font-size:15px;opacity:.7">shopper photo</div>
</div>"""

BARS = "".join(
    f'<div style="height:{h}px;width:8px;border-radius:3px;background:linear-gradient({GOLD},{BEIGE});opacity:{o}"></div>'
    for h, o in zip(
        [38, 70, 22, 90, 54, 30, 76, 46, 62, 18, 84, 40],
        [0.9, 0.7, 0.8, 1, 0.6, 0.8, 0.9, 0.7, 0.8, 0.6, 1, 0.7],
    )
)
VEC = f"""<div style="display:flex;flex-direction:column;align-items:center;gap:10px;flex:none">
  <div style="display:flex;align-items:flex-end;gap:4px;height:96px">{BARS}</div>
  <div class="mono" style="font-size:15px;opacity:.75">512-d vector</div></div>"""
TILES = "".join(f'<div class="tile"><b>{s}</b></div>' for s in ["0.91", "0.88", "0.86", "0.84"])
GRID = f"""<div style="display:flex;flex-direction:column;gap:10px;flex:none;width:176px">
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px">{TILES}</div>
  <div style="font-size:15px;opacity:.7;text-align:center">top-k similar products</div></div>"""

CHIPS = "".join(
    f'<span class="chip" style="font-size:18px">{c}</span>' for c in ["FashionCLIP", "OWLv2", "FAISS", "FastAPI", "WooCommerce"]
)

BANNER = f"""<div class="grid-bg"></div>
<div style="position:absolute;inset:0;display:flex;align-items:center;padding:0 40px 0 64px;gap:28px">
  <div style="width:490px;flex:none;display:flex;flex-direction:column;gap:22px">
    <div style="display:flex;align-items:center;gap:14px">
      <div style="width:54px;height:54px;border-radius:16px;background:linear-gradient(135deg,{GOLD},{BEIGE});display:flex;align-items:center;justify-content:center;color:#1a1306;font-weight:800;font-size:26px">R</div>
      <div style="font-size:21px;opacity:.78;font-weight:600">Case Study &middot; Source included</div>
    </div>
    <div class="title" style="font-size:62px">RIZA AI<br><span class="accent" style="white-space:nowrap">Visual Search</span></div>
    <div style="font-size:25px;opacity:.86;line-height:1.38;max-width:480px">Shop a fashion store by photo. A FashionCLIP + FAISS search API and a WooCommerce plugin that works with any store.</div>
    <div style="display:flex;flex-wrap:wrap;gap:10px">{CHIPS}</div>
  </div>
  <div class="card2" style="flex:none;display:flex;align-items:center;gap:10px;padding:40px 20px 50px">{PHOTO}<div class="arrow">&rarr;</div>{VEC}<div class="arrow">&rarr;</div>{GRID}</div>
</div>"""


def node(tag, color, title, items, extra=""):
    lis = "".join(f"<li>{i}</li>" for i in items)
    return (
        f'<div class="node" style="{extra}"><span class="tag" style="background:{color}26;color:{color}">{tag}</span>'
        f"<h3>{title}</h3><ul>{lis}</ul></div>"
    )


def edge(label):
    return (
        '<div style="display:flex;flex-direction:column;justify-content:center;align-items:center" class="edge">'
        f'<div class="arrow">&#8644;</div>{label}</div>'
    )


ARCH = f"""<div class="grid-bg"></div>
<div style="position:absolute;inset:0;padding:54px 64px;display:flex;flex-direction:column;gap:30px">
  <div style="display:flex;align-items:baseline;justify-content:space-between">
    <div class="title" style="font-size:44px">Architecture</div>
    <div style="font-size:20px;opacity:.7">The model service stays private &middot; only WordPress talks to it</div>
  </div>
  <div style="display:grid;grid-template-columns:290px 80px 1fr 80px 1fr;align-items:stretch;flex:1">
    <div style="display:flex;flex-direction:column;gap:22px;justify-content:center">
      {node("Clients", SKY, "Shopper", ["Web storefront: camera button + modal", "Mobile app via the same REST routes", "Product page: &ldquo;similar items&rdquo; grid"])}
    </div>
    {edge("HTTPS<br>REST")}
    <div style="display:flex;flex-direction:column;gap:22px;justify-content:center">
      {node("WordPress plugin &middot; PHP", GOLD, "Visual Search for WooCommerce", ["<span class='mono'>/wp-json/vsw/v1</span>: detect, search, similar", "Per-visitor rate limit, MIME sniffing, private 30-min uploads", "Only published, visible products are returned", "Auto-index on save, batch indexer, settings page"])}
      {node("Catalogue", MINT, "WooCommerce", ["Products, gallery images, category names", "Hooks: save / trash / delete"], "padding:18px 24px")}
    </div>
    {edge("X-API-Key<br>private network")}
    <div style="display:flex;flex-direction:column;gap:22px;justify-content:center">
      {node("Visual search API &middot; Python", BEIGE, "FastAPI service", ["<b>OWLv2</b> detector: 36 garment prompts, lazy-loaded", "<b>FashionCLIP</b> embedder: 512-d, L2-normalised", "<b>FAISS IndexFlatIP</b>: exact cosine search", "Per-product dedupe, thresholds, category boost", "SSRF-guarded image fetcher for indexing"])}
      {node("Storage", SKY, "SQLite &rarr; in-memory index", ["vectors.db is the source of truth; loaded into FAISS at startup"], "padding:18px 24px")}
    </div>
  </div>
</div>"""


def step(n, title, body):
    return f'<div class="step"><div class="n">{n}</div><h4>{title}</h4><p>{body}</p></div>'


HOW = f"""<div class="grid-bg"></div>
<div style="position:absolute;inset:0;padding:60px 64px;display:flex;flex-direction:column;gap:34px">
  <div>
    <div class="accent" style="font-size:22px;font-weight:700;margin-bottom:10px">SIGNATURE FEATURE</div>
    <div class="title" style="font-size:50px">How &ldquo;search by photo&rdquo; works</div>
  </div>
  <div style="display:flex;gap:18px;flex:1">
    {step(1, "Upload", "The shopper picks or takes a photo. WordPress checks the real image type, caps the size and keeps it privately for 30 min.")}
    {step(2, "Detect", "OWLv2 runs 36 descriptive prompts (<code>a pair of heels</code>) and keeps the best box per garment type &rarr; tappable chips.")}
    {step(3, "Crop", "The chosen box is cropped with 10% padding: a little context (hem, collar) improves matches.")}
    {step(4, "Embed", "FashionCLIP turns the crop into a 512-d vector, L2-normalised so inner product = cosine similarity.")}
    {step(5, "Search", "FAISS returns <code>top_k &times; 6</code> image neighbours &rarr; best image per product &rarr; score threshold.")}
    {step(6, "Rank", "Products whose category matches the item (&ldquo;Dress&rdquo;, <bdi>&#1601;&#1587;&#1578;&#1575;&#1606;</bdi>) move first; hidden products are dropped.")}
  </div>
  <div style="display:flex;gap:40px;font-size:19px;opacity:.82">
    <div>&#9889; <span class="mono">/v1/search/quick</span> skips detection and searches the whole photo</div>
    <div>&#129513; The same index powers &ldquo;similar items&rdquo; on product pages</div>
  </div>
</div>"""

CFG = {
    "outDir": "..",
    "brand": {"name": "RIZA AI Visual Search", "tagline": "", "accent": GOLD, "accent2": BEIGE, "dark": True},
    "images": [
        {"type": "html", "file": "banner.png", "width": 1280, "height": 640, "css": CSS, "body": BANNER},
        {"type": "html", "file": "architecture.png", "width": 1600, "height": 820, "css": CSS, "body": ARCH},
        {"type": "html", "file": "how-visual-search-works.png", "width": 1600, "height": 700, "css": CSS, "body": HOW},
    ],
}

pathlib.Path(__file__).with_name("render.json").write_text(json.dumps(CFG, ensure_ascii=False, indent=1), encoding="utf-8")
print("render.json written")
