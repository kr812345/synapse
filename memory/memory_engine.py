from shared.interfaces import Module
from shared.models import Event, Knowledge
from typing import Dict, List
import logging
from datetime import datetime, timezone
import sqlite3
import json

logger = logging.getLogger(__name__)

class MemoryEngine(Module):
    def __init__(self, db_path=":memory:"):
        self.kernel = None
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self):
        cursor = self.conn.cursor()
        
        # events
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS events (
            id TEXT PRIMARY KEY,
            source TEXT,
            destination TEXT,
            event_type TEXT,
            payload TEXT,
            timestamp TEXT
        )
        ''')

        # tasks
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id TEXT PRIMARY KEY,
            parent_task_id TEXT,
            description TEXT,
            status TEXT,
            assigned_agent TEXT,
            dependencies TEXT,
            result_payload TEXT,
            created_at TEXT,
            completed_at TEXT
        )
        ''')
        
        # artifacts
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS artifacts (
            id TEXT PRIMARY KEY,
            task_id TEXT,
            agent_id TEXT,
            title TEXT,
            file_path TEXT,
            summary TEXT,
            embedding TEXT,
            created_at TEXT
        )
        ''')
        
        # knowledge_graph
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS knowledge_graph (
            id TEXT PRIMARY KEY,
            observation TEXT,
            source TEXT,
            confidence REAL,
            category TEXT,
            importance INTEGER,
            embedding TEXT,
            expiration TEXT,
            created_at TEXT
        )
        ''')
        
        # agents
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS agents (
            id TEXT PRIMARY KEY,
            department TEXT,
            role TEXT,
            total_tasks_completed INTEGER,
            success_rate REAL,
            last_active TEXT
        )
        ''')

        # metrics
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS metrics (
            id TEXT PRIMARY KEY,
            metric_name TEXT,
            value REAL,
            timestamp TEXT
        )
        ''')
        self.conn.commit()

    @property
    def name(self) -> str:
        return "memory_engine"
        
    def set_kernel(self, kernel):
        self.kernel = kernel

    async def handle_event(self, event: Event) -> None:
        if event.event_type == "memory.store_knowledge":
            knowledge_data = event.payload.get("knowledge", {})
            try:
                knowledge = Knowledge(**knowledge_data)
                
                cursor = self.conn.cursor()
                cursor.execute('''
                INSERT INTO knowledge_graph 
                (id, observation, source, confidence, category, importance, embedding, expiration, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    knowledge.id,
                    knowledge.observation,
                    knowledge.source,
                    knowledge.confidence,
                    knowledge.category,
                    knowledge.importance,
                    json.dumps(knowledge.embedding) if knowledge.embedding else None,
                    knowledge.expiration.isoformat() if knowledge.expiration else None,
                    knowledge.created_at.isoformat()
                ))
                self.conn.commit()
                
                logger.info(f"Stored knowledge: {knowledge.id} - {knowledge.observation[:30]}...")
                
                if self.kernel:
                    resp = Event(
                        source=self.name,
                        destination=event.source,
                        event_type="memory.knowledge_stored",
                        payload={"knowledge_id": knowledge.id, "status": "success"}
                    )
                    await self.kernel.send_event(resp)
            except Exception as e:
                logger.error(f"Failed to store knowledge: {e}")
                
        elif event.event_type == "memory.query_knowledge":
            query = event.payload.get("query", "")
            results = []
            
            cursor = self.conn.cursor()
            # Simple substring search in sqlite for MVP
            cursor.execute('''
            SELECT * FROM knowledge_graph 
            WHERE (LOWER(observation) LIKE ? OR LOWER(category) LIKE ?)
            ''', (f'%{query.lower()}%', f'%{query.lower()}%'))
            
            rows = cursor.fetchall()
            now = datetime.now(timezone.utc)
            for row in rows:
                if row['expiration']:
                    # Handle if there's Z at the end or +00:00, etc.
                    exp_str = row['expiration']
                    if exp_str.endswith('Z'):
                        exp_str = exp_str[:-1] + '+00:00'
                    exp = datetime.fromisoformat(exp_str)
                    if exp.tzinfo is None:
                        exp = exp.replace(tzinfo=timezone.utc)
                    if exp < now:
                        continue
                        
                results.append({
                    "id": row['id'],
                    "observation": row['observation'],
                    "source": row['source'],
                    "confidence": row['confidence'],
                    "category": row['category'],
                    "importance": row['importance'],
                    "embedding": json.loads(row['embedding']) if row['embedding'] else None,
                    "expiration": row['expiration'],
                    "created_at": row['created_at']
                })
                    
            if self.kernel:
                resp = Event(
                    source=self.name,
                    destination=event.source,
                    event_type="memory.query_results",
                    payload={"query": query, "results": results}
                )
                await self.kernel.send_event(resp)
