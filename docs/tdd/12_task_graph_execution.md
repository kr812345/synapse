# 12. Task Graph (DAG) Execution Paradigm

The defining feature of a real organization is parallel execution. A queue is too slow. The AI OS utilizes a Directed Acyclic Graph (DAG) for task execution.

## 12.1 The Planning Phase
When the CEO (User) issues a high-level command like:
> "Launch a new feature: AI code reviewer."

The Scheduler does not hand this to a single agent. Instead, it engages a specialized **Planning Model** (via the Model Router) to break this into a DAG.

### Resulting DAG:
```json
{
  "dag_id": "dag-launch-123",
  "nodes": [
    {
      "task_id": "t1",
      "department": "research",
      "description": "Analyze existing AI code reviewers on GitHub",
      "dependencies": []
    },
    {
      "task_id": "t2",
      "department": "engineering",
      "description": "Design backend architecture for code reviewer",
      "dependencies": ["t1"]
    },
    {
      "task_id": "t3",
      "department": "marketing",
      "description": "Draft launch tweet and blog post",
      "dependencies": ["t1"]
    },
    {
      "task_id": "t4",
      "department": "engineering",
      "description": "Implement code reviewer logic",
      "dependencies": ["t2"]
    }
  ]
}
```

## 12.2 Parallel Execution Execution Loop
1. The Scheduler evaluates the DAG. 
2. It finds all nodes with an empty `dependencies` array (e.g., `t1`).
3. It emits `task.create` for these nodes.
4. The Research Manager accepts `t1` and assigns it to a Research Worker.
5. While `t1` executes, `t2`, `t3`, and `t4` wait in a `pending` state.
6. Once `t1` emits `task.completed`, the Scheduler removes `t1` from all dependency lists.
7. `t2` and `t3` now have empty dependency arrays. The Scheduler emits `task.create` for **both simultaneously**.
8. The Engineering Manager and Marketing Manager go to work in parallel.
9. `t4` waits for `t2` to finish.

## 12.3 Artifact Passing
When `t1` completes, it generates an artifact (e.g., `competitor_analysis.md`).
Because `t2` and `t3` depend on `t1`, the Scheduler automatically injects the contents (or a summarized vector retrieval) of `competitor_analysis.md` into the prompt context for the Engineering and Marketing workers. 

This creates a seamless handoff between departments, exactly like passing a brief across desks in an office.
