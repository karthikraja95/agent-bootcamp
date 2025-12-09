"""Intake Agent for fraud detection system.

This module contains the Intake Agent that analyzes customer transaction reports
and extracts structured signals for investigation.
"""

import agents
from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from ..models import CustomerReport, ExtractedSignal
from ..prompts import INTAKE_AGENT_INSTRUCTIONS


class IntakeOutput(BaseModel):
    """Output from the Intake Agent."""

    customer_report: CustomerReport = Field(
        ..., description="Structured customer report data"
    )
    signals: list[ExtractedSignal] = Field(
        ..., description="Extracted signals indicating potential fraud or legitimacy"
    )
    risk_areas_to_investigate: list[str] = Field(
        ..., description="Suggested areas for further investigation"
    )


def create_intake_agent(
    openai_client: AsyncOpenAI,
    model: str = "gemini-2.5-flash",
) -> agents.Agent:
    """Create the Intake Agent.

    Parameters
    ----------
    openai_client : AsyncOpenAI
        OpenAI client for API calls.
    model : str, optional
        Model to use for the agent, by default "gemini-2.5-flash".

    Returns
    -------
    agents.Agent
        Configured Intake Agent.
    """
    return agents.Agent(
        name="IntakeAgent",
        instructions=INTAKE_AGENT_INSTRUCTIONS,
        output_type=IntakeOutput,
        model=agents.OpenAIChatCompletionsModel(
            model=model,
            openai_client=openai_client,
        ),
    )


async def run_intake_agent(
    agent: agents.Agent,
    customer_report: CustomerReport,
) -> IntakeOutput:
    """Run the Intake Agent on a customer report.

    Parameters
    ----------
    agent : agents.Agent
        The Intake Agent.
    customer_report : CustomerReport
        Customer report to analyze.

    Returns
    -------
    IntakeOutput
        Extracted signals and risk areas.
    """
    # Convert customer report to JSON for the agent
    report_json = customer_report.model_dump_json(indent=2)
    
    # Run the agent
    result = await agents.Runner.run(agent, input=report_json)
    
    # Extract structured output
    return result.final_output_as(IntakeOutput)

