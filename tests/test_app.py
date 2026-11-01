"""The local web app (app/server.py): it only ever runs the pack's own scripts with checked inputs."""

import json
import os
import tempfile
import unittest

from _load import ROOT
import importlib.util

spec = importlib.util.spec_from_file_location("nse_app", os.path.join(ROOT, "app", "server.py"))
app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app)


class Commands(unittest.TestCase):
    def test_each_step_runs_only_pack_scripts(self):
        bodies = {"scan": {"symbols": "ICICIBANK, M&M"}, "research": {"symbol": "TCS"}, "plan": {"symbol": "TCS.BO"},
                  "size": {"budget": "50000"}, "check": {"refresh": True}, "ticket": {}, "place": {"confirm": "yes"},
                  "track": {}}
        for step, body in bodies.items():
            for cmd in app.commands(step, dict(body, now="2026-10-30 09:40")):
                self.assertEqual(cmd[1:4], ["-I", "-X", "utf8"])
                self.assertTrue(cmd[4].startswith(ROOT) and cmd[4].endswith(".py"), cmd)
        scan = app.commands("scan", {"symbols": "ICICIBANK, M&M"})[0]
        self.assertEqual(scan[scan.index("--symbols") + 1], "ICICIBANK,M&M")
        self.assertIn(app.NIFTY50, app.commands("scan", {})[0])
        self.assertEqual(len(app.commands("scan", {"all": True})), 2)          # universe first

    def test_bad_input_is_refused(self):
        for step, body in (("research", {"symbol": "RELIANCE; rm -rf /"}), ("plan", {"symbol": "--write"}),
                           ("size", {"budget": "lots"}), ("size", {"budget": "10"}), ("place", {}),
                           ("scan", {"now": "tomorrow"}), ("nope", {})):
            with self.assertRaises(app.BadInput, msg=step):
                app.commands(step, body)

    def test_settings_keep_other_keys_and_stay_paper(self):
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "trader"))
            with open(os.path.join(d, "trader", "config.json"), "w") as fh:
                json.dump({"blocked": ["YESBANK"], "paper": False}, fh)
            cfg = app.save_settings(d, {"budget": "75000", "max_loss_per_trade_usd": "400"})
            self.assertEqual((cfg["budget"], cfg["max_loss_per_trade_usd"], cfg["blocked"], cfg["paper"]),
                             (75000.0, 400.0, ["YESBANK"], True))
            with self.assertRaises(app.BadInput):
                app.save_settings(d, {"budget": "-5"})


if __name__ == "__main__":
    unittest.main()
