#!/usr/bin/env python3
"""Flag paragraphs that transcribe their SRD say clause by clause (GH-502).

A paragraph drafted from a contract can end up as the contract's clauses in
order, one sentence each. It then discharges the contract instead of building
one point, and the contract freezes the split: a critic briefed that the SRD
is the drafting contract does not propose a restructure that breaks a say,
and every narrow fix mirrored back into the say makes the transcription
tighter. The Loom Introduction's opening was its say's five clauses in order
(petar-djukic/agent-skills#498).

For each prose paragraph of three or more sentences in the chapter, this
script matches each sentence to its closest clause of each say — a prose
paragraph of the SRD, taken from its `## Content` section when it has one —
by the share of the sentence's content words the clause carries. A paragraph
is flagged when most of its sentences match clauses of one say, in the say's
order. A flag is a prompt to revise the say with the paragraph, not a defect
in itself.

    say_transcription.py chapter.md docs/srd/srd-1-introduction.md [more.md ...]
"""
import argparse
import bisect
import os
import re
import sys

HERE = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, os.path.normpath(os.path.join(HERE, "..", "..", "..", "scripts")))
import md_paragraphs  # noqa: E402

MATCH = 0.5          # a sentence matches a clause carrying this share of its words
FLAG_SHARE = 0.7     # of the paragraph's sentences, matched in order
MIN_SENTENCES = 3
MIN_WORDS = 3

CITE = re.compile(r"\[@[^\]]*\]|\\\w+\{[^}]*\}|`[^`]*`")
SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[A-Z\\`\[(\"'])")
CLAUSE_END = re.compile(r"(?<=[.!?;:])\s+|\s+—\s+")
WORD = re.compile(r"[A-Za-z][A-Za-z'-]{3,}")
STOP = set("""
also among another because been before being between both cannot could does
each either every from have here into itself just more most much must never
only other over same should since some such than that their them then there
these they this those through under until upon very were what when where
whether which while whom whose will with within without would your about
above after again against across along already although always
""".split())


def _clean(text):
    return " ".join(CITE.sub(" ", text).split())


def words(text):
    return {w.lower().strip("'-") for w in WORD.findall(_clean(text))} - STOP


def sentences(text):
    return [s for s in SENTENCE_END.split(_clean(text)) if s.strip()]


def says(srd_text):
    """The say paragraphs of one SRD: its `## Content` section when present."""
    m = re.search(r"^## Content\s*$(.*?)(?=^## |\Z)", srd_text, re.M | re.S)
    body = m.group(1) if m else srd_text
    return [p[2] for p in md_paragraphs.paragraphs(body, 8)]


def transcription(paragraph, say):
    """(matched, total, clause indices) for one paragraph against one say."""
    clauses = [words(c) for c in CLAUSE_END.split(_clean(say)) if words(c)]
    hits = []
    sents = sentences(paragraph)
    for s in sents:
        w = words(s)
        if len(w) < MIN_WORDS or not clauses:
            continue
        score, idx = max((len(w & c) / len(w), i) for i, c in enumerate(clauses))
        if score >= MATCH:
            hits.append(idx)
    return _longest_in_order(hits), len(sents), hits


def _longest_in_order(seq):
    """Length of the longest non-decreasing subsequence: the sentences that
    follow the say's clause order, whatever else sits between them."""
    tails = []
    for x in seq:
        i = bisect.bisect_right(tails, x)
        tails[i:i + 1] = [x]
    return len(tails)


def flags(chapter_text, srd_texts):
    found = []
    pool = [(name, n, say) for name, text in srd_texts
            for n, say in enumerate(says(text), 1)]
    for start, _end, par in md_paragraphs.paragraphs(chapter_text, 12):
        if len(sentences(par)) < MIN_SENTENCES:
            continue
        best = None
        for name, n, say in pool:
            matched, total, hits = transcription(par, say)
            if matched >= MIN_SENTENCES and matched / total >= FLAG_SHARE:
                if not best or matched > best[0]:
                    best = (matched, total, name, n, say)
        if best:
            found.append({"line": start, "opens": " ".join(par.split()[:8]),
                          "matched": best[0], "sentences": best[1],
                          "srd": best[2], "say": best[3], "say_text": best[4]})
    return found


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("chapter")
    ap.add_argument("srds", nargs="+")
    a = ap.parse_args(argv)
    with open(a.chapter, encoding="utf-8") as f:
        chapter = f.read()
    srds = []
    for path in a.srds:
        with open(path, encoding="utf-8") as f:
            srds.append((path, f.read()))
    found = flags(chapter, srds)
    for x in found:
        print(f"{a.chapter}:{x['line']}: \"{x['opens']} ...\" — {x['matched']} of "
              f"{x['sentences']} sentences follow {x['srd']} say {x['say']} in order; "
              f"revise the say with any restructure")
    print(f"say_transcription: {len(found)} paragraph(s) flagged")
    return 0


if __name__ == "__main__":
    sys.exit(main())
