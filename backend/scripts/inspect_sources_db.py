"""Show how LocalSourcesRepository reads the sources database.

    python -m scripts.inspect_sources_db [path] ["arabic text to search"]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from app.config import get_settings
from app.repositories.local_sources import LocalSourcesRepository


def main() -> None:
    settings = get_settings()
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else settings.sources_db_path
    repo = LocalSourcesRepository(path, min_match_chars=settings.min_match_chars)
    print(json.dumps(repo.stats(), ensure_ascii=False, indent=2, default=str))
    if len(sys.argv) > 2:
        query = sys.argv[2]
        for label, results in (("quran", repo.search_quran(query)), ("hadith", repo.search_hadith(query))):
            for c in results:
                print(f"{label}: {c.score:.3f} {c.match_type} {c.entry.reference}")


if __name__ == "__main__":
    main()
