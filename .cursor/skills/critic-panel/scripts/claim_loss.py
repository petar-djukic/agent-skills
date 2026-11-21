#!/usr/bin/env python3
"""Pair each changed paragraph with its baseline version (GH-501).

A chain of narrow passes reviews the current text each time and never the text
the chain started from, so a claim one fix loses is invisible to the next. The
Loom Introduction's opening went from one thesis sentence ("declaring such an
application as data ... keeps its behaviour bounded ...") to three, the
consequence in a trailing clause, across two passes no critic compared
(petar-djukic/agent-skills#498).

This script makes the comparison readable. It aligns the prose paragraphs of
the article with those of a baseline — a file, or `rev:path` read through
`git show` — skips the ones that did not change, and writes a sheet with each
changed pair side by side, the sentence counts, each baseline sentence whose
content words no one current sentence carries but several do together (the
shape a split claim leaves), and the words a sentence lost. It judges nothing: a verdict critic reads
the sheet (critic-panel Mode A, the claim-loss leg) and reports each paragraph
whose claim, predicate, or consequence no longer sits in one place.

    claim_loss.py article.md --baseline 4bbb62b2~2:paper/01-introduction.md
    claim_loss.py article.md --baseline old/article.md --out sheet.md
"""
import argparse
import difflib
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, os.path.normpath(os.path.join(HERE, "..", "..", "..", "scripts")))
import md_paragraphs  # noqa: E402

PAIR_THRESHOLD = 0.35
CITE = re.compile(r"\[@[^\]]*\]|\\\w+\{[^}]*\}|`[^`]*`")
SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[A-Z\\`\[(\"'])")
WORD = re.compile(r"[A-Za-z][A-Za-z'-]{3,}")
STOP = set("""
also among another because been before being between both cannot could does
each either every from have here into itself just more most much must never
only other over same should since some such than that their them then there
these they this those through under until upon very were what when where
whether which while whom whose will with within without would your about
above after again against across along already although always another
""".split())


def read_baseline(spec, article):
    """A baseline path's text, or `rev:path` through git show."""
    if os.path.exists(spec):
        with open(spec, encoding="utf-8") as f:
            return f.read()
    if ":" not in spec:
        raise SystemExit(f"claim_loss: baseline {spec!r} is neither a file nor rev:path")
    repo = os.path.dirname(os.path.abspath(article)) or "."
    out = subprocess.run(["git", "-C", repo, "show", spec], capture_output=True,
                         text=True)
    if out.returncode != 0:
        raise SystemExit(f"claim_loss: git show {spec}: {out.stderr.strip()}")
    return out.stdout


def prose(text, min_words):
    return [p[2] for p in md_paragraphs.paragraphs(text, min_words)]


def _clean(text):
    return " ".join(CITE.sub(" ", text).split())


def sentences(text):
    return [s for s in SENTENCE_END.split(_clean(text)) if s.strip()]


def content_words(text):
    return {w.lower().strip("'-") for w in WORD.findall(_clean(text))} - STOP


def _ratio(a, b):
    return difflib.SequenceMatcher(None, a.lower().split(), b.lower().split()).ratio()


def align(base, cur):
    """Changed pairs as (baseline index, current index), and baseline
    paragraphs with no counterpart. Unchanged paragraphs never appear."""
    pairs, orphans = [], []
    sm = difflib.SequenceMatcher(None, [_clean(p) for p in base],
                                 [_clean(p) for p in cur], autojunk=False)
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == "equal":
            continue
        free = list(range(j1, j2))
        for i in range(i1, i2):
            scored = sorted(((_ratio(base[i], cur[j]), j) for j in free), reverse=True)
            if scored and scored[0][0] >= PAIR_THRESHOLD:
                pairs.append((i, scored[0][1]))
                free.remove(scored[0][1])
            else:
                orphans.append(i)
    return sorted(pairs, key=lambda p: p[1]), orphans


SPREAD_BEST = 0.7    # no one current sentence carries this share of its words
SPREAD_UNION = 0.6   # but two or more together do
SPREAD_PART = 0.2    # a current sentence counts toward the union at this share
MIN_WORDS = 4


def compare(b, c):
    """Per baseline sentence: where its content words went.

    A sentence whose words no one current sentence carries, but two or more
    do together, was spread — the shape a split claim leaves. Words no
    current sentence carries are lost. Both are recall aids for the critic."""
    bs, cs = sentences(b), sentences(c)
    cw = [content_words(s) for s in cs]
    spread, lost = [], []
    for n, sent in enumerate(bs, 1):
        words = content_words(sent)
        if len(words) < MIN_WORDS:
            continue
        share = [len(words & w) / len(words) for w in cw]
        parts = [j for j, s in enumerate(share, 1) if s >= SPREAD_PART]
        union = len(words & set().union(*[cw[j - 1] for j in parts])) / len(words) if parts else 0
        if share and max(share) < SPREAD_BEST and len(parts) >= 2 and union >= SPREAD_UNION:
            spread.append({"sentence": n, "into": parts, "best": max(share)})
        gone = sorted(words - set().union(*cw)) if cw else sorted(words)
        if len(gone) >= 2:
            lost.append({"sentence": n, "words": gone})
    return {"baseline_sentences": len(bs), "current_sentences": len(cs),
            "spread": spread, "lost": lost}


HEADER = """# Claim-loss sheet

Read-only. Each pair is one paragraph as it stood at the baseline and as it
stands now. For each, answer: does the current paragraph still carry the
baseline's claim, its predicate, and its consequence, in one place — its first
sentence, or one sentence it opens on? Report each paragraph where it does not
as a verdict finding with `Scope: paragraph`, its `Passage` the current
paragraph's first sentence. The word lists are recall aids, not verdicts: a
word can leave a paragraph because a fix was right to cut it.

Baseline: {baseline}
Article: {article}
Changed paragraphs: {n}
"""


def render(article, baseline, base, cur, pairs, orphans):
    out = [HEADER.format(baseline=baseline, article=article, n=len(pairs))]
    for k, (i, j) in enumerate(pairs, 1):
        d = compare(base[i], cur[j])
        out += [f"## Pair {k} (baseline paragraph {i + 1}, current paragraph {j + 1})", "",
                f"Sentences: {d['baseline_sentences']} at the baseline, "
                f"{d['current_sentences']} now", ""]
        for s in d["spread"]:
            out += [f"- Spread: baseline sentence {s['sentence']} is now carried by current "
                    f"sentences {', '.join(map(str, s['into']))}; the best one holds "
                    f"{s['best']:.0%} of its words."]
        for s in d["lost"]:
            out += [f"- Lost from baseline sentence {s['sentence']}: {', '.join(s['words'])}"]
        if not d["spread"] and not d["lost"]:
            out += ["- No sentence spread and no words lost."]
        out += ["", "### Baseline", "", base[i], "", "### Current", "", cur[j], ""]
    if orphans:
        out += ["## Baseline paragraphs with no counterpart", ""]
        for i in orphans:
            out += [f"- paragraph {i + 1}: {sentences(base[i])[0][:160]}"]
        out += [""]
    return "\n".join(out)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("article")
    ap.add_argument("--baseline", required=True, help="a file, or rev:path for git show")
    ap.add_argument("--out", help="default <stem>.claim-loss.md")
    ap.add_argument("--min-words", type=int, default=12)
    a = ap.parse_args(argv)
    with open(a.article, encoding="utf-8") as f:
        cur = prose(f.read(), a.min_words)
    base = prose(read_baseline(a.baseline, a.article), a.min_words)
    pairs, orphans = align(base, cur)
    out = a.out or os.path.splitext(a.article)[0] + ".claim-loss.md"
    with open(out, "w", encoding="utf-8") as f:
        f.write(render(a.article, a.baseline, base, cur, pairs, orphans))
    print(f"claim_loss: {len(pairs)} changed paragraph(s), "
          f"{len(orphans)} with no counterpart -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
