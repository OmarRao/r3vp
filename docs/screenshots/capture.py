"""Regenerate README/user-guide screenshots from the mockup HTML files.

Renders each mockup-*.html to a PNG at 1440x900 with headless Chromium.

Usage:
    # regenerate every screenshot
    python capture.py

    # regenerate only specific ones (by PNG name, with or without .png)
    python capture.py ai-insights reports

Requires Playwright:
    pip install playwright && playwright install chromium

Built by Omar Rao, Engineer - Data Resilience, Cybersecurity and Privacy
https://www.linkedin.com/in/omarrao/ | https://omarrao.substack.com/
"""
import asyncio
import sys
from pathlib import Path

from playwright.async_api import async_playwright

BASE = Path(__file__).resolve().parent

# mockup HTML file -> output PNG name
PAGES = {
    "mockup-ai-insights.html": "ai-insights.png",
    "mockup-analytics.html": "analytics.png",
    "mockup-api-keys.html": "api-keys.png",
    "mockup-compliance-frameworks.html": "compliance-frameworks.png",
    "mockup-console.html": "console.png",
    "mockup-continuous-validation.html": "continuous-validation.png",
    "mockup-dashboard.html": "dashboard.png",
    "mockup-demo-dashboard.html": "demo-dashboard.png",
    "mockup-demo-login.html": "demo-login.png",
    "mockup-evidence-vault.html": "evidence-vault.png",
    "mockup-fleet.html": "fleet.png",
    "mockup-incidents.html": "incidents.png",
    "mockup-integrations.html": "integrations.png",
    "mockup-mssp.html": "mssp.png",
    "mockup-multicloud-dashboard.html": "multicloud-dashboard.png",
    "mockup-onboarding.html": "onboarding.png",
    "mockup-providers-p6.html": "providers-p6.png",
    "mockup-providers.html": "providers.png",
    "mockup-reports.html": "reports.png",
    "mockup-runbook-execution.html": "runbook-execution.png",
    "mockup-runbooks.html": "runbooks.png",
    "mockup-schedule.html": "schedule.png",
    "mockup-scorecard.html": "scorecard.png",
    "mockup-sso.html": "sso.png",
    "mockup-team.html": "team.png",
    "mockup-testrun.html": "test-run-detail.png",
    "mockup-threat-scanner.html": "threat-scanner.png",
    "mockup-workloads.html": "workloads.png",
}


async def capture(pairs: list[tuple[str, str]]) -> None:
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 1440, "height": 900})
        for html, png in pairs:
            url = "file:///" + str(BASE / html).replace("\\", "/")
            await page.goto(url, wait_until="networkidle")
            await page.screenshot(path=str(BASE / png), full_page=False)
            print(f"Done: {png}")
        await browser.close()


def main() -> None:
    wanted = {a.removesuffix(".png") for a in sys.argv[1:]}
    if wanted:
        pairs = [(h, p) for h, p in PAGES.items() if p.removesuffix(".png") in wanted]
        missing = wanted - {p.removesuffix(".png") for _, p in pairs}
        if missing:
            print(f"Unknown screenshot name(s): {', '.join(sorted(missing))}")
            sys.exit(1)
    else:
        pairs = list(PAGES.items())
    asyncio.run(capture(pairs))


if __name__ == "__main__":
    main()
