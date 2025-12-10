"""Pattern Analyzer Agent for AML fraud detection.

This agent analyzes transaction patterns and identifies red flags using
dual knowledge sources (Wikipedia + Google Search).

Note: Gemini models do not support structured output (response_format) when using
function calling. The agent returns natural language which we parse into structured data.
"""

import json

import agents
from openai import AsyncOpenAI
from pydantic import ValidationError

from src.fraud_detection.models import RedFlag
from src.fraud_detection.prompts import PATTERN_ANALYZER_AGENT_INSTRUCTIONS
from src.utils import AsyncWeaviateKnowledgeBase
from src.utils.tools.gemini_grounding import GeminiGroundingWithGoogleSearch


def create_pattern_analyzer_agent(
    openai_client: AsyncOpenAI,
    async_knowledgebase: AsyncWeaviateKnowledgeBase,
    gemini_grounding: GeminiGroundingWithGoogleSearch,
    model: str = "gemini-2.5-flash",
) -> agents.Agent:
    """Create Pattern Analyzer Agent with dual knowledge sources.

    Parameters
    ----------
    openai_client : AsyncOpenAI
        OpenAI client for agent execution
    async_knowledgebase : AsyncWeaviateKnowledgeBase
        Wikipedia knowledge base for pattern analysis concepts
    gemini_grounding : GeminiGroundingWithGoogleSearch
        Google Search tool for current fraud patterns
    model : str, optional
        Model to use, by default "gemini-2.5-flash"

    Returns
    -------
    agents.Agent
        Configured Pattern Analyzer Agent
    """
    # Note: No output_type because Gemini doesn't support structured output with tools
    return agents.Agent(
        name="PatternAnalyzer",
        instructions=PATTERN_ANALYZER_AGENT_INSTRUCTIONS,
        tools=[
            agents.function_tool(async_knowledgebase.search_knowledgebase),
            agents.function_tool(gemini_grounding.get_web_search_grounded_response),
        ],
        model=agents.OpenAIChatCompletionsModel(model=model, openai_client=openai_client),
    )


async def run_pattern_analyzer_agent(
    agent: agents.Agent,
    query: str,
) -> list[RedFlag]:
    """Run Pattern Analyzer Agent with a query.

    Parameters
    ----------
    agent : agents.Agent
        Configured Pattern Analyzer Agent
    query : str
        Query about transaction patterns to analyze (from InvestigationPlan)

    Returns
    -------
    list[RedFlag]
        List of identified red flags

    Examples
    --------
    >>> query = "Analyze frequency and timing of cash deposits under £10,000"
    >>> red_flags = await run_pattern_analyzer_agent(agent, query)
    >>> for flag in red_flags:
    ...     print(f"{flag.severity}: {flag.description}")
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
            flags_data = json.loads(json_str)
            return [RedFlag(**flag) for flag in flags_data]
        else:
            # Fallback: return empty list if no red flags found
            if "no red flags" in response_text.lower() or "no issues" in response_text.lower():
                return []
            # Otherwise create a single flag from the response
            return [
                RedFlag(
                    description="Analysis result",
                    severity="medium",
                    evidence=response_text[:200],
                    source="Agent analysis",
                )
            ]
    except (json.JSONDecodeError, ValidationError) as e:
        # Fallback: return the response as a single flag
        return [
            RedFlag(
                description=f"Parse error: {str(e)}",
                severity="low",
                evidence=response_text[:200],
                source="Agent analysis",
            )
        ]

