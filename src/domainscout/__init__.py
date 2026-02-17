from __future__ import annotations

__all__ = ["HarnessOptions", "UserInput", "WorkflowResult", "run_workflow"]


def __getattr__(name: str):
    if name in {"HarnessOptions", "UserInput", "WorkflowResult", "run_workflow"}:
        from .harness import HarnessOptions, UserInput, WorkflowResult, run_workflow

        return {
            "HarnessOptions": HarnessOptions,
            "UserInput": UserInput,
            "WorkflowResult": WorkflowResult,
            "run_workflow": run_workflow,
        }[name]
    raise AttributeError(name)
