#!/usr/bin/env python3
"""Offline tests for say_transcription.py (GH-502)."""
import os
import sys
import unittest

SK = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, SK)
import say_transcription as st  # noqa: E402

SRD = """# SRD

## Goals

Goals prose that is not a say and should never be read as one by the script.

## Content

Open on what the surveys report, then the thesis. The surveys' fact: multi-agent applications are built on large models, several agents wired into one workflow. The model is probabilistic: the same input can produce a different run. Then the thesis: such an application can be written down as data, a set of specifications; a checker verifies the set before anything runs, and one fixed engine executes them. Attribute the bound to the checker, which refuses a specification that leaves an outcome unhandled, and to the engine, which holds every run to the declared transitions.

Raise the bar from capable to dependable in a second paragraph that has nothing to do with the first.

## Links

Links prose that is not a say either.
"""

TRANSCRIBED = """# Introduction

Multi-agent applications built on large models wire several agents into one workflow. The model is probabilistic: the same input can produce a different run. We argue that such an application can be written down as data, a set of specifications. A checker verifies the set before anything runs, and one fixed engine executes them. The bound comes from the checker, which refuses a specification that leaves an outcome unhandled, and from the engine, which holds every run to the declared transitions.
"""

REWORKED = """# Introduction

Declared as checked data, an agentic application keeps its runs bounded even though each reply is a guess. The engine permits only transitions someone wrote down, and loading fails whenever any outcome lacks its handler. Teams already compose several such agents per workflow, as surveys of the field report. Their guesses differ run to run, which is exactly why the bound has to come from outside them.
"""


class SayTranscriptionTest(unittest.TestCase):
    def test_only_the_content_section_holds_says(self):
        found = st.says(SRD)
        self.assertEqual(len(found), 2)
        self.assertTrue(found[0].startswith("Open on what the surveys report"))

    def test_a_clause_by_clause_paragraph_is_flagged(self):
        found = st.flags(TRANSCRIBED, [("srd-1.md", SRD)])
        self.assertEqual(len(found), 1)
        self.assertEqual((found[0]["srd"], found[0]["say"]), ("srd-1.md", 1))
        self.assertGreaterEqual(found[0]["matched"], 4)

    def test_the_same_say_reworded_and_reordered_is_not_flagged(self):
        self.assertEqual(st.flags(REWORKED, [("srd-1.md", SRD)]), [])

    def test_in_order_is_the_longest_non_decreasing_run(self):
        self.assertEqual(st._longest_in_order([0, 2, 1, 3, 4]), 4)
        self.assertEqual(st._longest_in_order([4, 3, 2, 1]), 1)
        self.assertEqual(st._longest_in_order([]), 0)

    def test_a_short_paragraph_is_never_flagged(self):
        two = "# T\n\nThe model is probabilistic: the same input can produce a different run. One fixed engine executes them.\n"
        self.assertEqual(st.flags(two, [("srd-1.md", SRD)]), [])


if __name__ == "__main__":
    unittest.main()
