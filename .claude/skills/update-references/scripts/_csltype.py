"""CSL types for imported records.

The importers used to write ``type: article`` for every record. pandoc writes a
CSL ``article`` as BibTeX ``@misc`` and drops its ``container-title``, so a
journal or conference paper printed without its venue (GH-475). These helpers
map what a source says about a work onto the CSL type that keeps the venue.

``article`` stays the answer for preprints and for anything a source does not
classify: it is the honest CSL type when the venue is unknown.
"""

# OpenAlex work types that fix the CSL type on their own.
_OPENALEX_WORK = {
    "book-chapter": "chapter",
    "book": "book",
    "monograph": "book",
    "edited-book": "book",
    "reference-book": "book",
    "report": "report",
    "dissertation": "thesis",
    "dataset": "dataset",
    "preprint": "article",
    "standard": "standard",
}

# OpenAlex primary-source types, for the work types (article, review, ...)
# whose CSL type depends on where they appeared.
_OPENALEX_SOURCE = {
    "journal": "article-journal",
    "conference": "paper-conference",
    "repository": "article",
}

# Semantic Scholar publicationTypes, in the order they are tried.
_S2_TYPES = (
    ("Conference", "paper-conference"),
    ("JournalArticle", "article-journal"),
    ("BookSection", "chapter"),
    ("Book", "book"),
)


def _preprint_venue(venue):
    return (venue or "").strip().lower().startswith("arxiv")


def openalex_csl_type(work_type, source_type, venue=""):
    """The CSL type for an OpenAlex work, given its type and its primary source's."""
    if _preprint_venue(venue):
        return "article"
    if work_type in _OPENALEX_WORK:
        return _OPENALEX_WORK[work_type]
    return _OPENALEX_SOURCE.get(source_type or "", "article")


def s2_csl_type(publication_types, venue=""):
    """The CSL type for a Semantic Scholar paper, given its publicationTypes."""
    if _preprint_venue(venue):
        return "article"
    kinds = set(publication_types or [])
    for name, csl in _S2_TYPES:
        if name in kinds:
            return csl
    return "article"


def upgrade_type(existing, mapped):
    """Set a merged entry's type: a generic article takes a specific mapping;
    any other existing type is kept. Returns True when the entry changed."""
    current = existing.get("type")
    if mapped and mapped != "article" and current in (None, "", "article"):
        existing["type"] = mapped
        return True
    return False
