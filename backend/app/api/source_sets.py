from __future__ import annotations

from fastapi import APIRouter

from app.config import load_source_sets
from app.schemas import SourceSetOut

router = APIRouter(prefix="/api/source-sets", tags=["source-sets"])


@router.get("", response_model=list[SourceSetOut])
def list_source_sets() -> list[SourceSetOut]:
    out: list[SourceSetOut] = []
    for key, sset in load_source_sets().items():
        global_sources = [
            {
                "key": s.get("key"),
                "adapter": s.get("adapter"),
                "market": s.get("market"),
                "credibility": s.get("credibility"),
                # URLs are administrator config; we surface counts/keys, not raw URLs.
                "url_count": len(s.get("urls", [])),
            }
            for s in sset.get("global_sources", [])
        ]
        out.append(
            SourceSetOut(
                key=key,
                category=sset.get("category"),
                global_source_count=len(sset.get("global_sources", [])),
                swiss_retailer_count=len(sset.get("swiss_retailers", [])),
                global_sources=global_sources,
                swiss_retailers=sset.get("swiss_retailers", []),
            )
        )
    return out
