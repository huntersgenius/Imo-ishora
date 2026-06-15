"""Curated, generated data that ships with the backend.

``dictionary.json`` is produced by ``scripts/build_dictionary.py`` from
``r2_video_inventory.csv``. Do not hand-edit it; regenerate it instead.
"""

from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent
DICTIONARY_PATH = DATA_DIR / "dictionary.json"

__all__ = ["DATA_DIR", "DICTIONARY_PATH"]
