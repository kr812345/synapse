import os
import json
import uuid
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional
import psycopg2
import psycopg2.extras

from shared.interfaces import Module
from shared.models import Event, Knowledge

logger = logging.getLogger(__name__)


class MemoryEngine(Module):
    def __init__(self, db_url: Optional[str] = None):
        self.kernel = None
        self.db_url = db_url or os.environ.get("DATABASE_URL") or "dbname=synapse user=root"
        self.conn = None
        self.degraded = False
        self._in_memory_chats: Dict[str, List[Dict[str, str]]] = {}
        self._in_memory_knowledge: List[Knowledge] = []
        try:
            self.conn = psycopg2.connect(self.db_url)
            self.conn.autocommit = True
            self._init_db()
        except Exception as e:
            self.conn = None
            self.degraded = True
            logger.warning(f"PostgreSQL unavailable ({e}); running MemoryEngine in degraded in-memory mode.")

    def _init_db(self):
        if not self.conn:
            return
        cursor = self.conn.cursor()

        cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")

        # events
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id TEXT PRIMARY KEY,
            source TEXT,
            destination TEXT,
            event_type TEXT,
            payload JSONB,
            timestamp TIMESTAMP
        )
        """)

        # tasks
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id TEXT PRIMARY KEY,
            parent_task_id TEXT,
            description TEXT,
            status TEXT,
            assigned_agent TEXT,
            dependencies JSONB,
            result_payload JSONB,
            created_at TIMESTAMP,
            completed_at TIMESTAMP
        )
        """)

        # artifacts
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS artifacts (
            id TEXT PRIMARY KEY,
            task_id TEXT,
            agent_id TEXT,
            title TEXT,
            file_path TEXT,
            summary TEXT,
            embedding vector(1536),
            created_at TIMESTAMP
        )
        """)

        # knowledge_graph
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS knowledge_graph (
            id TEXT PRIMARY KEY,
            observation TEXT,
            source TEXT,
            confidence REAL,
            category TEXT,
            importance INTEGER,
            embedding vector(1536),
            expiration TIMESTAMP,
            created_at TIMESTAMP
        )
        """)

        # agents
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS agents (
            id TEXT PRIMARY KEY,
            department TEXT,
            role TEXT,
            total_tasks_completed INTEGER,
            success_rate REAL,
            last_active TIMESTAMP
        )
        """)

        # chat_sessions
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_sessions (
            id TEXT PRIMARY KEY,
            session_id TEXT,
            role TEXT,
            content TEXT,
            timestamp TIMESTAMP
        )
        """)

        # metrics
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS metrics (
            id TEXT PRIMARY KEY,
            metric_name TEXT,
            value REAL,
            timestamp TIMESTAMP
        )
        """)

    @property
    def name(self) -> str:
        return "memory_engine"

    def set_kernel(self, kernel):
        self.kernel = kernel

    def store_chat(self, session_id: str, role: str, content: str) -> None:
        """Direct helper to store a chat turn in DB or degraded in-memory store."""
        session_key = session_id or "default"
        self._in_memory_chats.setdefault(session_key, []).append(
            {"role": role, "content": content}
        )
        if not self.conn or self.degraded:
            return
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                """
                INSERT INTO chat_sessions (id, session_id, role, content, timestamp)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (str(uuid.uuid4()), session_key, role, content, datetime.utcnow()),
            )
        except Exception as e:
            logger.warning(f"DB store_chat failed ({e}); kept in-memory.")

    def get_chat_history(self, session_id: str, limit: int = 10) -> List[Dict[str, str]]:
        """Direct helper to fetch recent chat turns from DB or degraded in-memory store."""
        session_key = session_id or "default"
        if not self.conn or self.degraded:
            return list(self._in_memory_chats.get(session_key, [])[-limit:])
        try:
            cursor = self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
            cursor.execute(
                """
                SELECT role, content FROM chat_sessions
                WHERE session_id = %s ORDER BY timestamp ASC LIMIT %s
                """,
                (session_key, limit),
            )
            rows = cursor.fetchall()
            return [{"role": r["role"], "content": r["content"]} for r in rows]
        except Exception as e:
            logger.warning(f"DB get_chat_history failed ({e}); returning in-memory.")
            return list(self._in_memory_chats.get(session_key, [])[-limit:])

    async def handle_event(self, event: Event) -> None:
        if event.event_type == "memory.store_knowledge":
            knowledge_data = event.payload.get("knowledge", {})
            try:
                knowledge = Knowledge(**knowledge_data)
                if self.conn and not self.degraded:
                    cursor = self.conn.cursor()
                    cursor.execute(
                        """
                        INSERT INTO knowledge_graph
                        (id, observation, source, confidence, category, importance, embedding, expiration, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            knowledge.id,
                            knowledge.observation,
                            knowledge.source,
                            knowledge.confidence,
                            knowledge.category,
                            knowledge.importance,
                            json.dumps(knowledge.embedding) if knowledge.embedding else None,
                            knowledge.expiration,
                            knowledge.created_at,
                        ),
                    )
                else:
                    self._in_memory_knowledge.append(knowledge)

                logger.info(f"Stored knowledge: {knowledge.id} - {knowledge.observation[:30]}...")

                if self.kernel:
                    resp = Event(
                        source=self.name,
                        destination=event.source,
                        event_type="memory.knowledge_stored",
                        payload={"knowledge_id": knowledge.id, "status": "success"},
                    )
                    await self.kernel.send_event(resp)
            except Exception as e:
                logger.error(f"Failed to store knowledge: {e}")

        elif event.event_type == "memory.query_knowledge":
            query = event.payload.get("query", "")
            results = []

            if self.conn and not self.degraded:
                cursor = self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
                cursor.execute(
                    """
                    SELECT * FROM knowledge_graph
                    WHERE (LOWER(observation) LIKE %s OR LOWER(category) LIKE %s)
                    """,
                    (f"%{query.lower()}%", f"%{query.lower()}%"),
                )
                rows = cursor.fetchall()
                now = datetime.utcnow()
                for row in rows:
                    if row["expiration"]:
                        exp = row["expiration"]
                        if exp.tzinfo is None:
                            if exp < now:
                                continue
                        else:
                            if exp < datetime.now(timezone.utc):
                                continue

                    emb = row["embedding"]
                    if emb and isinstance(emb, str):
                        import ast
                        emb = ast.literal_eval(emb)

                    results.append({
                        "id": row["id"],
                        "observation": row["observation"],
                        "source": row["source"],
                        "confidence": row["confidence"],
                        "category": row["category"],
                        "importance": row["importance"],
                        "embedding": emb,
                        "expiration": row["expiration"].isoformat() if row["expiration"] else None,
                        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                    })
            else:
                q_lower = query.lower()
                now = datetime.utcnow()
                for k in self._in_memory_knowledge:
                    if k.expiration:
                        exp = k.expiration
                        if exp.tzinfo is None and exp < now:
                            continue
                        if exp.tzinfo is not None and exp < datetime.now(timezone.utc):
                            continue
                    if q_lower in k.observation.lower() or q_lower in k.category.lower():
                        results.append({
                            "id": k.id,
                            "observation": k.observation,
                            "source": k.source,
                            "confidence": k.confidence,
                            "category": k.category,
                            "importance": k.importance,
                            "embedding": k.embedding,
                            "expiration": k.expiration.isoformat() if k.expiration else None,
                            "created_at": k.created_at.isoformat() if k.created_at else None,
                        })

            if self.kernel:
                resp = Event(
                    source=self.name,
                    destination=event.source,
                    event_type="memory.query_results",
                    payload={"query": query, "results": results},
                )
                await self.kernel.send_event(resp)

        elif event.event_type == "memory.store_chat":
            session_id = event.payload.get("session_id")
            role = event.payload.get("role")
            content = event.payload.get("content")
            self.store_chat(session_id, role, content)

        elif event.event_type == "memory.get_chat_history":
            session_id = event.payload.get("session_id")
            history = self.get_chat_history(session_id, limit=10)
            if self.kernel:
                resp = Event(
                    source=self.name,
                    destination=event.source,
                    event_type="memory.chat_history_result",
                    payload={"session_id": session_id, "history": history},
                )
                await self.kernel.send_event(resp)
