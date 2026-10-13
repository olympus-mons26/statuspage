import email.message
import json
import os
import smtplib
import socket
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from scripts.site_config import read_json, validate_monitors, write_json


class NotificationError(RuntimeError):
    pass


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def probe_url(url, timeout=12):
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "StatusPageMonitor/1.0"},
    )
    started = time.monotonic()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            status_code = response.getcode()
            healthy = 200 <= status_code < 400
            return {
                "healthy": healthy,
                "httpStatus": status_code,
                "error": None if healthy else f"HTTP {status_code}",
                "responseTimeMs": round((time.monotonic() - started) * 1000),
            }
    except urllib.error.HTTPError as error:
        healthy = 200 <= error.code < 400
        return {
            "healthy": healthy,
            "httpStatus": error.code,
            "error": None if healthy else f"HTTP {error.code}",
            "responseTimeMs": round((time.monotonic() - started) * 1000),
        }
    except (urllib.error.URLError, TimeoutError, socket.timeout, OSError) as error:
        reason = error.reason if isinstance(error, urllib.error.URLError) else error
        return {
            "healthy": False,
            "httpStatus": None,
            "error": str(reason)[:240],
            "responseTimeMs": round((time.monotonic() - started) * 1000),
        }


def github_request(method, path, payload=None):
    token = os.environ.get("GH_TOKEN")
    repository = os.environ.get("GITHUB_REPOSITORY")
    if not token or not repository:
        raise NotificationError("GitHub issue notifications require GH_TOKEN and GITHUB_REPOSITORY.")

    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        f"https://api.github.com/repos/{repository}{path}",
        data=body,
        method=method,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "StatusPageMonitor",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            response_body = response.read()
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")[:500]
        raise NotificationError(f"GitHub API request failed ({error.code}): {detail}") from error
    except (urllib.error.URLError, TimeoutError, socket.timeout, OSError) as error:
        raise NotificationError(f"GitHub API request failed: {error}") from error
    if not response_body:
        return {}
    return json.loads(response_body.decode("utf-8"))


def create_issue(monitor, incident, result):
    started_at = incident["startedAt"]
    details = result.get("error") or f"HTTP {result.get('httpStatus', 'unknown status')}"
    issue = github_request("POST", "/issues", {
        "title": f"[Website down] {monitor['name']}",
        "body": (
            f"**{monitor['name']}** is not responding as expected.\n\n"
            f"- URL: {monitor['url']}\n"
            f"- First detected: {started_at}\n"
            f"- Latest result: {details}\n\n"
            "This issue is created automatically by the status monitor."
        ),
    })
    issue_number = issue.get("number")
    if not isinstance(issue_number, int):
        raise NotificationError("GitHub created an issue without returning its issue number.")
    return issue_number


def close_issue(issue_number):
    github_request("PATCH", f"/issues/{issue_number}", {"state": "closed"})


def send_alert_email(monitor, incident, result):
    recipient = os.environ.get("ALERT_EMAIL", "").strip()
    host = os.environ.get("SMTP_HOST", "").strip()
    port_value = os.environ.get("SMTP_PORT", "").strip()
    username = os.environ.get("SMTP_USERNAME", "")
    password = os.environ.get("SMTP_PASSWORD", "")
    sender = os.environ.get("SMTP_FROM", "").strip()
    if not all((recipient, host, port_value, username, password, sender)):
        raise NotificationError(
            "Email alert settings are incomplete; configure ALERT_EMAIL and the SMTP_* secrets."
        )
    try:
        port = int(port_value)
    except ValueError as error:
        raise NotificationError("SMTP_PORT must be a valid integer.") from error

    message = email.message.EmailMessage()
    message["Subject"] = f"[Status alert] {monitor['name']} is not working"
    message["From"] = sender
    message["To"] = recipient
    message.set_content(
        f"{monitor['name']} is not responding as expected.\n\n"
        f"Website: {monitor['url']}\n"
        f"First detected: {incident['startedAt']}\n"
        f"Latest result: {result.get('error') or result.get('httpStatus')}\n"
    )

    try:
        if port == 465:
            with smtplib.SMTP_SSL(host, port, timeout=20) as server:
                server.login(username, password)
                server.send_message(message)
        else:
            with smtplib.SMTP(host, port, timeout=20) as server:
                server.starttls()
                server.login(username, password)
                server.send_message(message)
    except (smtplib.SMTPException, OSError, ValueError) as error:
        raise NotificationError(f"Email alert delivery failed: {error}") from error


def run_monitor(
    monitors_path="monitors.json",
    state_path="monitor-state.json",
    status_path="public/status.json",
    probe=probe_url,
    issue_creator=create_issue,
    issue_closer=close_issue,
    email_sender=send_alert_email,
    clock=utc_now,
):
    monitors = validate_monitors(read_json(monitors_path))
    state = read_json(state_path, default={"sites": {}, "pendingClosures": []})
    if not isinstance(state, dict) or not isinstance(state.get("sites"), dict):
        raise ValueError("monitor-state.json has an invalid format.")
    pending_closures = state.setdefault("pendingClosures", [])
    if not isinstance(pending_closures, list):
        raise ValueError("monitor-state.json pendingClosures must be a list.")

    state_sites = state["sites"]
    monitor_ids = {site["id"] for site in monitors}
    errors = []
    now = clock()

    for removed_id in set(state_sites) - monitor_ids:
        removed = state_sites.pop(removed_id)
        incident = removed.get("incident") or {}
        issue_number = incident.get("issueNumber")
        if issue_number is not None:
            pending_closures.append({
                "issueNumber": issue_number,
                "monitorId": removed_id,
            })

    public_sites = []
    for monitor in monitors:
        result = probe(monitor["url"])
        previous = state_sites.get(monitor["id"], {"status": "unknown", "incident": None})
        previous_status = previous.get("status", "unknown")
        incident = previous.get("incident")

        if result["healthy"]:
            if incident and incident.get("issueNumber") is not None:
                pending_closures.append({
                    "issueNumber": incident["issueNumber"],
                    "monitorId": monitor["id"],
                })
            incident = None
            current_status = "up"
        else:
            current_status = "down"
            if previous_status != "down" or not incident:
                incident = {
                    "startedAt": now,
                    "issueNumber": None,
                    "emailSent": False,
                }

        state_sites[monitor["id"]] = {
            "status": current_status,
            "incident": incident,
        }

        if current_status == "down" and incident:
            if incident.get("issueNumber") is None:
                try:
                    incident["issueNumber"] = issue_creator(monitor, incident, result)
                except NotificationError as error:
                    errors.append(f"{monitor['name']}: {error}")
            if not incident.get("emailSent", False):
                try:
                    email_sender(monitor, incident, result)
                    incident["emailSent"] = True
                except NotificationError as error:
                    errors.append(f"{monitor['name']}: {error}")

        public_sites.append({
            "id": monitor["id"],
            "name": monitor["name"],
            "url": monitor["url"],
            "status": current_status,
            "checkedAt": now,
            "responseTimeMs": result.get("responseTimeMs"),
            "httpStatus": result.get("httpStatus"),
        })

    remaining_closures = []
    closed_numbers = set()
    for closure in pending_closures:
        issue_number = closure.get("issueNumber")
        if issue_number in closed_numbers:
            continue
        closed_numbers.add(issue_number)
        try:
            issue_closer(issue_number)
        except NotificationError as error:
            errors.append(f"Could not close recovered incident #{issue_number}: {error}")
            remaining_closures.append(closure)
    state["pendingClosures"] = remaining_closures

    write_json(state_path, state)
    write_json(status_path, {
        "generatedAt": now,
        "sites": public_sites,
    })
    for site in public_sites:
        print(f"{site['name']}: {site['status']}")
    return errors


def main():
    errors = run_monitor()
    if errors:
        for error in errors:
            print(f"::error::{error}", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
