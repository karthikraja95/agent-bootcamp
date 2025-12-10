"""Typology Matcher Agent for AML fraud detection.

This agent matches customer activity against known AML typologies using
dual knowledge sources (Wikipedia + Google Search).

Note: Gemini models do not support structured output (response_format) when using
function calling. The agent returns natural language which we parse into structured data.
"""

import json

import agents
from openai import AsyncOpenAI
from pydantic import ValidationError

from src.fraud_detection.models import TypologyMatch
from src.fraud_detection.prompts import TYPOLOGY_MATCHER_AGENT_INSTRUCTIONS
from src.utils import AsyncWeaviateKnowledgeBase
from src.utils.tools.gemini_grounding import GeminiGroundingWithGoogleSearch


def create_typology_matcher_agent(
    openai_client: AsyncOpenAI,
    async_knowledgebase: AsyncWeaviateKnowledgeBase,
    gemini_grounding: GeminiGroundingWithGoogleSearch,
    model: str = "gemini-2.5-flash",
) -> agents.Agent:
    """Create Typology Matcher Agent with dual knowledge sources.

    Parameters
    ----------
    openai_client : AsyncOpenAI
        OpenAI client for agent execution
    async_knowledgebase : AsyncWeaviateKnowledgeBase
        Wikipedia knowledge base for AML typology definitions
    gemini_grounding : GeminiGroundingWithGoogleSearch
        Google Search tool for current AML guidance
    model : str, optional
        Model to use, by default "gemini-2.5-flash"

    Returns
    -------
    agents.Agent
        Configured Typology Matcher Agent
    """
    # Note: No output_type because Gemini doesn't support structured output with tools
    return agents.Agent(
        name="TypologyMatcher",
        instructions=TYPOLOGY_MATCHER_AGENT_INSTRUCTIONS,
        tools=[
            agents.function_tool(async_knowledgebase.search_knowledgebase),
            agents.function_tool(gemini_grounding.get_web_search_grounded_response),
        ],
        model=agents.OpenAIChatCompletionsModel(model=model, openai_client=openai_client),
    )


async def run_typology_matcher_agent(
    agent: agents.Agent,
    query: str,
) -> list[TypologyMatch]:
    """Run Typology Matcher Agent with a query.

    Parameters
    ----------
    agent : agents.Agent
        Configured Typology Matcher Agent
    query : str
        Query about potential typology matches (from InvestigationPlan)

    Returns
    -------
    list[TypologyMatch]
        List of typology matching results

    Examples
    --------
    >>> query = "Check if pattern of £7,500 transfers matches structuring typology"
    >>> matches = await run_typology_matcher_agent(agent, query)
    >>> for match in matches:
    ...     print(f"{match.name}: {match.matched} (confidence: {match.confidence})")
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
            matches_data = json.loads(json_str)
            return [TypologyMatch(**match) for match in matches_data]
        else:
            # Fallback: create a single match from the response
            return [
                TypologyMatch(
                    name="Analysis",
                    matched=True,
                    confidence=0.5,
                    explanation=response_text[:500],
                    source="Agent analysis",
                )
            ]
    except (json.JSONDecodeError, ValidationError) as e:
        # Fallback: return the response as a single match
        return [
            TypologyMatch(
                name="Analysis",
                matched=True,
                confidence=0.5,
                explanation=f"Parse error: {str(e)}. Response: {response_text[:300]}",
                source="Agent analysis",
            )
        ]

