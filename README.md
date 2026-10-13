# Status — website uptime page

A small, public status page for Wick, Inkwell, and Whack-a-mole. The page is a static site hosted on Surge; GitHub Actions checks the websites, publishes their latest status, and sends outage alerts.

The design uses a warm, paper-like light theme and an ink-dark theme, with a persistent light/dark toggle. The editorial typography takes a cue from the writing-focused Wick and Inkwell sites, while the simple, playful service marks keep the page easy to scan.

## Current monitors

| Name | Website |
| --- | --- |
| Wick | <https://wick-md.surge.sh> |
| Inkwell | <https://inkwell-md.surge.sh> |
| Whack-a-mole | <https://whackamole-game.surge.sh> |

An HTTP `2xx` or `3xx` response is considered healthy. An HTTP `4xx`/`5xx` response, connection error, or timeout is considered down. Each check uses a 12-second timeout. The page refreshes its displayed status every minute; GitHub Actions checks on a 15-minute schedule. GitHub schedules are best-effort and may run late.

## How it works

- `public/` contains the complete static site. It does not require a frontend build or install any browser-side packages.
- `monitors.json` is the editable list of monitor IDs, names, and URLs.
- `.github/workflows/status-monitor.yml` checks the configured websites every 15 minutes, updates the status JSON, saves incident state, and deploys `public/` to Surge.
- `scripts/monitor.py` probes websites and handles outage/recovery transitions. It sends an email and opens one GitHub issue when a site first goes down. Repeated failed checks during the same outage do not send duplicate alerts. When a site recovers, its issue is closed; a later outage starts a new incident.
- `scripts/manage_sites.py` validates website changes submitted through the Actions workflow form.
- `monitor-state.json` tracks active incidents and pending issue closures. It is committed by Actions so the alert lifecycle survives between scheduled runs. It contains no credentials.

The public page is read-only. A person with write access to this GitHub repository can add, edit, or remove monitors through **Actions → Status monitor → Run workflow**. This makes GitHub repository access the authorization boundary; there is no separate website login or embedded editor.

## Deploy and configure

1. In the repository's **Settings → Secrets and variables → Actions**, add these **secrets**:

   | Secret | Value |
   | --- | --- |
   | `SURGE_TOKEN` | A deployment token from your Surge account. Create one locally with `surge token`; do not paste it into an issue or commit it. |
   | `SMTP_HOST` | The SMTP server hostname for the mailbox/provider that will send alerts. |
   | `SMTP_PORT` | SMTP port, usually `465` for implicit TLS or `587` for STARTTLS. |
   | `SMTP_USERNAME` | SMTP account username. |
   | `SMTP_PASSWORD` | SMTP account password or app password. |
   | `SMTP_FROM` | Verified sender address accepted by your SMTP provider. |

2. Optionally add these **Actions variables**:

   | Variable | Default | Purpose |
   | --- | --- | --- |
   | `ALERT_EMAIL` | `bpanda.cp@gmail.com` | Destination for outage email. |
   | `SURGE_DOMAIN` | `olympus-mons26-statuspage.surge.sh` | Surge domain to deploy. Choose a domain available to your Surge account. |

   The default contact button uses `mailto:bpanda.cp@gmail.com`; change `contactUrl` in `public/site-config.json` if you want a different contact destination. The repository link is configured there too.

3. Confirm GitHub Actions are enabled for the repository and that the workflow can use its `GITHUB_TOKEN` to write repository contents and issues. The workflow declares the required `contents: write` and `issues: write` permissions. Since the monitor list and incident state are committed back to the default branch, branch protection must allow the Actions bot to push these commits; otherwise incident deduplication and workflow-based edits will not persist.
4. Run **Actions → Status monitor → Run workflow**, choose **check**, and run it once to perform an initial check and deploy. Alternatively, run the **Status monitor** workflow with **add**, **edit**, or **remove** to change monitors and deploy the result.
5. Open the `SURGE_DOMAIN` value after the deployment step succeeds. For the default domain, that is <https://olympus-mons26-statuspage.surge.sh>.

The first failed check of a website sends the alert email and creates a `[Website down]` issue in this repository. When the next check finds it healthy, the issue is closed. If email delivery fails, the workflow reports the failure and retries on a later failed check; the GitHub issue is not duplicated if it was already created.

## Manage websites without editing code

Open **Actions → Status monitor → Run workflow** and select an operation:

- **add** requires a display name and an `http://` or `https://` URL.
- **edit** requires the exact current URL, plus the new display name and URL.
- **remove** requires the exact current URL.
- **check** leaves the monitor list unchanged and runs a check/deployment.

Changes are validated, saved to `monitors.json`, and included in the status-page deployment. URLs with embedded usernames or passwords are rejected. Anyone who can run a workflow that writes to this repository must be trusted with repository write access.

## Run locally

You can preview the static page with any static file server. For example, from the repository root:

```sh
python3 -m http.server 8000 --directory public
```

Then open <http://localhost:8000>. The public page and monitor scripts use only browser/Python standard-library features, so no Python virtual environment or package installation is needed. The initial status is `Waiting for check` until `public/status.json` contains a result; for a local preview, that file is seeded with the three configured websites and an unknown status.

To run the Python checks in an isolated virtual environment (optional; no third-party packages are needed):

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m unittest discover -s tests -v
deactivate
```

Open the local preview URL in a browser to try the page, theme toggle, status display, and responsive layout.

## Project layout

```text
.github/workflows/status-monitor.yml  Scheduled checks, management, alerts, deployment
monitors.json                         Editable monitor list
monitor-state.json                    Persistent outage/notification state
public/                               Static page, styles, scripts, published status
scripts/                              Monitor and website-management logic
tests/                                Monitor lifecycle and validation tests
```