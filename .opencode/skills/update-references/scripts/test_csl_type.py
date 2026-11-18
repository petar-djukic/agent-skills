#!/usr/bin/env python3
"""Tests for _csltype, the CSL type an imported record gets. Run:

    python3 test_csl_type.py

No network. Covers GH-475: every OpenAlex and Semantic Scholar record used to
land as the generic CSL type article, which pandoc writes as @misc without the
venue, so journal and conference papers printed without where they appeared.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from _csltype import openalex_csl_type, s2_csl_type, upgrade_type  # noqa: E402

FAILURES = []


def check(name, ok, detail=""):
    print(("ok   " if ok else "FAIL ") + name + ("" if ok else "  " + detail))
    if not ok:
        FAILURES.append(name)


def main():
    cases = [
        ("a journal article", ("article", "journal", "Science of Computer Programming"), "article-journal"),
        ("a proceedings paper", ("article", "conference", "SIGMOD"), "paper-conference"),
        ("a book chapter", ("book-chapter", "book series", "Lecture Notes in Computer Science"), "chapter"),
        ("a book", ("book", None, ""), "book"),
        ("a report", ("report", None, ""), "report"),
        ("a dissertation", ("dissertation", "repository", ""), "thesis"),
        ("a preprint by work type", ("preprint", "repository", "arXiv (Cornell University)"), "article"),
        ("an arXiv venue overrides a journal source", ("article", "journal", "arXiv preprint arXiv:2308.00352"), "article"),
        ("a repository source", ("article", "repository", "Zenodo"), "article"),
        ("an unclassified work", ("other", None, ""), "article"),
    ]
    for name, args, want in cases:
        got = openalex_csl_type(*args)
        check("OpenAlex: " + name, got == want, "got %r, want %r" % (got, want))

    s2 = [
        ("a conference paper", (["Conference"], "ICLR"), "paper-conference"),
        ("a journal article", (["JournalArticle", "Review"], "IEEE TSE"), "article-journal"),
        ("a book section", (["BookSection"], ""), "chapter"),
        ("an arXiv paper typed as a journal article", (["JournalArticle"], "arXiv.org"), "article"),
        ("no types", (None, ""), "article"),
    ]
    for name, args, want in s2:
        got = s2_csl_type(*args)
        check("Semantic Scholar: " + name, got == want, "got %r, want %r" % (got, want))

    generic = {"type": "article"}
    check("a generic article is upgraded", upgrade_type(generic, "article-journal")
          and generic["type"] == "article-journal", repr(generic))
    typed = {"type": "book"}
    check("a specific type is kept", not upgrade_type(typed, "article-journal")
          and typed["type"] == "book", repr(typed))
    untouched = {"type": "article"}
    check("a generic mapping changes nothing", not upgrade_type(untouched, "article")
          and untouched["type"] == "article", repr(untouched))
    missing = {}
    check("a missing type takes the mapping", upgrade_type(missing, "paper-conference")
          and missing["type"] == "paper-conference", repr(missing))

    print()
    if FAILURES:
        print("%d failed: %s" % (len(FAILURES), ", ".join(FAILURES)))
        return 1
    print("all csl-type tests passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
