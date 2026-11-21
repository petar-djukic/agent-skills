#!/usr/bin/env python3
"""Offline tests for claim_loss.py (GH-501)."""
import os
import subprocess
import sys
import tempfile
import unittest

SK = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, SK)
import claim_loss  # noqa: E402

STEADY = ("The second paragraph says one plain thing about the engine and keeps "
          "saying it in the same words across both versions of the article.")
NEW = ("A wholly new paragraph about the deployment arrives in the current version "
       "and has no counterpart in the baseline at all.")
BASELINE = f"""# Introduction

Multi-agent applications built on Large AI Models wire several agents into one workflow. We argue that declaring such an application as data keeps its behaviour bounded, readable, and checkable before it runs, despite the models inside it. The checker and the engine produce the bound.

{STEADY}
"""
CURRENT = f"""# Introduction

Multi-agent applications built on Large AI Models wire several agents into one workflow. We argue that such an application can be written down as data. A checker verifies the set before anything runs, so its behaviour stays bounded despite the models inside it. The bound comes from the checker and from the engine.

{STEADY}

{NEW}
"""


class ClaimLossTest(unittest.TestCase):
    def test_a_split_thesis_pairs_and_unchanged_paragraphs_do_not(self):
        base = claim_loss.prose(BASELINE, 12)
        cur = claim_loss.prose(CURRENT, 12)
        pairs, orphans = claim_loss.align(base, cur)
        self.assertEqual(pairs, [(0, 0)])
        self.assertEqual(orphans, [])
        d = claim_loss.compare(base[0], cur[0])
        self.assertEqual((d["baseline_sentences"], d["current_sentences"]), (3, 4))

    def test_the_split_thesis_is_reported_as_spread_with_its_lost_words(self):
        base = claim_loss.prose(BASELINE, 12)
        cur = claim_loss.prose(CURRENT, 12)
        d = claim_loss.compare(base[0], cur[0])
        self.assertEqual([s["sentence"] for s in d["spread"]], [2])
        self.assertEqual(d["spread"][0]["into"], [2, 3])
        lost = {s["sentence"]: s["words"] for s in d["lost"]}
        self.assertIn("declaring", lost[2])
        self.assertIn("checkable", lost[2])

    def test_the_loom_opening_split_is_reported(self):
        """The real case: the Loom Introduction's opening, 2026-11-08 against
        2026-11-20 (petar-djukic/agent-skills#498)."""
        before = (
            "Multi-agent applications built on Large AI Models (LAMs) wire several agents, "
            "each with a defined job, into one workflow. The LAM inside each agent is "
            "probabilistic, so the same input can produce a different run, and no "
            "enumeration of cases covers what a LAM may reply. We argue that declaring such "
            "an application as data, as specifications a checker verifies whole and a fixed "
            "engine runs, keeps its behaviour bounded, readable, and checkable before it "
            "runs, despite the LAMs inside it. The checker and the engine produce the bound; "
            "the language is the form that makes both possible.")
        after = (
            "Multi-agent applications built on Large AI Models (LAMs) wire several agents, "
            "each with a defined job, into one workflow. The LAM inside each agent is "
            "probabilistic: the same input can produce a different run, and the set of "
            "replies it may give cannot be listed in advance. We argue that such an "
            "application can be written down as data: a set of specifications, one per "
            "agent and one for the application that joins them. A checker verifies the set "
            "as a whole before anything runs, and one fixed engine runs them, so the "
            "application is read and checked before it is deployed and its behaviour in "
            "operation stays bounded despite the LAMs inside it. The bound comes from the "
            "checker, which refuses a specification that leaves a declared outcome "
            "unhandled, and from the engine, which holds every run to the transitions the "
            "specification declares.")
        d = claim_loss.compare(before, after)
        self.assertIn({"sentence": 3, "into": [3, 4]},
                      [{k: s[k] for k in ("sentence", "into")} for s in d["spread"]])
        lost = {s["sentence"]: s["words"] for s in d["lost"]}
        self.assertTrue({"declaring", "keeps", "checkable"} <= set(lost[3]))

    def test_a_sentence_kept_whole_is_not_spread(self):
        same = "The engine holds every run to the transitions the specification declares."
        d = claim_loss.compare(same + " It adds nothing else here.",
                               "A new opening sentence comes first now. " + same)
        self.assertEqual(d["spread"], [])
        self.assertEqual(d["lost"], [])

    def test_the_sheet_carries_both_versions_and_the_instruction(self):
        base = claim_loss.prose(BASELINE, 12)
        cur = claim_loss.prose(CURRENT, 12)
        pairs, orphans = claim_loss.align(base, cur)
        sheet = claim_loss.render("cur.md", "base.md", base, cur, pairs, orphans)
        self.assertIn("Scope: paragraph", sheet)
        self.assertIn("### Baseline", sheet)
        self.assertIn("keeps its behaviour bounded", sheet)
        self.assertIn("can be written down as data", sheet)
        self.assertNotIn(STEADY, sheet)
        self.assertNotIn(NEW, sheet)

    def test_a_removed_paragraph_is_listed_as_without_counterpart(self):
        base = claim_loss.prose(BASELINE, 12)
        pairs, orphans = claim_loss.align(base, base[1:])
        self.assertEqual(pairs, [])
        self.assertEqual(orphans, [0])

    def test_a_rev_path_baseline_is_read_through_git(self):
        with tempfile.TemporaryDirectory() as t:
            run = lambda *a: subprocess.run(["git", "-C", t, *a], check=True,
                                            capture_output=True)
            run("init", "-q")
            path = os.path.join(t, "intro.md")
            with open(path, "w", encoding="utf-8") as f:
                f.write(BASELINE)
            run("add", "intro.md")
            run("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "base")
            with open(path, "w", encoding="utf-8") as f:
                f.write(CURRENT)
            out = os.path.join(t, "sheet.md")
            self.assertEqual(claim_loss.main([path, "--baseline", "HEAD:intro.md",
                                              "--out", out]), 0)
            with open(out, encoding="utf-8") as f:
                sheet = f.read()
            self.assertIn("Changed paragraphs: 1", sheet)
            self.assertIn("HEAD:intro.md", sheet)


if __name__ == "__main__":
    unittest.main()
