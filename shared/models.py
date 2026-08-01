from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional
from datetime import datetime
import uuid

class Event(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source: str
    destination: str
    event_type: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)

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
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Knowledge(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    observation: str
    source: str
    confidence: float
    category: str
    importance: int
    embedding: Optional[List[float]] = None
    expiration: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


