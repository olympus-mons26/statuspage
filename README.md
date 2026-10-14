# Status Page for olympus-mons26

A public uptime dashboard for the Wick, Inkwell, and Whack-a-mole websites. The page displays the latest check results, refreshes them every minute, and supports light and dark themes. GitHub Actions checks monitored sites every 15 minutes and deploys the static site to Surge.

**Public status page:** <https://olympus-mons26-statuspage.surge.sh>

## Monitored websites

| Service | URL |
| --- | --- |
| Wick | <https://wick-md.surge.sh> |
| Inkwell | <https://inkwell-md.surge.sh> |
| Whack-a-mole | <https://whackamole-game.surge.sh> |

An HTTP `2xx` or `3xx` response is healthy. HTTP `4xx`/`5xx` responses, connection errors, and timeouts are considered down. Each request has a 12-second timeout. GitHub scheduled workflows are best-effort and may run late.

## How it works

- `public/` is the static website. It has no frontend build step or browser-side package dependencies.
- `monitors.json` is the monitor list. A repository writer can manage it through the **Status monitor** GitHub Actions workflow.
- `scripts/monitor.py` checks each URL, writes public results to `public/status.json`, and tracks outage and recovery state in `monitor-state.json`.
- On a newly detected outage, the monitor attempts to send an email and create a GitHub issue. On recovery, it closes the incident issue. Repeated failures during the same incident do not create duplicate issues or resend a successful email.
- `.github/workflows/status-monitor.yml` runs checks every 15 minutes, supports manual monitor-list changes, and deploys `public/` to Surge.

The public page is read-only; there is no separate website login or embedded editor. GitHub repository write access is required to change the monitor list.

## Setup and deployment

### Configure GitHub Actions

In the repository, open **Settings → Secrets and variables → Actions** and add these repository secrets:

| Secret | Purpose |
| --- | --- |
| `SURGE_TOKEN` | Surge deployment token. Create one with the Surge CLI command `surge token`. |
| `SMTP_HOST` | SMTP server hostname used for alert email. |
| `SMTP_PORT` | SMTP port, usually `465` (implicit TLS) or `587` (STARTTLS). |
| `SMTP_USERNAME` | SMTP account username. |
| `SMTP_PASSWORD` | SMTP password or app password. |
| `SMTP_FROM` | Verified sender email address. |

Keep credentials in GitHub Secrets; do not commit them to this repository.

Optional repository Actions variables:

| Variable | Default | Purpose |
| --- | --- | --- |
| `SURGE_DOMAIN` | `olympus-mons26-statuspage.surge.sh` | Surge domain to deploy to. |
| `ALERT_EMAIL` | `bpanda.cp@gmail.com` | Destination for outage notifications. |

The workflow uses the repository's `GITHUB_TOKEN` to create and close issues. Its declared permissions include `contents: write` and `issues: write`. If branch protection is enabled, allow the Actions bot to push updates to `monitors.json` and `monitor-state.json`.

### Deploy the site

After configuring `SURGE_TOKEN` and the SMTP secrets, open **Actions → Status monitor → Run workflow**, select **check**, then run the workflow. A successful deployment publishes the page at <https://olympus-mons26-statuspage.surge.sh>. Scheduled checks then run every 15 minutes.

If email settings are missing or invalid, outage email notifications will fail and the workflow will report the notification error. Status results are still published, and the monitor retries notifications on a later failed check.

## Manage monitored websites

Open **Actions → Status monitor → Run workflow** and select an operation:

- **add** — enter a display name and an `http://` or `https://` URL.
- **edit** — enter the exact current URL and the new display name and URL.
- **remove** — enter the exact current URL.
- **check** — leave the monitor list unchanged, check the sites, and deploy.

The workflow validates changes and includes them in the deployment. URLs containing embedded usernames or passwords are rejected. Anyone able to run a workflow that writes to the repository must be trusted with repository write access.

## Preview locally

From the repository root, run:

```sh
python3 -m http.server 8000 --directory public
```

Then visit <http://localhost:8000>. The included `public/status.json` starts with unknown statuses until a monitor check publishes real results.

## Run tests

The Python tests use only the standard library:

```sh
python3 -m unittest discover -s tests -v
```

## Project layout

```text
.github/workflows/status-monitor.yml  Scheduled checks, alerts, management, deployment
monitors.json                         Editable website monitor list
monitor-state.json                    Persistent incident and notification state
public/                               Static site and published status data
scripts/                              Monitoring and monitor-management logic
tests/                                Unit tests
```
