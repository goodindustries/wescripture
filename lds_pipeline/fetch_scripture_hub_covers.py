#!/usr/bin/env python3
"""
Download standard-works cover JPEGs from the same Church image service used on
https://www.churchofjesuschrist.org/study/scriptures (tile art next to each work link).

Image IDs were resolved from the live page (anchor href → nested img src); re-verify with
Puppeteer against /study/scriptures if tiles change.

Run from repo root:
  python3 lds_pipeline/fetch_scripture_hub_covers.py
"""

from __future__ import annotations

import urllib.request
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
OUT_DIR = _REPO / "library" / "assets" / "corpus" / "covers"

# Church /imgs/{assetKey}/full/!{maxWidth},/0/default — max width ~800 for crisp tiles.
_WIDTH = 800
_BASE = "https://www.churchofjesuschrist.org/imgs"

# Keys: WeScripture testament codes. Values: Gospel Library scripture cover asset keys (from study hub).
COVER_KEYS: dict[str, str] = {
    "OT": "g5gickahk6wnygbo4y5t2sgqv5590yxhjzs9oyvj",  # /study/scriptures/ot
    "NT": "5lrvp4tmkx1kgj2zqi1rkjaayjmj6d3dwtibly7t",  # /study/scriptures/nt
    "BOM": "pezq51mqdlsfg6znj28seegave1osc6jg4d48ewb",  # /study/scriptures/bofm
    "DC": "lbphummygbskmauexvxd46t16oc434dcpdzbdxzn",  # /study/scriptures/dc-testament
    "PGP": "cxfe5k79jt3p7u4m79ccka8ovn4609hkwzs0y1iw",  # /study/scriptures/pgp
}

OUT_FILES: dict[str, str] = {
    "OT": "church_ot.jpg",
    "NT": "church_nt.jpg",
    "BOM": "church_bom.jpg",
    "DC": "church_dc.jpg",
    "PGP": "church_pgp.jpg",
}


def cover_url(asset_key: str) -> str:
    # "!800," encoded as %21800%2C per Church CDN
    return f"{_BASE}/{asset_key}/full/%21{_WIDTH}%2C/0/default"


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 WeScripture-cover-sync/1.0"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read()


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for testament, key in COVER_KEYS.items():
        url = cover_url(key)
        name = OUT_FILES[testament]
        path = OUT_DIR / name
        data = fetch(url)
        path.write_bytes(data)
        print(f"  {name}  ({len(data)} bytes)  <- {url}")


if __name__ == "__main__":
    main()
