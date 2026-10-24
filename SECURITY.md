# Security Policy

## Supported Versions

| Version | Supported |
| ------- | --------- |
| Latest release | :white_check_mark: |
| Older releases | :x: |

## Reporting a Vulnerability

If you discover a security vulnerability in **PrintMoney**, please report it **privately and responsibly**.

- **Preferred:** Use [GitHub Private Vulnerability Reporting](https://github.com/cibi-dev/print-money/security/advisories/new).
- **Alternative:** If private reporting is unavailable, send details to the repository owner via the GitHub profile contact or open an issue **only if it doesn't contain sensitive information**.

Please include as much information as possible: steps to reproduce, affected version, potential impact, and any suggested fix.

We will acknowledge your report as soon as possible, evaluate it, and respond with the expected timeline for a fix. Please do not publicly disclose vulnerabilities until a fix is released.

## Security Notes

- **Local-first:** PrintMoney is a desktop application that runs locally. User data is stored in %APPDATA%\PrintMoney\ (SQLite database).
- **No telemetry:** The app does not send data to external servers by publicly embedded telemetry routines.
- **Third-party dependencies:** Keep your environment updated to minimize risk.
- **Windows SmartScreen:** Signed releases will reduce warnings; unsigned releases may show SmartScreen warnings due to the application certificate status.
