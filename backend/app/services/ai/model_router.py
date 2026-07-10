"""Model routing configuration (LD-24, LD-18.3, LD-5).

One table decides, per task type: which model serves it and how large its
case-context budget is. No hidden model selection — the executor logs the
routed model into ai_call_log on every call.

Initial pair (LD-24): GPT-4o for reasoning-heavy tasks, GPT-4o-mini for
formatting-heavy tasks, both via the Datails Azure AI Foundry instance in the
tenant's region. Adding a model = a new entry here + a DECISIONS.md line —
never an external or ungoverned endpoint.
"""

from dataclasses import dataclass

MODEL_REASONING = "gpt-4o"
MODEL_FORMATTING = "gpt-4o-mini"

# LD-5: default context budget, configurable per task type. Never unbounded.
DEFAULT_CONTEXT_BUDGET_TOKENS = 8_000


@dataclass(frozen=True)
class TaskRoute:
    task_type: str
    model: str
    context_budget_tokens: int = DEFAULT_CONTEXT_BUDGET_TOKENS


# The Phase 10 task types (03; LD-20). Routing rationale (02 Block G): strong
# reasoning only where genuinely needed; cheaper model for formatting-heavy work.
_ROUTES: dict[str, TaskRoute] = {
    route.task_type: route
    for route in (
        TaskRoute("case_summarization", MODEL_FORMATTING),
        TaskRoute("report_drafting", MODEL_REASONING),
        TaskRoute("finding_draft", MODEL_REASONING),
        TaskRoute("research_assistant", MODEL_REASONING),
    )
}

TASK_TYPES = tuple(_ROUTES)


def get_route(task_type: str) -> TaskRoute:
    route = _ROUTES.get(task_type)
    if route is None:
        raise ValueError(
            f"unknown AI task type {task_type!r}; known: {sorted(_ROUTES)}"
        )
    return route
