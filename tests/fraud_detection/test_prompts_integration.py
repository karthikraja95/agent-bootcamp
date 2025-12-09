"""Integration tests for agent prompts with real API calls.

This test suite validates:
1. Agent creation with prompts
2. Tool integration (Wikipedia + Google Search)
3. Actual API calls to verify prompts work
4. Response format validation
"""

import asyncio
from pathlib import Path

import agents
import pytest
import pytest_asyncio
from dotenv import load_dotenv
from openai import AsyncOpenAI

from src.fraud_detection.prompts import (
    ENTITY_RESEARCH_AGENT_INSTRUCTIONS,
    INTAKE_AGENT_INSTRUCTIONS,
    PATTERN_ANALYZER_AGENT_INSTRUCTIONS,
    PLANNER_AGENT_INSTRUCTIONS,
    REASONING_AGENT_INSTRUCTIONS,
    REPORT_AGENT_INSTRUCTIONS,
    TYPOLOGY_MATCHER_AGENT_INSTRUCTIONS,
)
from src.utils import (
    AsyncWeaviateKnowledgeBase,
    Configs,
    get_weaviate_async_client,
)
from src.utils.tools.gemini_grounding import (
    GeminiGroundingWithGoogleSearch,
    ModelSettings,
)

# Load environment variables
load_dotenv(verbose=True)

# Test configuration
AGENT_LLM_NAMES = {
    "worker": "gemini-2.5-flash",
    "planner": "gemini-2.5-pro",
}


@pytest_asyncio.fixture(scope="module")
async def async_clients():
    """Set up async clients for testing."""
    configs = Configs.from_env_var()
    
    # Weaviate client
    weaviate_client = get_weaviate_async_client(
        http_host=configs.weaviate_http_host,
        http_port=configs.weaviate_http_port,
        http_secure=configs.weaviate_http_secure,
        grpc_host=configs.weaviate_grpc_host,
        grpc_port=configs.weaviate_grpc_port,
        grpc_secure=configs.weaviate_grpc_secure,
        api_key=configs.weaviate_api_key,
    )
    
    # OpenAI client
    openai_client = AsyncOpenAI()
    
    # Knowledge base
    kb = AsyncWeaviateKnowledgeBase(
        weaviate_client,
        collection_name="enwiki_20250520",
    )
    
    # Gemini grounding tool
    gemini_tool = GeminiGroundingWithGoogleSearch(
        model_settings=ModelSettings(model=AGENT_LLM_NAMES["worker"])
    )
    
    yield {
        "weaviate": weaviate_client,
        "openai": openai_client,
        "kb": kb,
        "gemini": gemini_tool,
    }
    
    # Cleanup
    await weaviate_client.close()
    await openai_client.close()


class TestPromptValidation:
    """Test that all prompts are properly defined."""

    def test_all_prompts_exist(self):
        """Test that all required prompts are defined."""
        prompts = [
            INTAKE_AGENT_INSTRUCTIONS,
            PLANNER_AGENT_INSTRUCTIONS,
            TYPOLOGY_MATCHER_AGENT_INSTRUCTIONS,
            PATTERN_ANALYZER_AGENT_INSTRUCTIONS,
            ENTITY_RESEARCH_AGENT_INSTRUCTIONS,
            REASONING_AGENT_INSTRUCTIONS,
            REPORT_AGENT_INSTRUCTIONS,
        ]
        
        for prompt in prompts:
            assert isinstance(prompt, str)
            assert len(prompt) > 100  # Should be substantial
            assert "You are" in prompt  # Should have agent identity

    def test_prompts_have_task_description(self):
        """Test that prompts describe the agent's task."""
        prompts = [
            TYPOLOGY_MATCHER_AGENT_INSTRUCTIONS,
            PATTERN_ANALYZER_AGENT_INSTRUCTIONS,
            ENTITY_RESEARCH_AGENT_INSTRUCTIONS,
        ]
        
        for prompt in prompts:
            assert "task" in prompt.lower() or "your role" in prompt.lower()

    def test_dual_kb_prompts_mention_both_tools(self):
        """Test that dual-KB agents mention both knowledge sources."""
        dual_kb_prompts = [
            TYPOLOGY_MATCHER_AGENT_INSTRUCTIONS,
            PATTERN_ANALYZER_AGENT_INSTRUCTIONS,
        ]
        
        for prompt in dual_kb_prompts:
            assert "search_knowledgebase" in prompt
            assert "get_web_search_grounded_response" in prompt
            assert "When to use" in prompt  # Should have routing guidance


@pytest.mark.asyncio
class TestAgentCreation:
    """Test that agents can be created with the prompts."""

    async def test_create_typology_matcher_agent(self, async_clients):
        """Test creating Typology Matcher agent with both tools."""
        # Create KB worker agent
        kb_agent = agents.Agent(
            name="KnowledgeBaseAgent",
            instructions="You search the knowledge base and return results.",
            tools=[
                agents.function_tool(async_clients["kb"].search_knowledgebase),
            ],
            model=agents.OpenAIChatCompletionsModel(
                model=AGENT_LLM_NAMES["worker"],
                openai_client=async_clients["openai"],
            ),
        )
        
        # Create Typology Matcher with both tools
        typology_agent = agents.Agent(
            name="TypologyMatcher",
            instructions=TYPOLOGY_MATCHER_AGENT_INSTRUCTIONS,
            tools=[
                kb_agent.as_tool(
                    tool_name="search_knowledgebase",
                    tool_description="Search Wikipedia for AML typologies and concepts",
                ),
                agents.function_tool(
                    async_clients["gemini"].get_web_search_grounded_response
                ),
            ],
            model=agents.OpenAIChatCompletionsModel(
                model=AGENT_LLM_NAMES["worker"],
                openai_client=async_clients["openai"],
            ),
        )
        
        assert typology_agent is not None
        assert typology_agent.name == "TypologyMatcher"
        assert len(typology_agent.tools) == 2

    async def test_create_entity_research_agent(self, async_clients):
        """Test creating Entity Research agent with Google Search only."""
        entity_agent = agents.Agent(
            name="EntityResearch",
            instructions=ENTITY_RESEARCH_AGENT_INSTRUCTIONS,
            tools=[
                agents.function_tool(
                    async_clients["gemini"].get_web_search_grounded_response
                ),
            ],
            model=agents.OpenAIChatCompletionsModel(
                model=AGENT_LLM_NAMES["worker"],
                openai_client=async_clients["openai"],
            ),
        )
        
        assert entity_agent is not None
        assert entity_agent.name == "EntityResearch"
        assert len(entity_agent.tools) == 1


@pytest.mark.asyncio
@pytest.mark.slow  # Mark as slow since it makes real API calls
class TestAgentAPIIntegration:
    """Test agents with real API calls (requires valid API keys)."""

    async def test_typology_matcher_wikipedia_search(self, async_clients):
        """Test Typology Matcher can search Wikipedia for AML typologies."""
        # Create KB worker agent
        kb_agent = agents.Agent(
            name="KnowledgeBaseAgent",
            instructions="You search the knowledge base and return a summary with sources.",
            tools=[
                agents.function_tool(async_clients["kb"].search_knowledgebase),
            ],
            model=agents.OpenAIChatCompletionsModel(
                model=AGENT_LLM_NAMES["worker"],
                openai_client=async_clients["openai"],
            ),
        )

        # Create Typology Matcher
        typology_agent = agents.Agent(
            name="TypologyMatcher",
            instructions=TYPOLOGY_MATCHER_AGENT_INSTRUCTIONS,
            tools=[
                kb_agent.as_tool(
                    tool_name="search_knowledgebase",
                    tool_description="Search Wikipedia for AML typologies and concepts",
                ),
                agents.function_tool(
                    async_clients["gemini"].get_web_search_grounded_response
                ),
            ],
            model=agents.OpenAIChatCompletionsModel(
                model=AGENT_LLM_NAMES["worker"],
                openai_client=async_clients["openai"],
            ),
        )

        # Test query about structuring
        query = "What is structuring in money laundering? Provide a brief definition."

        result = await agents.Runner.run(typology_agent, input=query)

        # Verify response
        assert result is not None
        assert result.final_output is not None

        # Should mention structuring
        response_text = str(result.final_output).lower()
        assert "structur" in response_text  # matches "structuring" or "structure"

        print(f"\n✅ Typology Matcher Response:\n{result.final_output}\n")

    async def test_entity_research_google_search(self, async_clients):
        """Test Entity Research can search Google for entity information."""
        entity_agent = agents.Agent(
            name="EntityResearch",
            instructions=ENTITY_RESEARCH_AGENT_INSTRUCTIONS,
            tools=[
                agents.function_tool(
                    async_clients["gemini"].get_web_search_grounded_response
                ),
            ],
            model=agents.OpenAIChatCompletionsModel(
                model=AGENT_LLM_NAMES["worker"],
                openai_client=async_clients["openai"],
            ),
        )

        # Test query about a known entity
        query = "Search for information about OFAC sanctions list. What is it?"

        result = await agents.Runner.run(entity_agent, input=query)

        # Verify response
        assert result is not None
        assert result.final_output is not None

        response_text = str(result.final_output).lower()
        assert "ofac" in response_text or "sanctions" in response_text

        print(f"\n✅ Entity Research Response:\n{result.final_output}\n")

    async def test_pattern_analyzer_dual_kb(self, async_clients):
        """Test Pattern Analyzer can use both Wikipedia and Google Search."""
        # Create KB worker agent
        kb_agent = agents.Agent(
            name="KnowledgeBaseAgent",
            instructions="You search the knowledge base and return a summary with sources.",
            tools=[
                agents.function_tool(async_clients["kb"].search_knowledgebase),
            ],
            model=agents.OpenAIChatCompletionsModel(
                model=AGENT_LLM_NAMES["worker"],
                openai_client=async_clients["openai"],
            ),
        )

        # Create Pattern Analyzer
        pattern_agent = agents.Agent(
            name="PatternAnalyzer",
            instructions=PATTERN_ANALYZER_AGENT_INSTRUCTIONS,
            tools=[
                kb_agent.as_tool(
                    tool_name="search_knowledgebase",
                    tool_description="Search Wikipedia for pattern analysis concepts",
                ),
                agents.function_tool(
                    async_clients["gemini"].get_web_search_grounded_response
                ),
            ],
            model=agents.OpenAIChatCompletionsModel(
                model=AGENT_LLM_NAMES["worker"],
                openai_client=async_clients["openai"],
            ),
        )

        # Test query about Benford's Law (should use Wikipedia)
        query = "What is Benford's Law and how is it used in fraud detection?"

        result = await agents.Runner.run(pattern_agent, input=query)

        # Verify response
        assert result is not None
        assert result.final_output is not None

        response_text = str(result.final_output).lower()
        assert "benford" in response_text

        print(f"\n✅ Pattern Analyzer Response:\n{result.final_output}\n")

