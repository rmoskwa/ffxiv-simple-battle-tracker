"""XIVAPI client with persistent caching for ability attack types.

This module provides efficient lookup of ability attack types (physical/magical)
by querying XIVAPI and caching results locally.
"""

import json
import logging
import urllib.error
import urllib.request
from pathlib import Path
from typing import Literal

logger = logging.getLogger(__name__)

# Attack type ID to category mapping
ATTACK_TYPE_CATEGORIES: dict[int, str] = {
    1: "Physical",  # 斬 Slash
    2: "Physical",  # 突 Thrust
    3: "Physical",  # 打 Strike
    4: "Physical",  # 射 Shoot
    5: "Magical",  # 魔法 Magic
    6: "Magical",  # ブレス Breath (treated as magical for mitigation purposes)
    7: "Magical",  # 音波 Sound Wave (treated as magical for mitigation purposes)
    8: "Special",  # リミットブレイク Limit Break
}

# Default cache file location (in the data directory)
DEFAULT_CACHE_PATH = Path(__file__).parent / "ability_cache.json"

# XIVAPI configuration
XIVAPI_BASE_URL = "https://xivapi.com"
XIVAPI_TIMEOUT = 15  # seconds
XIVAPI_BATCH_SIZE = 100  # Max abilities per request


HitType = Literal["Physical", "Magical", "Special", "Unknown"]


class XIVAPICache:
    """Cached client for XIVAPI ability lookups."""

    def __init__(self, cache_path: Path | None = None):
        """Initialize the cache.

        Args:
            cache_path: Path to the cache JSON file. Defaults to ability_cache.json
                       in the same directory as this module.
        """
        self.cache_path = cache_path or DEFAULT_CACHE_PATH
        self._cache: dict[str, dict] = {}
        self._load_cache()

    def _load_cache(self) -> None:
        """Load the cache from disk."""
        if self.cache_path.exists():
            try:
                with open(self.cache_path, encoding="utf-8") as f:
                    self._cache = json.load(f)
                logger.debug(f"Loaded {len(self._cache)} abilities from cache")
            except (json.JSONDecodeError, OSError) as e:
                logger.warning(f"Failed to load cache: {e}")
                self._cache = {}
        else:
            self._cache = {}

    def _save_cache(self) -> None:
        """Save the cache to disk."""
        try:
            with open(self.cache_path, "w", encoding="utf-8") as f:
                json.dump(self._cache, f, indent=2, ensure_ascii=False)
            logger.debug(f"Saved {len(self._cache)} abilities to cache")
        except OSError as e:
            logger.warning(f"Failed to save cache: {e}")

    def get_hit_type(self, ability_id: str) -> HitType:
        """Get the hit type for an ability from cache.

        Args:
            ability_id: Hex string ability ID (e.g., "79DF")

        Returns:
            Hit type: "Physical", "Magical", "Special", or "Unknown"
        """
        # Normalize to uppercase hex
        ability_id_upper = ability_id.upper()

        if ability_id_upper in self._cache:
            cached = self._cache[ability_id_upper]
            attack_type_id = cached.get("attack_type_id")
            if attack_type_id is not None:
                return ATTACK_TYPE_CATEGORIES.get(attack_type_id, "Unknown")
            return "Unknown"

        return "Unknown"

    def get_cached_ability_ids(self) -> set[str]:
        """Get all ability IDs currently in cache."""
        return set(self._cache.keys())

    def fetch_abilities(self, ability_ids: list[str]) -> dict[str, HitType]:
        """Fetch ability data from XIVAPI for the given IDs.

        Args:
            ability_ids: List of hex string ability IDs to fetch

        Returns:
            Dictionary mapping ability ID to hit type
        """
        if not ability_ids:
            return {}

        # Convert hex IDs to decimal for XIVAPI
        decimal_ids = []
        hex_to_decimal: dict[int, str] = {}
        for hex_id in ability_ids:
            try:
                decimal_id = int(hex_id, 16)
                decimal_ids.append(decimal_id)
                hex_to_decimal[decimal_id] = hex_id.upper()
            except ValueError:
                logger.warning(f"Invalid ability ID: {hex_id}")
                continue

        if not decimal_ids:
            return {}

        results: dict[str, HitType] = {}

        # Batch the requests
        for i in range(0, len(decimal_ids), XIVAPI_BATCH_SIZE):
            batch = decimal_ids[i : i + XIVAPI_BATCH_SIZE]
            batch_results = self._fetch_batch(batch, hex_to_decimal)
            results.update(batch_results)

        # Save cache after fetching
        self._save_cache()

        return results

    def _fetch_batch(
        self, decimal_ids: list[int], hex_to_decimal: dict[int, str]
    ) -> dict[str, HitType]:
        """Fetch a batch of abilities from XIVAPI.

        Args:
            decimal_ids: List of decimal ability IDs
            hex_to_decimal: Mapping from decimal to hex ID

        Returns:
            Dictionary mapping hex ability ID to hit type
        """
        ids_param = ",".join(str(id) for id in decimal_ids)
        url = (
            f"{XIVAPI_BASE_URL}/action?ids={ids_param}"
            f"&columns=ID,Name,AttackType.ID,AttackType.Name"
        )

        results: dict[str, HitType] = {}

        try:
            request = urllib.request.Request(
                url,
                headers={"User-Agent": "FFXIV-Battle-Tracker/1.0"},
            )
            with urllib.request.urlopen(request, timeout=XIVAPI_TIMEOUT) as response:
                data = json.loads(response.read())

            for item in data.get("Results", []):
                decimal_id = item.get("ID")
                if decimal_id is None:
                    continue

                hex_id = hex_to_decimal.get(decimal_id)
                if hex_id is None:
                    continue

                attack_type = item.get("AttackType") or {}
                attack_type_id = attack_type.get("ID")
                attack_type_name = attack_type.get("Name")

                # Cache the result
                self._cache[hex_id] = {
                    "name": item.get("Name"),
                    "attack_type_id": attack_type_id,
                    "attack_type_name": attack_type_name,
                }

                # Determine hit type
                if attack_type_id is not None:
                    hit_type = ATTACK_TYPE_CATEGORIES.get(attack_type_id, "Unknown")
                else:
                    hit_type = "Unknown"
                results[hex_id] = hit_type

            logger.debug(f"Fetched {len(results)} abilities from XIVAPI")

        except urllib.error.URLError as e:
            logger.warning(f"Failed to fetch from XIVAPI: {e}")
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Failed to parse XIVAPI response: {e}")

        return results

    def fetch_missing(self, ability_ids: list[str]) -> dict[str, HitType]:
        """Fetch only abilities not already in cache.

        Args:
            ability_ids: List of hex string ability IDs

        Returns:
            Dictionary mapping ability ID to hit type (includes cached results)
        """
        # Normalize IDs
        normalized = [id.upper() for id in ability_ids]

        # Find which are missing from cache
        cached = self.get_cached_ability_ids()
        missing = [id for id in normalized if id not in cached]

        # Fetch missing ones
        if missing:
            logger.info(f"Fetching {len(missing)} abilities from XIVAPI...")
            self.fetch_abilities(missing)

        # Return all results (from cache)
        return {id: self.get_hit_type(id) for id in normalized}


# Global cache instance
_cache_instance: XIVAPICache | None = None


def get_cache() -> XIVAPICache:
    """Get the global cache instance."""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = XIVAPICache()
    return _cache_instance


def get_hit_type(ability_id: str) -> HitType:
    """Get hit type for an ability (from cache only).

    Args:
        ability_id: Hex string ability ID

    Returns:
        Hit type or "Unknown" if not cached
    """
    return get_cache().get_hit_type(ability_id)


def fetch_hit_types(ability_ids: list[str]) -> dict[str, HitType]:
    """Fetch hit types for abilities, using cache when available.

    Args:
        ability_ids: List of hex string ability IDs

    Returns:
        Dictionary mapping ability ID to hit type
    """
    return get_cache().fetch_missing(ability_ids)
