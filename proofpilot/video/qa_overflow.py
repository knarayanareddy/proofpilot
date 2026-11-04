import json, sys, time
from playwright.sync_api import sync_playwright

FRAMES = [int(x) for x in sys.argv[1:]] or [300]

SEEK_JS = """
async (frame) => {
  const w = window;
  if (typeof w.remotion_setFrame === 'function') {
    await w.remotion_setFrame({frame, composition: 'ProofPilot'});
    return 'api';
  }
  return 'no-api';
}
"""

CHECK_JS = """
() => {
  const out = [];
  document.querySelectorAll('*').forEach((el) => {
    const cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden') return;
    const r = el.getBoundingClientRect();
    if (r.width === 0 || r.height === 0) return;
    const text = (el.textContent || '').trim();
    const hasText = text.length > 0 && el.children.length === 0;
    const overflowX = el.scrollWidth - el.clientWidth;
    const overflowY = el.scrollHeight - el.clientHeight;
    const clipped = cs.overflow !== 'visible' && (overflowX > 2 || overflowY > 2);
    const outside = r.left < -2 || r.top < -2 || r.right > 1922 || r.bottom > 1082;
    if ((clipped && hasText) || (outside && hasText)) {
      out.push({
        tag: el.tagName, text: text.slice(0, 120),
        rect: [Math.round(r.left), Math.round(r.top), Math.round(r.width), Math.round(r.height)],
        ox: overflowX, oy: overflowY, clip: cs.overflow,
        fs: cs.fontSize, clipped, outside,
      });
    }
  });
  return out;
}
"""

with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/home/user/proofpilot/video/node_modules/.remotion/chrome-headless-shell/linux64/chrome-headless-shell-linux64/chrome-headless-shell", args=["--no-sandbox","--disable-dev-shm-usage"])
    pg = b.new_page(viewport={"width": 1920, "height": 1080})
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("console", lambda m: errs.append("console:" + m.text) if m.type == "error" else None)
    pg.goto("http://localhost:3000/?composition=ProofPilot", wait_until="networkidle", timeout=120000)
    time.sleep(6)
    print("title:", pg.title())
    mode = pg.evaluate(SEEK_JS, 0)
    print("seek mode:", mode, flush=True)
    for f in FRAMES:
        if mode == "api":
            pg.evaluate(SEEK_JS, f)
        else:
            pg.evaluate("(f) => { window.__f = f; }", f)
        time.sleep(1.2)
        res = pg.evaluate(CHECK_JS)
        print(f"\n=== frame {f} : {len(res)} issues")
        for r in res[:25]:
            print("  ", json.dumps(r, ensure_ascii=False))
        if mode != "api":
            # fallback: type the frame into the studio's time field
            pass
    print("\npage errors:", errs[:10])
    b.close()
