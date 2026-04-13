from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


LicenseType = Literal[
    "public_domain",
    "cc_by_4",
    "cc_by_sa_4",
    "cc_by_nc_4",
    "cc_by_nc_nd_4",
    "unknown",
]

IngestMode = Literal["ingest", "link_only"]


@dataclass(frozen=True)
class SourceRecord:
    id: str
    title: str
    author: str
    year: int | None
    canonical_url: str
    license_type: LicenseType
    license_url: str | None
    redistributable: bool
    ingest_mode: IngestMode
    ingest_group: str
    cache_relpath: str | None = None


def registry() -> list[SourceRecord]:
    """
    License-safe targets for ingestion/reporting.

    Policy:
    - ingest only when redistributable=True and ingest_mode='ingest'
    - link_only items may be non-redistributable (we do not cache/redistribute)
    """

    return [
        # ── Nibley (seeded via explicit CC license record; URL may change) ──
        SourceRecord(
            id="nibley_teachings_bom_wordcruncher",
            title="Teachings of the Book of Mormon (Honors class transcripts, 1988–1990)",
            author="Hugh W. Nibley",
            year=2015,
            canonical_url="https://scholarsarchive.byu.edu/wordcruncher/29",
            license_type="cc_by_4",
            license_url="https://creativecommons.org/licenses/by/4.0/",
            redistributable=True,
            ingest_mode="link_only",
            ingest_group="nibley",
            cache_relpath=None,
        ),
        # ── Truman G. Madsen (likely free-to-read; redistribution unclear → link-only) ──
        SourceRecord(
            id="madsen_joseph_smith_lectures_byu_speeches",
            title="Joseph Smith Lectures (series)",
            author="Truman G. Madsen",
            year=1978,
            canonical_url="https://speeches.byu.edu/posts/trumanmadsen/",
            license_type="unknown",
            license_url=None,
            redistributable=False,
            ingest_mode="link_only",
            ingest_group="madsen",
            cache_relpath=None,
        ),
        # ── Matthew Bowman (modern scholarship: OA depends on per-paper license) ──
        SourceRecord(
            id="bowman_corpus_unpaywall_placeholder",
            title="Matthew Bowman — open-license papers (via DOI/Unpaywall)",
            author="Matthew Bowman",
            year=None,
            canonical_url="https://unpaywall.org/",
            license_type="unknown",
            license_url=None,
            redistributable=False,
            ingest_mode="link_only",
            ingest_group="bowman",
            cache_relpath=None,
        ),
        # ── Interpreter Foundation (site states CC BY-NC-ND 4.0; redistributable but restrictive) ──
        SourceRecord(
            id="interpreter_foundation_journal",
            title="Interpreter: A Journal of Latter-day Saint Faith and Scholarship",
            author="The Interpreter Foundation",
            year=None,
            canonical_url="https://interpreterfoundation.org/journal/",
            license_type="cc_by_nc_nd_4",
            license_url="https://interpreterfoundation.org/foundation/copyrights",
            redistributable=True,
            ingest_mode="link_only",
            ingest_group="interpreter",
            cache_relpath=None,
        ),
    ]

