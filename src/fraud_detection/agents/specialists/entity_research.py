"""Entity Research Agent for AML fraud detection.

This agent researches entities (customers, businesses, counterparties) for
adverse media, sanctions, and PEP status using Google Search.

Note: Gemini models do not support structured output (response_format) when using
function calling. The agent returns natural language which we parse into structured data.
"""

import json

import agents
from openai import AsyncOpenAI
from pydantic import ValidationError

from src.fraud_detection.models import EntityCheckResult
from src.fraud_detection.prompts import ENTITY_RESEARCH_AGENT_INSTRUCTIONS
from src.utils.tools.gemini_grounding import GeminiGroundingWithGoogleSearch


def create_entity_research_agent(
    openai_client: AsyncOpenAI,
    gemini_grounding: GeminiGroundingWithGoogleSearch,
    model: str = "gemini-2.5-flash",
) -> agents.Agent:
    """Create Entity Research Agent with Google Search.

    Parameters
    ----------
    openai_client : AsyncOpenAI
        OpenAI client for agent execution
    gemini_grounding : GeminiGroundingWithGoogleSearch
        Google Search tool for entity research
    model : str, optional
        Model to use, by default "gemini-2.5-flash"

    Returns
    -------
    agents.Agent
        Configured Entity Research Agent
    """
    # Note: No output_type because Gemini doesn't support structured output with tools
    return agents.Agent(
        name="EntityResearch",
        instructions=ENTITY_RESEARCH_AGENT_INSTRUCTIONS,
        tools=[
            agents.function_tool(gemini_grounding.get_web_search_grounded_response),
        ],
        model=agents.OpenAIChatCompletionsModel(model=model, openai_client=openai_client),
    )


async def run_entity_research_agent(
    agent: agents.Agent,
    query: str,
) -> list[EntityCheckResult]:
    """Run Entity Research Agent with a query.

    Parameters
    ----------
    agent : agents.Agent
        Configured Entity Research Agent
    query : str
        Query about entities to research (from InvestigationPlan)

    Returns
    -------
    list[EntityCheckResult]
        List of entity check results

    Examples
    --------
    >>> query = "Research Maya Singh for adverse media, sanctions, or PEP status"
    >>> results = await run_entity_research_agent(agent, query)
    >>> for result in results:
    ...     print(f"{result.entity_name}: {result.findings}")
    """
    result = await agents.Runner.run(agent, input=query)

    # Parse the natural language response into structured data
    response_text = result.final_output

    # Try to extract JSON from the response
    try:
        # Look for JSON array in the response
        start_idx = response_text.find("[")
        end_idx = response_text.rfind("]") + 1

        if start_idx != -1 and end_idx > start_idx:
            json_str = response_text[start_idx:end_idx]
            results_data = json.loads(json_str)
            return [EntityCheckResult(**result) for result in results_data]
        else:
            # Fallback: create a single result from the response
            return [
                EntityCheckResult(
                    entity_name="Unknown",
                    entity_type="customer",
                    adverse_media=False,
                    sanctions_hit=False,
                    pep_status=False,
                    findings=response_text[:300],
                    sources=[],
                )
            ]
    except (json.JSONDecodeError, ValidationError) as e:
        # Fallback: return the response as a single result
        return [
            EntityCheckResult(
                entity_name="Unknown",
                entity_type="customer",
                adverse_media=False,
                sanctions_hit=False,
                pep_status=False,
                findings=f"Parse error: {str(e)}. Response: {response_text[:200]}",
                sources=[],
            )
        ]

