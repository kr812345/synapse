from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
import uuid

class Event(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source: str
    destination: str
    event_type: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class AgentContract(BaseModel):
    identity: str
    department: str
    goal: str
    responsibilities: List[str]
    forbidden_actions: List[str]
    allowed_tools: List[str]
    memory_access: str
    output_schema: Dict[str, Any]
    confidence_score: float = 1.0

class Task(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    description: str
    requester: str
    status: str = "pending" # pending, agent_assigned, executing, validating, completed, failed
    assigned_agent: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    dag_id: Optional[str] = None
    dependencies: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class DAG(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    requester: str
    tasks: List[Task] = Field(default_factory=list)
    status: str = "pending" # pending, executing, completed, failed
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Knowledge(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    observation: str
    source: str
    confidence: float
    category: str
    importance: int
    embedding: Optional[List[float]] = None
    expiration: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))



