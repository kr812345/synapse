from shared.interfaces import Module
from shared.models import Event, Knowledge
from typing import Dict, List
import logging
from datetime import datetime
import psycopg2
import psycopg2.extras
import json

logger = logging.getLogger(__name__)

class MemoryEngine(Module):
    def __init__(self, db_url="dbname=synapse user=root"):
        self.kernel = None
        self.db_url = db_url
        self.conn = psycopg2.connect(self.db_url)
        self.conn.autocommit = True
        self._init_db()

    def _init_db(self):
        cursor = self.conn.cursor()
        
        cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")

        # events
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS events (
            id TEXT PRIMARY KEY,
            source TEXT,
            destination TEXT,
            event_type TEXT,
            payload JSONB,
            timestamp TIMESTAMP
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
            dependencies JSONB,
            result_payload JSONB,
            created_at TIMESTAMP,
            completed_at TIMESTAMP
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
            embedding vector(1536),
            created_at TIMESTAMP
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
            embedding vector(1536),
            expiration TIMESTAMP,
            created_at TIMESTAMP
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
            last_active TIMESTAMP
        )
        ''')

        # metrics
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS metrics (
            id TEXT PRIMARY KEY,
            metric_name TEXT,
            value REAL,
            timestamp TIMESTAMP
        )
        ''')

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
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ''', (
                    knowledge.id,
                    knowledge.observation,
                    knowledge.source,
                    knowledge.confidence,
                    knowledge.category,
                    knowledge.importance,
                    json.dumps(knowledge.embedding) if knowledge.embedding else None,
                    knowledge.expiration,
                    knowledge.created_at
                ))
                
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
            
            cursor = self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
            
            # Simple substring search in Postgres for MVP (since pgvector requires embedding query, we fallback to LIKE)
            cursor.execute('''
            SELECT * FROM knowledge_graph 
            WHERE (LOWER(observation) LIKE %s OR LOWER(category) LIKE %s)
            ''', (f'%{query.lower()}%', f'%{query.lower()}%'))
            
            rows = cursor.fetchall()
            now = datetime.utcnow()
            for row in rows:
                if row['expiration']:
                    # Assuming row['expiration'] is a datetime object in psycopg2
                    exp = row['expiration']
                    if exp.tzinfo is None:
                        if exp < now:
                            continue
                    else:
                        from datetime import timezone
                        if exp < datetime.now(timezone.utc):
                            continue
                        
                # Fix vector formatting from db to list if needed
                emb = row['embedding']
                if emb and isinstance(emb, str):
                    # pgvector returns '[1,2,3]' string when not cast with register_vector
                    import ast
                    emb = ast.literal_eval(emb)
                    
                results.append({
                    "id": row['id'],
                    "observation": row['observation'],
                    "source": row['source'],
                    "confidence": row['confidence'],
                    "category": row['category'],
                    "importance": row['importance'],
                    "embedding": emb,
                    "expiration": row['expiration'].isoformat() if row['expiration'] else None,
                    "created_at": row['created_at'].isoformat() if row['created_at'] else None
                })
                    
            if self.kernel:
                resp = Event(
                    source=self.name,
                    destination=event.source,
                    event_type="memory.query_results",
                    payload={"query": query, "results": results}
                )
                await self.kernel.send_event(resp)
