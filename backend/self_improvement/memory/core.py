# =============================================================================
# Self-Improvement Memory System
# =============================================================================
# Three-tier memory system with SQLite persistence:
#   1. Episodic   - specific events/experiences with timestamps
#   2. Semantic   - facts, patterns, consolidated knowledge
#   3. Procedural - learned procedures, skills, workflows
# Plus episodic consolidation (hippocampus-to-cortex style)
# =============================================================================

import os
import re
import json
import time
import sqlite3
import logging
import hashlib
import threading
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple, Iterator
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from collections import Counter

from backend.config import memory_db_path

logger = logging.getLogger(__name__)

MemoryStorePath = memory_db_path()


class MemoryType(str, Enum):
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"


class MemoryImportance(str, Enum):
    CRITICAL = 4
    HIGH = 3
    MEDIUM = 2
    LOW = 1


@dataclass
class Memory:
    id: Optional[int]
    type: MemoryType
    key: str
    content: str
    metadata: Dict[str, Any]
    importance: int
    created_at: float
    last_accessed_at: float
    access_count: int
    tags: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type.value if isinstance(self.type, MemoryType) else self.type,
            "key": self.key,
            "content": self.content,
            "metadata": self.metadata,
            "importance": self.importance,
            "created_at": self.created_at,
            "last_accessed_at": self.last_accessed_at,
            "access_count": self.access_count,
            "tags": self.tags,
        }


class MemorySystem:
    """Persistent three-tier memory with SQLite backend."""

    def __init__(self, db_path: str = MemoryStorePath):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._lock = threading.Lock()
        self._init_db()

    def _init_db(self):
        with self._lock, sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    type TEXT NOT NULL,
                    key TEXT NOT NULL,
                    content TEXT NOT NULL,
                    metadata TEXT NOT NULL DEFAULT '{}',
                    importance INTEGER NOT NULL DEFAULT 2,
                    created_at REAL NOT NULL,
                    last_accessed_at REAL NOT NULL,
                    access_count INTEGER NOT NULL DEFAULT 0,
                    tags TEXT NOT NULL DEFAULT '[]'
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_mem_type ON memories(type)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_mem_key ON memories(key)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_mem_importance ON memories(importance)
            """)
            conn.commit()

    # ----- CRUD ---------------------------------------------------------

    def store(self, mtype: MemoryType, key: str, content: str,
              metadata: Optional[Dict[str, Any]] = None,
              importance: int = 2, tags: Optional[List[str]] = None) -> int:
        """Store a memory, deduplicating on (type, key)."""
        metadata = metadata or {}
        tags = tags or []
        now = time.time()
        mtype_v = mtype.value if isinstance(mtype, MemoryType) else mtype

        with self._lock, sqlite3.connect(self.db_path) as conn:
            existing = conn.execute(
                "SELECT id FROM memories WHERE type=? AND key=?",
                (mtype_v, key),
            ).fetchone()

            if existing:
                conn.execute(
                    """UPDATE memories SET content=?, metadata=?, importance=?,
                       tags=?, last_accessed_at=?, created_at=?
                       WHERE id=?""",
                    (content, json.dumps(metadata), importance,
                     json.dumps(tags), now, now, existing[0]),
                )
                mid = existing[0]
                logger.debug(f"Updated memory {mid} ({mtype_v}:{key})")
            else:
                cur = conn.execute(
                    """INSERT INTO memories
                       (type, key, content, metadata, importance,
                        created_at, last_accessed_at, access_count, tags)
                       VALUES (?,?,?,?,?,?,?,0,?)""",
                    (mtype_v, key, content, json.dumps(metadata), importance,
                     now, now, json.dumps(tags)),
                )
                mid = cur.lastrowid
                logger.debug(f"Stored new memory {mid} ({mtype_v}:{key})")
            conn.commit()
        return mid

    def get(self, memory_id: int) -> Optional[Memory]:
        with self._lock, sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT * FROM memories WHERE id=?", (memory_id,)
            ).fetchone()
            if not row:
                return None
            conn.execute(
                "UPDATE memories SET access_count=access_count+1, "
                "last_accessed_at=? WHERE id=?",
                (time.time(), memory_id),
            )
            conn.commit()
            return self._row_to_memory(row)

    def recall(self, mtype: Optional[MemoryType] = None,
               query: Optional[str] = None,
               tags: Optional[List[str]] = None,
               limit: int = 10,
               min_importance: int = 0) -> List[Memory]:
        """Recall memories, optionally filtered/sorted by relevance."""
        conditions, params = [], []
        if mtype:
            conditions.append("type=?")
            params.append(mtype.value if isinstance(mtype, MemoryType) else mtype)
        if tags:
            conditions.append("tags LIKE ?")
            params.append(f"%{tags[0]}%")  # simple substring match
        if min_importance:
            conditions.append("importance>=?")
            params.append(min_importance)

        where = " WHERE " + " AND ".join(conditions) if conditions else ""
        _ORDER = "importance DESC, last_accessed_at DESC"
        _SQL = f"SELECT * FROM memories{where} ORDER BY {_ORDER} LIMIT ?"

        with self._lock, sqlite3.connect(self.db_path) as conn:
            params.append(limit)
            rows = conn.execute(_SQL, params).fetchall()

        results = [self._row_to_memory(r) for r in rows]

        if query:
            query_l = query.lower()
            results = [m for m in results
                       if query_l in m.content.lower()
                       or query_l in m.key.lower()
                       or any(query_l in s.lower() for s in m.metadata.values()
                              if isinstance(s, str))]

        return results

    def search(self, query: str, limit: int = 10) -> List[Memory]:
        """Keyword + basic pattern search across all memory types."""
        results = self.recall(limit=min(limit * 3, 50))
        query_l = query.lower()

        # Score by token overlap and exact substring
        tokens = set(re.findall(r"\w+", query_l))
        scored = []
        for m in results:
            text = f"{m.key} {m.content}".lower()
            token_hits = sum(1 for t in tokens if t in text)
            substring_hit = 2 if query_l in text else 0
            score = token_hits + substring_hit + m.importance * 0.5
            if score > 0:
                scored.append((score, m))

        scored.sort(key=lambda x: -x[0])
        return [m for _, m in scored[:limit]]

    def forget(self, memory_id: Optional[int] = None,
               before: Optional[float] = None,
               mtype: Optional[MemoryType] = None) -> int:
        """Delete a memory (or batch) and return count removed."""
        conditions, params = [], []
        if memory_id:
            conditions.append("id=?")
            params.append(memory_id)
        if before:
            conditions.append("created_at<?")
            params.append(before)
        if mtype:
            conditions.append("type=?")
            params.append(mtype.value if isinstance(mtype, MemoryType) else mtype)

        where = " WHERE " + " AND ".join(conditions) if conditions else ""
        sql = "DELETE FROM memories"
        if where:
            sql = sql + where
        with self._lock, sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(sql, params)
            conn.commit()
            return cur.rowcount

    # ----- Extra (prototype-level) -------------------------------------

    def remember_episode(self, event: str, context: Dict[str, Any],
                         importance: int = 2) -> int:
        """Record a discrete experience."""
        key = f"ep:{hashlib.sha256(
            (event + json.dumps(context, sort_keys=True)).encode()).hexdigest()[:12]}"
        return self.store(
            MemoryType.EPISODIC, key, event, context,
            importance=importance,
            tags=["episode"],
        )

    def remember_fact(self, subject: str, fact: str,
                      importance: int = 2, tags: Optional[List[str]] = None) -> int:
        """Store a semantic fact about a subject."""
        return self.store(
            MemoryType.SEMANTIC, f"fact:{subject}", fact,
            importance=importance, tags=tags or ["fact"],
        )

    def remember_procedure(self, name: str, steps: List[str],
                           success_rate: float = 1.0,
                           metadata: Optional[Dict[str, Any]] = None,
                           importance: int = 3) -> int:
        """Store how to do something, with a success signal."""
        md = dict(metadata or {})
        md["success_rate"] = success_rate
        md["step_count"] = len(steps)
        md["runs"] = 1
        return self.store(
            MemoryType.PROCEDURAL, name,
            "\n".join(f"{i+1}. {s}" for i, s in enumerate(steps)),
            md, importance=importance, tags=["procedure", name],
        )

    def update_procedure_success(self, name: str, succeeded: bool):
        """Update a procedure's running success rate."""
        with self._lock, sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT * FROM memories WHERE type='procedural' AND key=?",
                (name,),
            ).fetchone()
            if not row:
                return
            md = json.loads(row[4] or "{}")
            old_rate = md.get("success_rate", 1.0)
            old_runs = md.get("runs", 1)
            new_runs = old_runs + 1
            new_rate = ((old_rate * old_runs) + (1.0 if succeeded else 0.0)) / new_runs
            md["success_rate"] = round(new_rate, 3)
            md["runs"] = new_runs
            conn.execute(
                "UPDATE memories SET metadata=?, importance=? WHERE id=?",
                (json.dumps(md),
                 max(1, int(3 + (new_rate - 0.5) * 2)),
                 row[0]),
            )
            conn.commit()

    def stats(self) -> Dict[str, Any]:
        """Memory usage statistics."""
        with self._lock, sqlite3.connect(self.db_path) as conn:
            total = conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
            by_type = conn.execute(
                "SELECT type, COUNT(*) FROM memories GROUP BY type"
            ).fetchall()
            avg_imp = conn.execute(
                "SELECT AVG(importance) FROM memories"
            ).fetchone()[0] or 0
        return {
            "total_memories": total,
            "by_type": dict(by_type),
            "avg_importance": round(avg_imp, 2),
        }

    def consolidate(self) -> Dict[str, Any]:
        """Rehearse high-importance memories (strengthen)."""
        with self._lock, sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT id, importance FROM memories WHERE importance >= 3"
            ).fetchall()
            for mid, imp in rows:
                conn.execute(
                    "UPDATE memories SET access_count=access_count+1, "
                    "last_accessed_at=? WHERE id=?",
                    (time.time(), mid),
                )
            conn.commit()
            return {"rehearsed": len(rows)}

    # ----- Internals ---------------------------------------------------

    @staticmethod
    def _row_to_memory(row) -> Memory:
        return Memory(
            id=row[0],
            type=MemoryType(row[1]),
            key=row[2],
            content=row[3],
            metadata=json.loads(row[4] or "{}"),
            importance=row[5],
            created_at=row[6],
            last_accessed_at=row[7],
            access_count=row[8],
            tags=json.loads(row[9] or "[]"),
        )