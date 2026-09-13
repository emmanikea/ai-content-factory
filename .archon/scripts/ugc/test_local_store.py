#!/usr/bin/env python3
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from local_store import LocalStore, StoreConflict


class LocalStoreTests(unittest.TestCase):
    def test_put_get_and_version(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            store = LocalStore(temp)
            first = store.put("creators", "creator-a", {"name": "A"})
            self.assertEqual(first["store_version"], 1)
            self.assertEqual(store.get("creators", "creator-a"), {"name": "A"})
            second = store.put("creators", "creator-a", {"name": "B"}, expected_version=1)
            self.assertEqual(second["store_version"], 2)
            self.assertEqual(second["created_at"], first["created_at"])

    def test_conflict_blocks_stale_write(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            store = LocalStore(temp)
            store.put("references", "ref-1", {"x": 1})
            with self.assertRaises(StoreConflict):
                store.put("references", "ref-1", {"x": 2}, expected_version=0)

    def test_list_returns_metadata_not_documents(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            store = LocalStore(temp)
            store.put("specs", "b", {"secret": "payload-b"})
            store.put("specs", "a", {"secret": "payload-a"})
            rows = store.list("specs")
            self.assertEqual([row["id"] for row in rows], ["a", "b"])
            self.assertNotIn("document", rows[0])

    def test_delete_can_be_version_guarded(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            store = LocalStore(temp)
            store.put("jobs", "job-1", {"status": "planned"})
            with self.assertRaises(StoreConflict):
                store.delete("jobs", "job-1", expected_version=2)
            self.assertTrue(store.delete("jobs", "job-1", expected_version=1))
            self.assertIsNone(store.get("jobs", "job-1"))

    def test_rejects_path_like_ids(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            store = LocalStore(temp)
            with self.assertRaises(ValueError):
                store.put("artifacts", "../escape", {"x": 1})


if __name__ == "__main__":
    unittest.main()
