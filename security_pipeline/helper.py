# ---------------------------------------------------------------------------#
#                       HELPERS (MASKING & REPLACEMENT)                       #
# ---------------------------------------------------------------------------#
import hashlib
import re
from typing import Dict
import uuid


def _hash_mask(value: str) -> str:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
    return f"<HASH_{digest[:10]}>"


def _stable_uuid(seed: str, prefix: str) -> str:
    ns_uuid = uuid.uuid5(uuid.NAMESPACE_OID, seed)
    return f"{prefix}_{str(ns_uuid)[:8]}"


def _multi_replace(text: str, replacements: Dict[str, str]) -> str:
    """
    Safe multi-token replacement with longest-match-first strategy.
    """
    if not replacements:
        return text
    # Sort by descending length to avoid sub-string collisions
    sorted_pairs = sorted(replacements.items(), key=lambda kv: len(kv[0]), reverse=True)
    for old, new in sorted_pairs:
        text = re.sub(re.escape(old), new, text)
    return text