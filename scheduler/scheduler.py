from shared.interfaces import Module
from shared.models import Event, Task, DAG
from typing import Dict, List
import logging
import asyncio

logger = logging.getLogger(__name__)

class Scheduler(Module):
    def __init__(self):
        self.kernel = None
        self.tasks: Dict[str, Task] = {}
        self.dags: Dict[str, DAG] = {}

    @property
    def name(self) -> str:
        return "scheduler"
        
    def set_kernel(self, kernel):
        self.kernel = kernel

    async def _evaluate_dag(self, dag_id: str):
        if dag_id not in self.dags:
            return
        dag = self.dags[dag_id]
        
        all_completed = True
        
        for task in dag.tasks:
            global_task = self.tasks.get(task.id, task)
            
            if global_task.status != "completed":
                all_completed = False
                
            if global_task.status == "pending":
                # Check if dependencies are met
                deps_met = True
                for dep_id in global_task.dependencies:
                    dep_task = self.tasks.get(dep_id)
                    if not dep_task or dep_task.status != "completed":
                        deps_met = False
                        break
                        
                if deps_met:
                    global_task.status = "scheduling" # lock it from being re-evaluated
                    self.tasks[global_task.id] = global_task
                    
                    if self.kernel:
                        logger.info(f"DAG {dag_id}: Executing unblocked task {global_task.id}")
                        req_event = Event(
                            source=self.name,
                            destination="agent_registry",
                            event_type="registry.find_agent",
                            payload={"task_description": global_task.description, "task_id": global_task.id}
                        )
                        await self.kernel.send_event(req_event)
                        
        if all_completed and dag.status != "completed":
            dag.status = "completed"
            logger.info(f"DAG {dag_id} completed!")
            if self.kernel:
                resp_event = Event(
                    source=self.name,
                    destination=dag.requester,
                    event_type="dag.complete",
                    payload={"dag_id": dag.id}
                )
                await self.kernel.send_event(resp_event)

    async def handle_event(self, event: Event) -> None:
        if event.event_type == "dag.create":
            dag = DAG(**event.payload["dag"])
            self.dags[dag.id] = dag
            dag.status = "executing"
            
            for t in dag.tasks:
                t.dag_id = dag.id
                self.tasks[t.id] = t
                
            logger.info(f"Scheduler received DAG: {dag.id} with {len(dag.tasks)} tasks")
            await self._evaluate_dag(dag.id)

        elif event.event_type == "task.create":
            task = Task(**event.payload["task"])
            self.tasks[task.id] = task
            logger.info(f"Scheduler received task: {task.id} - {task.description}")
            
            if self.kernel:
                req_event = Event(
                    source=self.name,
                    destination="agent_registry",
                    event_type="registry.find_agent",
                    payload={"task_description": task.description, "task_id": task.id}
                )
                await self.kernel.send_event(req_event)
                
        elif event.event_type == "registry.agent_found":
            task_id = event.payload.get("task_id")
            contract_data = event.payload.get("contract")
            
            if task_id in self.tasks and contract_data:
                task = self.tasks[task_id]
                task.assigned_agent = contract_data["identity"]
                task.status = "agent_assigned"
                logger.info(f"Task {task.id} assigned to agent {task.assigned_agent}")
                
                if self.kernel:
                    route_event = Event(
                        source=self.name,
                        destination="model_router",
                        event_type="model.request_execution",
                        payload={"task_id": task.id, "task_description": task.description, "agent": contract_data}
                    )
                    await self.kernel.send_event(route_event)
                    
        elif event.event_type == "model.execution_complete":
            task_id = event.payload.get("task_id")
            result = event.payload.get("result")
            
            if task_id in self.tasks:
                task = self.tasks[task_id]
                task.result = result
                task.status = "completed"
                logger.info(f"Task {task.id} completed successfully")
                
                if self.kernel:
                    resp_event = Event(
                        source=self.name,
                        destination=task.requester,
                        event_type="task.complete",
                        payload={"task_id": task.id, "result": result}
                    )
                    await self.kernel.send_event(resp_event)
                    
                if task.dag_id:
                    await self._evaluate_dag(task.dag_id)
