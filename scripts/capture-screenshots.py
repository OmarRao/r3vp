"""
Capture screenshots of R3VP portal mockups using Playwright.

Run:
    python -m playwright install chromium
    python scripts/capture-screenshots.py
"""
import subprocess
import sys
import pathlib

base = pathlib.Path(__file__).parent.parent / "docs" / "screenshots"

def main():
    # Install playwright browser if needed
    subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True)

    from playwright.sync_api import sync_playwright

    pages = [
        ("mockup-console.html", "console.png"),
        ("mockup-threat-scanner.html", "threat-scanner.png"),
        ("mockup-incidents.html", "incidents.png"),
        ("mockup-dashboard.html", "dashboard.png"),
        ("mockup-workloads.html", "workloads.png"),
        ("mockup-testrun.html", "test-run-detail.png"),
    ]

    with sync_playwright() as p:
        browser = p.chromium.launch()
        for html_file, png_file in pages:
            html_path = base / html_file
            if not html_path.exists():
                print(f"Skipping {html_file} (not found)")
                continue
            page = browser.new_page(viewport={"width": 1440, "height": 860})
            url = "file:///" + str(html_path).replace("\\", "/")
            page.goto(url)
            page.wait_for_timeout(800)
            out = base / png_file
            page.screenshot(path=str(out), full_page=False)
            print(f"Captured {png_file}")
        browser.close()

if __name__ == "__main__":
    main()
