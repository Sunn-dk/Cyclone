"""Regression checks for scrolling past selectable statistics to an export button."""
import tempfile, unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from run_regressions import PKG, tap


class UiHelperTests(unittest.TestCase):
    def test_export_reached_with_edge_swipe_after_one_stale_dump(self):
        calls=[]
        container={"scrollable":"true","bounds":"[0,100][1080,2200]"}
        button={"resource-id":PKG+":id/btnExport","bounds":"[80,1700][1000,1840]"}
        with tempfile.TemporaryDirectory() as folder:
            runner=SimpleNamespace(out=Path(folder),adbcall=lambda *args:calls.append(args))
            with patch('run_regressions.ui',side_effect=[[container],[container],[container,button]]):
                tap(runner,'btnExport',scroll=True)
        swipes=[args for args in calls if args[2]=='swipe']
        self.assertEqual(len(swipes),2)
        self.assertTrue(all(args[3]==10 and args[5]==10 for args in swipes))
        self.assertEqual(calls[-1],('shell','input','tap',540,1770))

    def test_missing_button_fails_and_keeps_ui_evidence(self):
        with tempfile.TemporaryDirectory() as folder:
            runner=SimpleNamespace(out=Path(folder),adbcall=lambda *args:None)
            with patch('run_regressions.ui',return_value=[{"scrollable":"true","bounds":"[0,100][1080,2200]"}]):
                with self.assertRaisesRegex(RuntimeError,'Control not visible'):
                    tap(runner,'btnExport',scroll=True)
            self.assertTrue((Path(folder)/'unreachable-btnExport.json').exists())


if __name__=='__main__':
    unittest.main()
