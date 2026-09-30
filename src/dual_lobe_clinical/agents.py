from __future__ import annotations

from crewai import Agent

from dual_lobe_crewai.llm_factory import make_llm
from dual_lobe_crewai.prompts import B_ADVERSARY_PERSONA


def make_planner() -> Agent:
    return Agent(
        role="Lobe A — Planner and User-Facing Intelligence",
        goal=(
            "Understand the user's goal, create or revise the complete plan, "
            "and judge whether execution actually fulfilled it."
        ),
        backstory=(
            "You are the reasoning lobe. You do not own execution tools. "
            "You think, plan, revise when challenged by the execution lobe, "
            "and communicate the final result to the user."
        ),
        llm=make_llm("A"),
        tools=[],
        verbose=False,
        allow_delegation=False,
    )


def make_b_executor(tools=None) -> Agent:
    return Agent(
        role="Lobe B — Local Executor and Plan Challenger",
        goal=(
            "Execute A's current plan faithfully using local data and tools, "
            "challenge the plan whenever reality makes it invalid, and never "
            "silently rewrite A's plan."
        ),
        backstory=(
            "You are the execution lobe. You own tools and local data. "
            "You are adversarial toward weak planning but must cooperate with A "
            "because A alone owns the plan and user intent."
        ),
        llm=make_llm("B_CLINICAL"),
        tools=list(tools or []),
        verbose=False,
        allow_delegation=False,
    )


def make_b_verifier(tools=None) -> Agent:
    return Agent(
        role="Lobe B — Independent Adversary and Anti-Deception Verifier",
        goal=(
            "Independently challenge A's reasoning, goal-fit, assumptions, feasibility, execution provenance, "
            "and every material claim; surface omissions and contradictory evidence; never wave through an "
            "unsupported claim merely because A is confident or because B agrees with it."
        ),
        backstory=B_ADVERSARY_PERSONA,
        llm=make_llm("B_CLINICAL_VERIFY"),
        tools=list(tools or []),
        verbose=False,
        allow_delegation=False,
    )
