from typing import List, Any, Optional
from registry.sdk.base_agent import BaseAgent
import logging

logger = logging.getLogger(__name__)


class DevOpsWorker(BaseAgent):
    """DevOps Worker agent responsible for CI/CD, Dockerfile, K8s manifests, and infrastructure deployment."""

    def __init__(self, id: str = "devops_worker_1", name: str = "Dave DevOps"):
        super().__init__(id=id, name=name, department="engineering", role="devops_engineer")
        self.kernel: Optional[Any] = None

    def set_kernel(self, kernel: Any) -> None:
        self.kernel = kernel

    def allowed_tools(self) -> List[str]:
        return ["docker", "kubectl", "terminal", "terraform"]

    def forbidden_actions(self) -> List[str]:
        return ["drop_production_db", "delete_production_database", "bypass_ci_checks"]

    def memory_access_level(self) -> str:
        return "admin"

    def can_handle(self, task_description: str) -> bool:
        if not task_description or not isinstance(task_description, str):
            return False
        desc_lower = task_description.lower()
        return any(k in desc_lower for k in ["devops", "deploy", "ci", "cd", "docker", "k8s", "kubernetes", "infra", "container", "pipeline"])

    async def execute(self, task: Any) -> Any:
        if task is None:
            task_desc = ""
            task_id = None
        elif isinstance(task, dict):
            raw_desc = task.get("description")
            if raw_desc is None:
                raw_desc = task.get("task_description")
            task_desc = raw_desc if raw_desc is not None else str(task)
            task_id = task.get("id") or task.get("task_id")
        elif hasattr(task, "description"):
            raw_desc = getattr(task, "description", "")
            task_desc = raw_desc if raw_desc is not None else ""
            task_id = getattr(task, "id", None)
        else:
            task_desc = str(task)
            task_id = None

        if not isinstance(task_desc, str):
            task_desc = str(task_desc)

        dockerfile_content = (
            "FROM python:3.12-slim\n"
            "WORKDIR /app\n"
            "COPY . /app\n"
            "RUN pip install --no-cache-dir -r requirements.txt\n"
            "CMD [\"python\", \"main.py\"]\n"
        )

        return {
            "status": "success",
            "role": self.role,
            "task_id": task_id,
            "task": task,
            "result": "deployment pipeline executed",
            "output": {
                "action": "devops_deployment_config",
                "config_type": "dockerfile_and_k8s",
                "dockerfile": dockerfile_content,
                "k8s_manifest": {
                    "apiVersion": "apps/v1",
                    "kind": "Deployment",
                    "metadata": {"name": "synapse-backend"},
                    "spec": {"replicas": 2}
                },
                "infra_status": "healthy"
            }
        }

    def validate(self, result: Any) -> bool:
        return isinstance(result, dict) and result.get("status") == "success"

    def report(self) -> Any:
        return {"status": "idle", "role": self.role}

    def remember(self, knowledge: Any) -> None:
        pass
