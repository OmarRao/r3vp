"""Re-screenshot all mockup HTML files at 1440x900."""
import pathlib
from playwright.sync_api import sync_playwright

BASE = pathlib.Path(__file__).parent.parent / "docs" / "screenshots"

NAME_MAP = {
    "mockup-ai-insights": "ai-insights",
    "mockup-analytics": "analytics",
    "mockup-api-keys": "api-keys",
    "mockup-compliance-frameworks": "compliance-frameworks",
    "mockup-console": "console",
    "mockup-continuous-validation": "continuous-validation",
    "mockup-dashboard": "dashboard",
    "mockup-evidence-vault": "evidence-vault",
    "mockup-fleet": "fleet",
    "mockup-incidents": "incidents",
    "mockup-integrations": "integrations",
    "mockup-mssp": "mssp",
    "mockup-multicloud-dashboard": "multicloud-dashboard",
    "mockup-onboarding": "onboarding",
    "mockup-providers-p6": "providers-p6",
    "mockup-providers": "providers",
    "mockup-reports": "reports",
    "mockup-runbook-execution": "runbook-execution",
    "mockup-runbooks": "runbooks",
    "mockup-schedule": "schedule",
    "mockup-scorecard": "scorecard",
    "mockup-sso": "sso",
    "mockup-team": "team",
    "mockup-testrun": "test-run-detail",
    "mockup-threat-scanner": "threat-scanner",
    "mockup-workloads": "workloads",
}

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.set_viewport_size({"width": 1440, "height": 900})
    for stem, out_name in NAME_MAP.items():
        html_path = BASE / f"{stem}.html"
        if not html_path.exists():
            print(f"  SKIP  {stem}.html (not found)")
            continue
        out_path = BASE / f"{out_name}.png"
        page.goto(html_path.as_uri())
        page.wait_for_timeout(400)
        page.screenshot(path=str(out_path))
        print(f"  OK    {out_name}.png")
    browser.close()

print("Done.")
