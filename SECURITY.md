# Security Policy

Built by Omar Rao, Engineer - Data Resilience, Cybersecurity and Privacy
https://www.linkedin.com/in/omarrao/ | https://omarrao.substack.com/

---

## Supported Versions

| Version | Supported |
|---|---|
| Latest (main branch) | Yes |
| Prior releases | No |

R3VP is under active development. Security fixes are applied to the main branch only.

---

## Reporting a Vulnerability

**Please do not open a public GitHub issue for security vulnerabilities.**

Use GitHub's private vulnerability reporting to disclose security issues responsibly:

1. Go to the [Security Advisories](https://github.com/OmarRao/r3vp/security/advisories) tab
2. Click **Report a vulnerability**
3. Fill in the advisory form with as much detail as possible

You can also reach out directly via LinkedIn: https://www.linkedin.com/in/omarrao/

---

## What to Include

A good vulnerability report includes:

- Description of the vulnerability and its impact
- Steps to reproduce (proof of concept if available)
- Affected component (appliance, API, portal, a specific dependency)
- Suggested severity (Critical / High / Medium / Low)
- Your preferred credit attribution for the advisory

---

## Response Timeline

| Stage | Target |
|---|---|
| Initial acknowledgement | Within 48 hours |
| Severity assessment | Within 5 business days |
| Fix or mitigation | Depends on severity (Critical: 7 days, High: 14 days, Medium/Low: 30 days) |
| Public advisory | After fix is merged and released |

---

## Scope

The following are in scope:

- **Appliance**: credential handling, SOPS vault, mTLS relay client, Temporal workflow activities
- **API**: authentication bypass, authorization flaws (RBAC/MSSP permission escalation), SQL injection, injection in report generation
- **Portal**: XSS, CSRF, Auth0 token handling, sensitive data exposure
- **Compliance**: tampering with hash-chained audit log, evidence bundle integrity bypass
- **Dependencies**: known CVEs in pinned versions with a clear exploit path

The following are out of scope:

- Vulnerabilities requiring physical access to the appliance host
- Social engineering attacks
- Issues in third-party services (Temporal Cloud, Auth0, Stripe) that R3VP cannot control
- Self-XSS or vulnerabilities requiring the attacker to already have admin access

---

## Security Architecture Notes

Key design decisions relevant to security researchers:

- **Credentials never leave the customer environment.** Veeam and vCenter credentials are encrypted with SOPS + age inside the appliance. The SaaS API never receives or stores plaintext credentials.
- **Outbound-only appliance communication.** The appliance opens no inbound ports. All communication is outbound HTTPS with mutual TLS.
- **mTLS thumbprint verification.** Every appliance request is verified against the registered certificate thumbprint in the database.
- **Hash-chained audit log.** The appliance audit trail uses SHA-256 chaining. Any modification to a historical entry breaks the chain and is detectable.
- **API keys are SHA-256 hashed.** Raw key values are shown once at creation and never stored.
- **RBAC with 24 named permissions.** Authorization is enforced at the service layer, not just the router layer.

---

## Credits

Security researchers who responsibly disclose vulnerabilities will be credited in the published GitHub Security Advisory unless they prefer to remain anonymous.

---

*Built by Omar Rao, Engineer - Data Resilience, Cybersecurity and Privacy*
*https://www.linkedin.com/in/omarrao/ | https://omarrao.substack.com/*
