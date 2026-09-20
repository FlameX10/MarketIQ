"""
Cache manager for storing and retrieving generated content.
File-based cache with automatic expiry.
"""

import os
import json
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import shutil


class CacheManager:
    """Manages file-based caching with TTL support."""

    def __init__(self, cache_dir: str = "cache", ttl_hours: int = 24):
        """
        Initialize cache manager.

        Args:
            cache_dir: Directory to store cache files
            ttl_hours: Time-to-live in hours for cached content
        """
        self.cache_dir = cache_dir
        self.ttl_hours = ttl_hours

        # Ensure cache directory exists
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)

    def _compute_hash(self, market_name: str, base_year: str = "2024") -> str:
        """
        Compute a unique hash for the market.

        Args:
            market_name: The market name (upper case)
            base_year: Base year for the report

        Returns:
            SHA256 hash string
        """
        key = f"{market_name.upper()}_{base_year}"
        return hashlib.sha256(key.encode()).hexdigest()[:16]

    def _get_cache_path(self, cache_hash: str) -> str:
        """Get the full path for a cache file."""
        return os.path.join(self.cache_dir, f"{cache_hash}.json")

    def _get_metadata_path(self, cache_hash: str) -> str:
        """Get the metadata file path."""
        return os.path.join(self.cache_dir, f"{cache_hash}.meta")

    def get(
        self, market_name: str, base_year: str = "2024"
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached content if available and not expired.

        Args:
            market_name: The market name
            base_year: Base year for the report

        Returns:
            Cached content dict or None if not found/expired
        """
        cache_hash = self._compute_hash(market_name, base_year)
        cache_path = self._get_cache_path(cache_hash)
        meta_path = self._get_metadata_path(cache_hash)

        # Check if cache file exists
        if not os.path.exists(cache_path):
            print(f"Cache miss: {market_name}")
            return None

        # Check metadata for expiry
        if os.path.exists(meta_path):
            try:
                with open(meta_path, "r") as f:
                    metadata = json.load(f)

                cached_time = datetime.fromisoformat(metadata["cached_at"])
                expiry_time = cached_time + timedelta(hours=self.ttl_hours)

                if datetime.now() > expiry_time:
                    print(f"Cache expired: {market_name}")
                    # Remove expired cache
                    self.delete(market_name, base_year)
                    return None
            except Exception as e:
                print(f"Error reading cache metadata: {e}")
                return None

        # Load and return cached content
        try:
            with open(cache_path, "r") as f:
                content = json.load(f)
            print(f"Cache hit: {market_name}")
            return content
        except Exception as e:
            print(f"Error reading cache: {e}")
            return None

    def save(
        self, market_name: str, content: Dict[str, Any], base_year: str = "2024"
    ) -> bool:
        """
        Save content to cache.

        Args:
            market_name: The market name
            content: Content dict to cache
            base_year: Base year for the report

        Returns:
            True if successful, False otherwise
        """
        cache_hash = self._compute_hash(market_name, base_year)
        cache_path = self._get_cache_path(cache_hash)
        meta_path = self._get_metadata_path(cache_hash)

        try:
            # Save content
            with open(cache_path, "w") as f:
                json.dump(content, f, indent=2)

            # Save metadata
            metadata = {
                "market_name": market_name,
                "base_year": base_year,
                "cached_at": datetime.now().isoformat(),
                "ttl_hours": self.ttl_hours,
            }
            with open(meta_path, "w") as f:
                json.dump(metadata, f, indent=2)

            print(f"Cached: {market_name}")
            return True
        except Exception as e:
            print(f"Error saving cache: {e}")
            return False

    def delete(self, market_name: str, base_year: str = "2024") -> bool:
        """
        Delete cache entry.

        Args:
            market_name: The market name
            base_year: Base year for the report

        Returns:
            True if successful, False otherwise
        """
        cache_hash = self._compute_hash(market_name, base_year)
        cache_path = self._get_cache_path(cache_hash)
        meta_path = self._get_metadata_path(cache_hash)

        try:
            if os.path.exists(cache_path):
                os.remove(cache_path)
            if os.path.exists(meta_path):
                os.remove(meta_path)
            return True
        except Exception as e:
            print(f"Error deleting cache: {e}")
            return False

    def clear_all(self) -> int:
        """
        Clear all cached content.

        Returns:
            Number of cache entries cleared
        """
        count = 0
        try:
            for filename in os.listdir(self.cache_dir):
                file_path = os.path.join(self.cache_dir, filename)
                if os.path.isfile(file_path):
                    os.remove(file_path)
                    count += 1
            print(f"Cleared {count} cache entries")
        except Exception as e:
            print(f"Error clearing cache: {e}")
        return count

    def list_cached(self) -> list:
        """
        List all cached entries.

        Returns:
            List of dicts with cache info
        """
        entries = []
        try:
            for filename in os.listdir(self.cache_dir):
                if filename.endswith(".meta"):
                    meta_path = os.path.join(self.cache_dir, filename)
                    with open(meta_path, "r") as f:
                        metadata = json.load(f)
                    entries.append(metadata)
        except Exception as e:
            print(f"Error listing cache: {e}")
        return entries


if __name__ == "__main__":
    # Test cache manager
    cache = CacheManager(ttl_hours=24)

    # Test save
    test_content = {
        "executive_summary_intro": "Test content",
        "market_definition": "Test definition",
    }
    cache.save("GREEN METHANOL", test_content)

    # Test get
    cached = cache.get("GREEN METHANOL")
    print(f"Cached: {cached is not None}")

    # Test list
    entries = cache.list_cached()
    print(f"Cached entries: {len(entries)}")
