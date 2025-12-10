"""Planner Agent for fraud detection system.

This module contains the Planner Agent that creates investigation plans
based on intake signals and customer data.
"""

import agents
from openai import AsyncOpenAI

from ..models import InvestigationPlan
from ..prompts import PLANNER_AGENT_INSTRUCTIONS
from .intake import IntakeOutput


def create_planner_agent(
    openai_client: AsyncOpenAI,
    model: str = "gemini-2.5-pro",
) -> agents.Agent:
    """Create the Planner Agent.

    Parameters
    ----------
    openai_client : AsyncOpenAI
        OpenAI client for API calls.
    model : str, optional
        Model to use for the agent, by default "gemini-2.5-pro".

    Returns
    -------
    agents.Agent
        Configured Planner Agent.
    """
    return agents.Agent(
        name="PlannerAgent",
        instructions=PLANNER_AGENT_INSTRUCTIONS,
        output_type=InvestigationPlan,
        model=agents.OpenAIChatCompletionsModel(
            model=model,
            openai_client=openai_client,
        ),
    )


async def run_planner_agent(
    agent: agents.Agent,
    intake_output: IntakeOutput,
) -> InvestigationPlan:
    """Run the Planner Agent on intake output.

    Parameters
    ----------
    agent : agents.Agent
        The Planner Agent.
    intake_output : IntakeOutput
        Output from the Intake Agent containing signals and risk areas.

    Returns
    -------
    InvestigationPlan
        Investigation plan with queries for specialist agents.
    """
    # Convert intake output to JSON for the agent
    intake_json = intake_output.model_dump_json(indent=2)
    
    # Run the agent
    result = await agents.Runner.run(agent, input=intake_json)
    
    # Extract structured output
    return result.final_output_as(InvestigationPlan)

