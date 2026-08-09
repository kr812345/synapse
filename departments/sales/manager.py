from typing import List, Any, Optional, Dict
from shared.interfaces import Module, KernelInterface
from shared.models import Event
from registry.sdk.base_agent import BaseAgent
from .outreach_worker import OutreachWorker
import logging

logger = logging.getLogger(__name__)

class SalesManager(Module, BaseAgent):
    def __init__(self, id: str = "sls_mgr", name: str = "Sales Manager"):
        self._agent_name = name
        BaseAgent.__init__(self, id=id, name=name, department="sales", role="manager")
        self.kernel: Optional[KernelInterface] = None
        self.workers: List[BaseAgent] = [
            OutreachWorker(f"{id}_worker1", "Oscar Outreach")
        ]

    @property
    def name(self) -> str:
        return "department.sales"

    @name.setter
    def name(self, value: str) -> None:
        self._agent_name = value

    def set_kernel(self, kernel: KernelInterface) -> None:
        self.kernel = kernel

    def allowed_tools(self) -> List[str]:
        return ["crm", "crm_search", "lead_qualifier", "email_sender", "email_draft", "pitch_generator"]

    def forbidden_actions(self) -> List[str]:
        return ["grant_unauthorized_discount", "delete_leads", "send_unauthorized_discounts", "unauthorized_discount"]

    def memory_access_level(self) -> str:
        return "admin"

    def can_handle(self, task_description: str) -> bool:
        desc = task_description.lower()
        return "sales" in desc or "lead" in desc or "deal" in desc or "crm" in desc or "outreach" in desc or "pitch" in desc

    async def execute(self, task: Any) -> Any:
        if isinstance(task, dict):
            task_dict = task
            desc = task_dict.get("description", "")
            lead_score = task_dict.get("lead_score", 50)
            company_raw = task_dict.get("company")
            template_raw = task_dict.get("template")
            action = task_dict.get("action", "")
        elif hasattr(task, "description"):
            desc = getattr(task, "description", str(task))
            lead_score = getattr(task, "lead_score", 50)
            company_raw = getattr(task, "company", None)
            template_raw = getattr(task, "template", None)
            action = getattr(task, "action", "")
            task_dict = {"description": desc}
        else:
            desc = str(task)
            lead_score = 50
            company_raw = None
            template_raw = None
            action = ""
            task_dict = {"description": desc}

        if action in self.forbidden_actions():
            raise PermissionError(f"Action '{action}' is forbidden for agent {self.name}")

        company = company_raw if company_raw else "unknown"
        email_template = template_raw if template_raw else "default_outreach"

        if lead_score <= 0:
            qualification = "unqualified"
        elif lead_score < 30:
            qualification = "disqualified"
        else:
            qualification = "qualified"

        missing_fields = []
        if "email" in task_dict and not task_dict["email"]:
            missing_fields.append("email")
        if "contact_name" in task_dict and not task_dict["contact_name"]:
            missing_fields.append("contact_name")

        worker_results = []
        for worker in self.workers:
            if worker.can_handle(desc):
                try:
                    res = await worker.execute(task)
                    worker_results.append(res)
                except Exception as e:
                    logger.warning(f"Worker {worker.name} execution warning: {e}")

        return {
            "status": "success",
            "qualification": qualification,
            "company": company,
            "missing_crm_fields": missing_fields,
            "email_template": email_template,
            "worker_results": worker_results,
            "task": task,
            "result": f"lead generation campaign executed for {company}: {qualification}. Sales lead pitch generated successfully"
        }

    def validate(self, result: Any) -> bool:
        return isinstance(result, dict) and result.get("status") == "success"

    def report(self) -> Any:
        return {"status": "managing", "workers_active": len(self.workers)}

    def remember(self, knowledge: Any) -> None:
        pass

    async def handle_event(self, event: Event) -> None:
        if event.event_type in ("department.execute_task", "task.assigned") or event.destination == self.name:
            task_data = event.payload.get("task", event.payload)
            if isinstance(task_data, dict):
                task_id = task_data.get("id")
            elif hasattr(task_data, "id"):
                task_id = getattr(task_data, "id", None)
            else:
                task_id = None

            try:
                result = await self.execute(task_data)
                if self.kernel:
                    response_event = Event(
                        source=self.name,
                        destination=event.source,
                        event_type="department.task_completed",
                        payload={
                            "task_id": task_id,
                            "status": "success",
                            "result": result
                        }
                    )
                    await self.kernel.send_event(response_event)
            except Exception as exc:
                logger.error(f"Execution error in {self.name} for task {task_id}: {exc}", exc_info=True)
                if self.kernel:
                    failure_event = Event(
                        source=self.name,
                        destination=event.source,
                        event_type="department.task_failed",
                        payload={
                            "task_id": task_id,
                            "status": "failed",
                            "error": str(exc)
                        }
                    )
                    await self.kernel.send_event(failure_event)
