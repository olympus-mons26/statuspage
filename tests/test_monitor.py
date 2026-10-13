import json
import tempfile
import unittest
from pathlib import Path

from scripts.monitor import run_monitor


class MonitorLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.monitors_path = self.root / "monitors.json"
        self.state_path = self.root / "monitor-state.json"
        self.status_path = self.root / "public" / "status.json"
        self.monitors = [{
            "id": "example",
            "name": "Example",
            "url": "https://example.com",
        }]
        self.monitors_path.write_text(json.dumps(self.monitors), encoding="utf-8")
        self.state_path.write_text(
            json.dumps({"sites": {}, "pendingClosures": []}),
            encoding="utf-8",
        )
        self.results = []
        self.created_issues = []
        self.closed_issues = []
        self.emails = []
        self.now = 0

    def tearDown(self):
        self.temp_dir.cleanup()

    def run_check(self):
        self.now += 1
        return run_monitor(
            monitors_path=self.monitors_path,
            state_path=self.state_path,
            status_path=self.status_path,
            probe=lambda _url: self.results.pop(0),
            issue_creator=self.create_issue,
            issue_closer=self.closed_issues.append,
            email_sender=lambda monitor, incident, result: self.emails.append(
                (monitor["id"], incident["startedAt"], result["error"])
            ),
            clock=lambda: f"2026-01-01T00:00:{self.now:02d}Z",
        )

    def create_issue(self, monitor, incident, result):
        number = 100 + len(self.created_issues)
        self.created_issues.append((monitor["id"], incident["startedAt"], result["error"]))
        return number

    @staticmethod
    def down_result():
        return {
            "healthy": False,
            "httpStatus": 503,
            "error": "HTTP 503",
            "responseTimeMs": 12,
        }

    @staticmethod
    def up_result():
        return {
            "healthy": True,
            "httpStatus": 200,
            "error": None,
            "responseTimeMs": 8,
        }

    def test_alerts_once_per_outage_and_realerts_after_recovery(self):
        self.results = [self.down_result()]
        self.assertEqual(self.run_check(), [])
        self.assertEqual(len(self.created_issues), 1)
        self.assertEqual(len(self.emails), 1)

        self.results = [self.down_result()]
        self.assertEqual(self.run_check(), [])
        self.assertEqual(len(self.created_issues), 1)
        self.assertEqual(len(self.emails), 1)

        self.results = [self.up_result()]
        self.assertEqual(self.run_check(), [])
        self.assertEqual(self.closed_issues, [100])

        self.results = [self.down_result()]
        self.assertEqual(self.run_check(), [])
        self.assertEqual(len(self.created_issues), 2)
        self.assertEqual(len(self.emails), 2)

    def test_notification_failure_is_reported_and_retried_without_duplicate_issue(self):
        def fail_email(_monitor, _incident, _result):
            from scripts.monitor import NotificationError
            raise NotificationError("SMTP unavailable")

        self.results = [self.down_result()]
        errors = run_monitor(
            monitors_path=self.monitors_path,
            state_path=self.state_path,
            status_path=self.status_path,
            probe=lambda _url: self.results.pop(0),
            issue_creator=self.create_issue,
            issue_closer=self.closed_issues.append,
            email_sender=fail_email,
            clock=lambda: "2026-01-01T00:00:01Z",
        )
        self.assertEqual(len(errors), 1)
        self.assertEqual(len(self.created_issues), 1)

        self.results = [self.down_result()]
        errors = self.run_check()
        self.assertEqual(errors, [])
        self.assertEqual(len(self.created_issues), 1)
        self.assertEqual(len(self.emails), 1)

    def test_status_file_contains_only_current_public_results(self):
        self.results = [self.up_result()]
        self.run_check()
        status = json.loads(self.status_path.read_text(encoding="utf-8"))
        self.assertEqual(status["sites"][0]["status"], "up")
        self.assertNotIn("issueNumber", status["sites"][0])


if __name__ == "__main__":
    unittest.main()
