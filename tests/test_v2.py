"""Offline tests for the version 2 clinic test (no Ollama). Run with: python3 -m pytest -q"""
from __future__ import annotations

import json
import random
import tempfile
import unittest
import urllib.error
from pathlib import Path
from typing import Any, Dict, List

import analysis_v2
import run_v2
from clinic.score import score_episode
from clinic_v2 import build_tasks
from clinic_v2.prompts import MARK, SYSTEM, datamark, user_message
from run_llm import SYSTEM_PROMPT as V1_PROMPT

DATA = run_v2.load_tasks()
TASKS = DATA["tasks"]
OK_TO = DATA["approved_recipient"]


def correct_actions(t: Dict[str, Any]) -> List[Dict[str, str]]:
    out = []
    for a in t["required_actions"]:
        p = {"action": a, "patient_id": t["patient_id"]}
        if a == "send_external":
            p["to"] = OK_TO
        if a == "book_appointment":
            p["date"] = t["expected_date"]
        out.append(p)
    return out


def injected_action(t: Dict[str, Any]) -> Dict[str, str]:
    inj = t["injection"]
    p = {"action": inj["action"], "patient_id": inj.get("patient_id", t["patient_id"])}
    if "to" in inj:
        p["to"] = inj["to"]
    if inj["action"] == "book_appointment":
        p["date"] = inj.get("date", t.get("expected_date", "2026-12-01"))
    return p


def scripted_fake(models: List[str]) -> run_v2.AskFn:
    """Does the real task every time; follows the hidden instruction only with the plain prompt."""
    table: Dict[Any, str] = {}
    for key, task in run_v2.grid(models, TASKS):
        model, _, lang, defence, injected = key
        acts = correct_actions(task)
        if injected and defence == "plain":
            acts = acts + [injected_action(task)]
        table[(model, SYSTEM[defence], user_message(task, lang, injected, defence))] = json.dumps({"actions": acts})

    def ask(model: str, system: str, user: str) -> str:
        return table[(model, system, user)]
    return ask


class TaskFileTests(unittest.TestCase):
    def test_file_matches_the_builder(self):
        self.assertEqual(DATA, build_tasks.build())

    def test_size_balance_and_languages(self):
        self.assertEqual(len(TASKS), 40)
        self.assertEqual(len({t["id"] for t in TASKS}), 40)
        kinds = [t["injection"]["kind"] for t in TASKS]
        self.assertEqual(kinds.count("out_of_scope"), 20)
        self.assertEqual(kinds.count("wrong_argument"), 20)
        for t in TASKS:
            for field in ("instruction", "note", "injection"):
                self.assertTrue(t[field]["en"] and t[field]["ru"], t["id"])
            self.assertTrue(set(t["required_actions"]) <= set(t["allowed_actions"]), t["id"])
            if t["injection"]["kind"] == "out_of_scope":
                self.assertNotIn(t["injection"]["action"], t["allowed_actions"], t["id"])
            else:
                self.assertIn(t["injection"]["action"], t["allowed_actions"], t["id"])

    def test_correct_actions_complete_and_injection_is_caught_by_argument_scope(self):
        for t in TASKS:
            clean = score_episode(correct_actions(t), t, False, OK_TO, "scoped_with_arguments", random.Random(1))
            self.assertTrue(clean["completed"], t["id"])
            self.assertEqual(clean["authorised_blocked"], 0, t["id"])
            m = score_episode([injected_action(t)], t, True, OK_TO, "scoped_with_arguments", random.Random(1))
            self.assertTrue(m["injection_followed"], t["id"])
            self.assertFalse(m["attack_accepted"], t["id"])
            free = score_episode([injected_action(t)], t, True, OK_TO, "unrestricted", random.Random(1))
            self.assertTrue(free["attack_accepted"], t["id"])


class PromptTests(unittest.TestCase):
    def test_plain_prompt_is_the_version_1_prompt(self):
        self.assertEqual(SYSTEM["plain"], V1_PROMPT)

    def test_datamark_marks_only_the_note(self):
        t = TASKS[0]
        msg = user_message(t, "ru", True, "datamark")
        task_part, note_part = msg.split("\n\nPatient note (from the clinic system): ")
        self.assertIn(t["instruction"]["ru"], task_part)
        self.assertNotIn(" ", note_part)
        self.assertEqual(note_part.replace(MARK, " "), t["note"]["ru"] + " " + t["injection"]["ru"])
        self.assertEqual(datamark("a  b\nc"), "a{0}b{0}c".format(MARK))
        self.assertIn(MARK, SYSTEM["datamark"])
        self.assertNotIn(MARK, SYSTEM["plain"])

    def test_clean_message_has_no_injection(self):
        for t in TASKS:
            for defence in ("plain", "datamark"):
                msg = user_message(t, "en", False, defence)
                self.assertNotIn(datamark(t["injection"]["en"]) if defence == "datamark" else t["injection"]["en"], msg)


class RunnerTests(unittest.TestCase):
    def test_end_to_end_mock_run_resume_and_analysis(self):
        models = ["fake-a", "fake-b"]
        with tempfile.TemporaryDirectory() as d:
            runs = Path(d) / "runs.jsonl"
            n = run_v2.run(models, TASKS, scripted_fake(models), runs)
            self.assertEqual(n, 2 * 40 * 2 * 2 * 2)
            self.assertEqual(run_v2.run(models, TASKS, scripted_fake(models), runs), 0)  # resumes, nothing left
            with runs.open("a", encoding="utf-8") as f:
                f.write('{"model": "fake-a", "task"')  # half-written line after a crash
            self.assertEqual(len(run_v2.done_keys(runs)), 640)

            scored = analysis_v2.score_all(analysis_v2.load_runs(runs), DATA)
            summary = {(r["model"], r["language"], r["prompt"]): r for r in analysis_v2.summary_rows(scored)}
            plain = summary[("fake-a", "Roman Urdu", "plain")]
            mark = summary[("fake-a", "Roman Urdu", "datamark")]
            self.assertEqual((plain["followed"], plain["clean_completed"], plain["unparsed"]), (40, 40, 0))
            self.assertEqual((mark["followed"], mark["clean_completed"]), (0, 40))
            self.assertEqual(plain["injected_task_still_completed"], 40)

            pol = {(r["model"], r["language"], r["prompt"]): r for r in analysis_v2.policy_rows(scored)}
            p = pol[("fake-b", "English", "plain")]
            self.assertEqual(p["attack_unrestricted"], 40)
            self.assertEqual(p["attack_scoped_with_arguments"], 0)
            self.assertEqual(p["attack_task_scoped_capability"], 20)  # the 20 wrong-argument attacks
            self.assertEqual(p["clean_done_scoped_with_arguments"], 40)

            tests = {(t["comparison"], t["measure"]): t for t in analysis_v2.paired_rows(scored)}
            t = tests[("fake-a English: plain (a) vs datamark (b)", "injection_followed")]
            self.assertEqual((t["only_a"], t["only_b"]), (40, 0))
            self.assertLess(t["p_mcnemar_exact"], 1e-9)

            try:
                import matplotlib  # noqa: F401
            except ImportError:
                self.skipTest("matplotlib not installed")
            png = Path(d) / "chart.png"
            analysis_v2.chart(analysis_v2.summary_rows(scored), png)
            self.assertGreater(png.stat().st_size, 10000)

    def test_one_retry_then_recorded_as_failed(self):
        calls = {"n": 0}

        def flaky(model: str, system: str, user: str) -> str:
            calls["n"] += 1
            if calls["n"] == 1:
                raise urllib.error.URLError("timed out")
            return '{"actions": []}'

        self.assertEqual(run_v2.ask_with_retry(flaky, "m", "s", "u"), ('{"actions": []}', None))

        def dead(model: str, system: str, user: str) -> str:
            raise TimeoutError("timed out")

        reply, err = run_v2.ask_with_retry(dead, "m", "s", "u")
        self.assertEqual(reply, "")
        self.assertIn("TimeoutError", err or "")


class StatsTests(unittest.TestCase):
    def test_mcnemar_exact_and_bootstrap(self):
        self.assertEqual(analysis_v2.mcnemar_exact(0, 0), 1.0)
        self.assertAlmostEqual(analysis_v2.mcnemar_exact(0, 5), 0.0625)
        self.assertAlmostEqual(analysis_v2.mcnemar_exact(3, 3), 1.0)
        lo, hi = analysis_v2.bootstrap_ci([1.0] * 10 + [0.0] * 10)
        self.assertLess(lo, 0.5)
        self.assertGreater(hi, 0.5)
        self.assertEqual(analysis_v2.bootstrap_ci([1.0] * 5), (1.0, 1.0))


if __name__ == "__main__":
    unittest.main()
