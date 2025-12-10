"""Tests for specialist agents (Typology Matcher, Pattern Analyzer, Entity Research).

This test suite validates the specialist agents that perform focused analysis:
- Typology Matcher: Matches activity against known AML typologies
- Pattern Analyzer: Identifies suspicious transaction patterns
- Entity Research: Researches entities for adverse media, sanctions, PEP status
"""

import pytest
import pytest_asyncio
from openai import AsyncOpenAI

from src.fraud_detection.agents.specialists import (
    create_entity_research_agent,
    create_pattern_analyzer_agent,
    create_typology_matcher_agent,
    run_entity_research_agent,
    run_pattern_analyzer_agent,
    run_typology_matcher_agent,
)
from src.fraud_detection.models import EntityCheckResult, RedFlag, TypologyMatch
from src.utils import (
    AsyncWeaviateKnowledgeBase,
    Configs,
    get_weaviate_async_client,
)
from src.utils.tools.gemini_grounding import GeminiGroundingWithGoogleSearch

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv(verbose=True)
except ImportError:
    pass


@pytest_asyncio.fixture(scope="function")
async def openai_client():
    """Create OpenAI client for testing."""
    client = AsyncOpenAI()
    yield client


@pytest_asyncio.fixture(scope="function")
async def async_knowledgebase():
    """Create AsyncWeaviateKnowledgeBase for testing."""
    configs = Configs.from_env_var()
    async_weaviate_client = get_weaviate_async_client(
        http_host=configs.weaviate_http_host,
        http_port=configs.weaviate_http_port,
        http_secure=configs.weaviate_http_secure,
        grpc_host=configs.weaviate_grpc_host,
        grpc_port=configs.weaviate_grpc_port,
        grpc_secure=configs.weaviate_grpc_secure,
        api_key=configs.weaviate_api_key,
    )
    kb = AsyncWeaviateKnowledgeBase(
        async_weaviate_client,
        collection_name="enwiki_20250520",
    )
    yield kb


@pytest_asyncio.fixture(scope="function")
async def gemini_grounding():
    """Create GeminiGroundingWithGoogleSearch for testing."""
    return GeminiGroundingWithGoogleSearch()


@pytest.mark.asyncio
class TestTypologyMatcherCreation:
    """Test Typology Matcher Agent creation and structure."""

    async def test_create_typology_matcher_agent(
        self, openai_client, async_knowledgebase, gemini_grounding
    ):
        """Test that Typology Matcher Agent can be created."""
        agent = create_typology_matcher_agent(
            openai_client, async_knowledgebase, gemini_grounding
        )

        assert agent is not None
        assert agent.name == "TypologyMatcher"
        assert len(agent.tools) == 2  # Wikipedia + Google Search
        # Note: output_type is None because Gemini doesn't support structured output with tools
        assert agent.output_type is None


@pytest.mark.asyncio
class TestPatternAnalyzerCreation:
    """Test Pattern Analyzer Agent creation and structure."""

    async def test_create_pattern_analyzer_agent(
        self, openai_client, async_knowledgebase, gemini_grounding
    ):
        """Test that Pattern Analyzer Agent can be created."""
        agent = create_pattern_analyzer_agent(
            openai_client, async_knowledgebase, gemini_grounding
        )

        assert agent is not None
        assert agent.name == "PatternAnalyzer"
        assert len(agent.tools) == 2  # Wikipedia + Google Search
        # Note: output_type is None because Gemini doesn't support structured output with tools
        assert agent.output_type is None


@pytest.mark.asyncio
class TestEntityResearchCreation:
    """Test Entity Research Agent creation and structure."""

    async def test_create_entity_research_agent(self, openai_client, gemini_grounding):
        """Test that Entity Research Agent can be created."""
        agent = create_entity_research_agent(openai_client, gemini_grounding)

        assert agent is not None
        assert agent.name == "EntityResearch"
        assert len(agent.tools) == 1  # Google Search only
        # Note: output_type is None because Gemini doesn't support structured output with tools
        assert agent.output_type is None


@pytest.mark.slow
@pytest.mark.asyncio
class TestTypologyMatcherAPI:
    """Test Typology Matcher Agent with real API calls."""

    async def test_typology_matcher_structuring(
        self, openai_client, async_knowledgebase, gemini_grounding
    ):
        """Test typology matching for structuring pattern."""
        agent = create_typology_matcher_agent(
            openai_client, async_knowledgebase, gemini_grounding
        )

        query = (
            "Check if the pattern of multiple £7,500 transfers to offshore exchanges "
            "matches the 'structuring' or 'smurfing' AML typology. "
            "The customer made 8 transfers of exactly £7,500 each over 2 months."
        )

        matches = await run_typology_matcher_agent(agent, query)

        assert isinstance(matches, list)
        assert len(matches) > 0
        assert all(isinstance(m, TypologyMatch) for m in matches)

        # Should identify structuring
        structuring_match = next((m for m in matches if "structur" in m.name.lower()), None)
        assert structuring_match is not None, "Should identify structuring typology"

        print(f"\n✅ Typology Matcher - Structuring Test:")
        for match in matches:
            print(f"   {match.name}: matched={match.matched}, confidence={match.confidence:.2f}")
            print(f"   Source: {match.source[:80]}...")


@pytest.mark.slow
@pytest.mark.asyncio
class TestPatternAnalyzerAPI:
    """Test Pattern Analyzer Agent with real API calls."""

    async def test_pattern_analyzer_threshold_avoidance(
        self, openai_client, async_knowledgebase, gemini_grounding
    ):
        """Test pattern analysis for threshold avoidance."""
        agent = create_pattern_analyzer_agent(
            openai_client, async_knowledgebase, gemini_grounding
        )

        query = (
            "Analyze the following transaction pattern for red flags: "
            "Customer made 8 cash deposits of exactly £7,500 each over 2 months, "
            "all just below the £10,000 reporting threshold. "
            "Deposits occurred on different days but with regular spacing."
        )

        red_flags = await run_pattern_analyzer_agent(agent, query)

        assert isinstance(red_flags, list)
        assert len(red_flags) > 0
        assert all(isinstance(rf, RedFlag) for rf in red_flags)

        # Should identify high-severity red flags
        high_severity = [rf for rf in red_flags if rf.severity == "high"]
        assert len(high_severity) > 0, "Should identify at least one high-severity red flag"

        print(f"\n✅ Pattern Analyzer - Threshold Avoidance Test:")
        for flag in red_flags:
            print(f"   [{flag.severity.upper()}] {flag.description[:80]}...")
            print(f"   Evidence: {flag.evidence[:80]}...")

    async def test_pattern_analyzer_legitimate_activity(
        self, openai_client, async_knowledgebase, gemini_grounding
    ):
        """Test pattern analysis for legitimate activity."""
        agent = create_pattern_analyzer_agent(
            openai_client, async_knowledgebase, gemini_grounding
        )

        query = (
            "Analyze the following transaction pattern: "
            "Freelance software developer receives international wire transfers "
            "from 3 different clients (Google, Microsoft, Amazon) ranging from "
            "$5,000 to $15,000 per month. Transfers are irregular but align with "
            "project completion dates. Customer has consistent business profile."
        )

        red_flags = await run_pattern_analyzer_agent(agent, query)

        assert isinstance(red_flags, list)
        # Legitimate activity may have 0 red flags or only low-severity ones
        if len(red_flags) > 0:
            high_severity = [rf for rf in red_flags if rf.severity == "high"]
            assert len(high_severity) == 0, "Legitimate activity should not have high-severity flags"

        print(f"\n✅ Pattern Analyzer - Legitimate Activity Test:")
        print(f"   Red flags found: {len(red_flags)}")
        for flag in red_flags:
            print(f"   [{flag.severity.upper()}] {flag.description[:80]}...")


@pytest.mark.slow
@pytest.mark.asyncio
class TestEntityResearchAPI:
    """Test Entity Research Agent with real API calls."""

    async def test_entity_research_legitimate_company(
        self, openai_client, gemini_grounding
    ):
        """Test entity research for a legitimate company."""
        agent = create_entity_research_agent(openai_client, gemini_grounding)

        query = (
            "Research 'Microsoft Corporation' for adverse media, sanctions, or PEP status. "
            "Check if this is a legitimate business entity."
        )

        results = await run_entity_research_agent(agent, query)

        assert isinstance(results, list)
        assert len(results) > 0
        assert all(isinstance(r, EntityCheckResult) for r in results)

        # Verify structure and sources
        company_result = results[0]
        assert company_result.entity_name is not None
        assert len(company_result.sources) > 0, "Should provide sources"
        # Note: We don't assert specific findings as legitimate companies may have
        # regulatory issues, lawsuits, etc. that could be flagged as adverse media

        print(f"\n✅ Entity Research - Legitimate Company Test:")
        for result in results:
            print(f"   Entity: {result.entity_name}")
            print(f"   Adverse Media: {result.adverse_media}")
            print(f"   Sanctions: {result.sanctions_hit}")
            print(f"   PEP: {result.pep_status}")
            print(f"   Findings: {result.findings[:100]}...")

    async def test_entity_research_high_risk_jurisdiction(
        self, openai_client, gemini_grounding
    ):
        """Test entity research for high-risk jurisdiction entity."""
        agent = create_entity_research_agent(openai_client, gemini_grounding)

        query = (
            "Research 'DigitalGulf Exchange' (cryptocurrency exchange based in UAE) "
            "for adverse media, regulatory actions, or sanctions. "
            "Check if this exchange has any compliance issues."
        )

        results = await run_entity_research_agent(agent, query)

        assert isinstance(results, list)
        assert len(results) > 0
        assert all(isinstance(r, EntityCheckResult) for r in results)

        print(f"\n✅ Entity Research - High-Risk Jurisdiction Test:")
        for result in results:
            print(f"   Entity: {result.entity_name}")
            print(f"   Type: {result.entity_type}")
            print(f"   Findings: {result.findings[:150]}...")
            print(f"   Sources: {len(result.sources)} sources")


class TestSpecialistOutputStructure:
    """Test that specialist agents return properly structured outputs."""

    def test_typology_match_structure(self):
        """Test TypologyMatch model structure."""
        match = TypologyMatch(
            name="Structuring",
            matched=True,
            confidence=0.85,
            explanation="Pattern matches structuring typology",
            source="Wikipedia: Structuring (money laundering)",
        )

        assert match.name == "Structuring"
        assert match.matched is True
        assert 0.0 <= match.confidence <= 1.0
        assert len(match.explanation) > 0
        assert len(match.source) > 0

    def test_red_flag_structure(self):
        """Test RedFlag model structure."""
        flag = RedFlag(
            description="Multiple transactions just below reporting threshold",
            severity="high",
            evidence="8 deposits of £7,500 each over 2 months",
            source="FATF Guidance on Structuring",
        )

        assert flag.severity in ["high", "medium", "low"]
        assert len(flag.description) > 0
        assert len(flag.evidence) > 0

    def test_entity_check_result_structure(self):
        """Test EntityCheckResult model structure."""
        result = EntityCheckResult(
            entity_name="Google LLC",
            entity_type="business",
            adverse_media=False,
            sanctions_hit=False,
            pep_status=False,
            findings="No adverse information found",
            sources=["https://www.google.com/about/"],
        )

        assert result.entity_type in ["customer", "business", "counterparty"]
        assert isinstance(result.adverse_media, bool)
        assert isinstance(result.sanctions_hit, bool)
        assert isinstance(result.pep_status, bool)
        assert len(result.findings) > 0

