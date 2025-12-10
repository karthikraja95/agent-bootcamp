"""Reasoning Agent - Synthesizes all specialist outputs using pure LLM reasoning.

This agent takes outputs from all specialist agents and applies pure LLM reasoning
to weigh evidence and reach a preliminary verdict. No tools, no rule-based scoring.
"""

import agents
from openai import AsyncOpenAI

from ..models import ReasoningOutput
from ..prompts import REASONING_AGENT_INSTRUCTIONS


def create_reasoning_agent(
    openai_client: AsyncOpenAI,
    model: str = "gemini-2.5-pro",
) -> agents.Agent:
    """Create a Reasoning Agent that synthesizes all investigation findings.

    This agent uses pure LLM reasoning (no tools) to analyze all evidence from
    specialist agents and reach a preliminary verdict.

    Args:
        openai_client: AsyncOpenAI client configured for Gemini API
        model: Model to use (default: gemini-2.5-pro for best reasoning)

    Returns:
        Configured Reasoning Agent with structured output
    """
    return agents.Agent(
        name="ReasoningAgent",
        instructions=REASONING_AGENT_INSTRUCTIONS,
        output_type=ReasoningOutput,
        model=agents.OpenAIChatCompletionsModel(model=model, openai_client=openai_client),
        # NO TOOLS - pure LLM reasoning only
    )


async def run_reasoning_agent(
    agent: agents.Agent,
    customer_report: str,
    intake_signals: str,
    typology_matches: str,
    red_flags: str,
    entity_checks: str,
) -> ReasoningOutput:
    """Run the Reasoning Agent to synthesize all investigation findings.

    Args:
        agent: Configured Reasoning Agent
        customer_report: Original customer report text
        intake_signals: Extracted signals from Intake Agent
        typology_matches: Results from Typology Matcher
        red_flags: Results from Pattern Analyzer
        entity_checks: Results from Entity Research

    Returns:
        ReasoningOutput with synthesized analysis and preliminary verdict
    """
    # Construct comprehensive input for reasoning
    reasoning_input = f"""
# CUSTOMER REPORT
{customer_report}

# INTAKE SIGNALS
{intake_signals}

# TYPOLOGY MATCHES
{typology_matches}

# RED FLAGS IDENTIFIED
{red_flags}

# ENTITY CHECK RESULTS
{entity_checks}

---

Analyze all the above evidence and provide your reasoning output.
"""

    result = await agents.Runner.run(agent, input=reasoning_input)
    return result.final_output

