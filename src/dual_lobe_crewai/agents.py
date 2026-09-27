from __future__ import annotations

from crewai import Agent

from .llm_factory import make_llm
from .prompts import A_PERSONA, B_ADVERSARY_PERSONA, CHILD_PERSONA


def make_a(tools=None) -> Agent:
    return Agent(
        role="Lobe A — Primary Worker and Delegator",
        goal="Solve the user's task with minimum wall-clock delay, delegating independent work whenever that can save the user time.",
        backstory=A_PERSONA,
        llm=make_llm("A"),
        tools=list(tools or []),
        verbose=False,
        allow_delegation=False,
    )


def make_child_worker(tools=None) -> Agent:
    return Agent(
        role="Temporary Delegated Inference Worker",
        goal="Execute the assigned independent subtask quickly and return a self-contained result to Lobe A.",
        backstory=CHILD_PERSONA,
        llm=make_llm("A_CHILD"),
        tools=list(tools or []),
        verbose=False,
        allow_delegation=False,
    )


def make_b_adversary(tools=None, *, llm_role: str = "B_VERIFY") -> Agent:
    return Agent(
        role="Lobe B — Independent Adversary and Anti-Deception Verifier",
        goal=(
            "Independently challenge A's reasoning, goal-fit, assumptions, feasibility, execution provenance, "
            "and every material claim; surface omissions and contradictory evidence; never wave through an "
            "unsupported claim merely because A is confident or because B agrees with it."
        ),
        backstory=B_ADVERSARY_PERSONA,
        llm=make_llm(llm_role),
        tools=list(tools or []),
        verbose=False,
        allow_delegation=False,
    )
