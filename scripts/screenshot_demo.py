"""Screenshot the demo login and demo dashboard mockups."""
import pathlib
from playwright.sync_api import sync_playwright

BASE = pathlib.Path(__file__).parent.parent / "docs" / "screenshots"

SHOTS = [
    ("mockup-demo-login.html",     "demo-login.png",     400, 700),
    ("mockup-demo-dashboard.html", "demo-dashboard.png", 1440, 900),
]

with sync_playwright() as p:
    browser = p.chromium.launch()
    for html, out, w, h in SHOTS:
        page = browser.new_page()
        page.set_viewport_size({"width": w, "height": h})
        page.goto((BASE / html).as_uri())
        page.wait_for_timeout(400)
        page.screenshot(path=str(BASE / out))
        print(f"  OK  {out}")
        page.close()
    browser.close()

print("Done.")
