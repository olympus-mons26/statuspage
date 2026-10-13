import unittest

from scripts.manage_sites import apply_operation


class ManageSitesTests(unittest.TestCase):
    def setUp(self):
        self.monitors = [{
            "id": "wick",
            "name": "Wick",
            "url": "https://wick-md.surge.sh",
        }]

    def test_add_site(self):
        result = apply_operation(
            self.monitors,
            "add",
            name="Inkwell",
            url="https://inkwell-md.surge.sh",
        )
        self.assertEqual(len(result), 2)
        self.assertEqual(result[1]["name"], "Inkwell")

    def test_edit_keeps_monitor_identity(self):
        result = apply_operation(
            self.monitors,
            "edit",
            existing_url="https://wick-md.surge.sh",
            name="Wick v2",
            url="https://wick-new.surge.sh",
        )
        self.assertEqual(result[0]["id"], "wick")
        self.assertEqual(result[0]["name"], "Wick v2")
        self.assertEqual(result[0]["url"], "https://wick-new.surge.sh")

    def test_remove_site(self):
        result = apply_operation(
            self.monitors,
            "remove",
            existing_url="https://wick-md.surge.sh",
        )
        self.assertEqual(result, [])

    def test_rejects_embedded_credentials(self):
        with self.assertRaisesRegex(ValueError, "credentials"):
            apply_operation(
                self.monitors,
                "add",
                name="Private",
                url="https://user:password@example.com",
            )


if __name__ == "__main__":
    unittest.main()
