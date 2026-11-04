import json, time
from playwright.sync_api import sync_playwright
import urllib.request

EXE = "/home/user/proofpilot/video/node_modules/.remotion/chrome-headless-shell/linux64/chrome-headless-shell-linux64/chrome-headless-shell"
BASE = "http://localhost:8000"

def head(url, rng=None):
    req = urllib.request.Request(url, method="HEAD")
    if rng: req.add_header("Range", rng)
    with urllib.request.urlopen(req) as r:
        return r.status, dict(r.headers)

for url in [BASE + "/film.mp4", BASE + "/film-poster.jpg", BASE + "/film", BASE + "/film-contact-sheet.jpg"]:
    try:
        st, h = head(url)
        print("HEAD %-28s %s  type=%s  len=%s  ranges=%s" % (url.replace(BASE, ""), st, h.get("Content-Type"), h.get("Content-Length"), h.get("Accept-Ranges")))
    except Exception as e:
        print("HEAD", url, "FAILED", e)

try:
    st, h = head(BASE + "/film.mp4", "bytes=1000-1999")
    print("RANGE bytes=1000-1999 ->", st, h.get("Content-Range"), "len", h.get("Content-Length"))
except Exception as e:
    print("RANGE FAILED", e)

with sync_playwright() as p:
    b = p.chromium.launch(executable_path=EXE, args=["--no-sandbox", "--disable-dev-shm-usage", "--autoplay-policy=no-user-gesture-required"])
    pg = b.new_page(viewport={"width": 1440, "height": 1000})
    errs = []
    pg.on("pageerror", lambda e: errs.append("pageerror:" + str(e)))
    pg.on("console", lambda m: errs.append("console:" + m.text) if m.type == "error" else None)
    pg.on("requestfailed", lambda r: errs.append("reqfail:" + r.url + " " + str(r.failure)))

    pg.goto(BASE + "/workspace", wait_until="networkidle", timeout=60000)
    time.sleep(2)
    info = pg.evaluate("""() => {
      const v = document.querySelector('video.film');
      if (!v) return {found: false};
      const r = v.getBoundingClientRect();
      return {
        found: true,
        src: v.querySelector('source')?.getAttribute('src'),
        poster: v.getAttribute('poster'),
        rect: [Math.round(r.x), Math.round(r.y), Math.round(r.width), Math.round(r.height)],
        inViewport: r.top < window.innerHeight && r.bottom > 0,
        canMp4: v.canPlayType('video/mp4; codecs="avc1.42E01E, mp4a.40.2"'),
      };
    }""")
    print("\nworkspace video:", json.dumps(info))
    play = pg.evaluate("""async () => {
      const v = document.querySelector('video.film');
      v.muted = true;
      try { await v.play(); } catch (e) { return {error: String(e)}; }
      await new Promise(r => setTimeout(r, 2500));
      const out = {duration: v.duration, currentTime: v.currentTime, readyState: v.readyState,
                   videoWidth: v.videoWidth, videoHeight: v.videoHeight, paused: v.paused, error: v.error && v.error.code};
      v.currentTime = 120; // seek test
      await new Promise(r => setTimeout(r, 2500));
      out.afterSeek = v.currentTime; out.pausedAfterSeek = v.paused;
      return out;
    }""")
    print("playback:", json.dumps(play))
    pg.screenshot(path="/tmp/ws_film.png", full_page=False)

    pg.goto(BASE + "/film", wait_until="networkidle", timeout=60000)
    time.sleep(2)
    f = pg.evaluate("""async () => {
      const v = document.querySelector('video'); v.muted = true;
      try { await v.play(); } catch (e) { return {error: String(e)}; }
      await new Promise(r => setTimeout(r, 2000));
      return {duration: v.duration, t: v.currentTime, w: v.videoWidth, h: v.videoHeight, rs: v.readyState};
    }""")
    print("film page playback:", json.dumps(f))
    pg.screenshot(path="/tmp/film_page.png")

    print("\nerrors:", [e for e in errs if "favicon" not in e][:8])
    b.close()
