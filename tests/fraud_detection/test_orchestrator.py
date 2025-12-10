"""Tests for Fraud Detection Orchestrator."""

from pathlib import Path

import pytest
import pytest_asyncio
from dotenv import load_dotenv
from openai import AsyncOpenAI

from src.fraud_detection.orchestrator import (
    analyze_fraud_report,
    analyze_fraud_report_with_progress,
)
from src.fraud_detection.models import FraudAssessment
from src.utils.env_vars import Configs
from src.utils.tools.gemini_grounding import GeminiGroundingWithGoogleSearch
from src.utils.tools.kb_weaviate import AsyncWeaviateKnowledgeBase, get_weaviate_async_client

# Load environment variables
load_dotenv(verbose=True)

# Path to test data
TEST_DATA_DIR = Path(__file__).parent.parent.parent / "test_data"


@pytest_asyncio.fixture(scope="module")
async def openai_client():
    """Create AsyncOpenAI client configured for Gemini."""
    client = AsyncOpenAI()
    yield client
    await client.close()


@pytest_asyncio.fixture(scope="module")
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
    await async_weaviate_client.close()


@pytest_asyncio.fixture(scope="module")
async def gemini_grounding():
    """Create GeminiGroundingWithGoogleSearch for testing."""
    return GeminiGroundingWithGoogleSearch()


# ============================================================================
# INTEGRATION TESTS
# ============================================================================


@pytest.mark.slow
class TestOrchestratorIntegration:
    """Test orchestrator with real API calls."""

    @pytest.mark.asyncio
    async def test_orchestrator_fraud_structuring(
        self, openai_client, async_knowledgebase, gemini_grounding
    ):
        """Test complete pipeline with fraud structuring case."""
        # Load real test data file
        file_path = TEST_DATA_DIR / "case_03_fraud_structuring.txt"
        raw_report = file_path.read_text(encoding="utf-8")

        # Run complete pipeline
        result = await analyze_fraud_report(
            raw_report, openai_client, async_knowledgebase, gemini_grounding
        )

        # Verify output structure
        assert isinstance(result, FraudAssessment)
        assert result.verdict in ["LIKELY_FRAUD", "SUSPICIOUS", "LIKELY_LEGITIMATE"]
        assert 0 <= result.confidence_score <= 100
        assert len(result.risk_summary) > 50

        # For structuring case, expect high suspicion
        assert result.verdict in ["LIKELY_FRAUD", "SUSPICIOUS"]
        assert result.confidence_score >= 60

        print(f"\n✅ Orchestrator - Fraud Structuring Test:")
        print(f"   Verdict: {result.verdict}")
        print(f"   Confidence: {result.confidence_score}%")
        print(f"   Typologies: {len(result.typologies)}")
        print(f"   Red Flags: {len(result.red_flags)}")
        print(f"   Entity Checks: {len(result.entity_checks)}")
        print(f"   Recommended Actions: {len(result.recommended_actions)}")

    @pytest.mark.asyncio
    async def test_orchestrator_legitimate_freelancer(
        self, openai_client, async_knowledgebase, gemini_grounding
    ):
        """Test complete pipeline with legitimate freelancer case."""
        # Load real test data file
        file_path = TEST_DATA_DIR / "case_01_legitimate_freelancer.txt"
        raw_report = file_path.read_text(encoding="utf-8")

        # Run complete pipeline
        result = await analyze_fraud_report(
            raw_report, openai_client, async_knowledgebase, gemini_grounding
        )

        # Verify output structure
        assert isinstance(result, FraudAssessment)
        assert result.verdict in ["LIKELY_FRAUD", "SUSPICIOUS", "LIKELY_LEGITIMATE"]
        assert 0 <= result.confidence_score <= 100
        assert len(result.risk_summary) > 50

        # For legitimate case, expect low suspicion
        assert result.verdict in ["LIKELY_LEGITIMATE", "SUSPICIOUS"]
        assert len(result.mitigating_factors) > 0

        print(f"\n✅ Orchestrator - Legitimate Freelancer Test:")
        print(f"   Verdict: {result.verdict}")
        print(f"   Confidence: {result.confidence_score}%")
        print(f"   Mitigating Factors: {len(result.mitigating_factors)}")
        print(f"   Recommended Actions: {len(result.recommended_actions)}")

    @pytest.mark.asyncio
    async def test_orchestrator_with_progress_callback(
        self, openai_client, async_knowledgebase, gemini_grounding
    ):
        """Test orchestrator with progress callback."""
        # Load real test data file (use a smaller case for faster testing)
        file_path = TEST_DATA_DIR / "case_01_legitimate_freelancer.txt"
        raw_report = file_path.read_text(encoding="utf-8")

        # Track progress updates
        progress_updates = []

        def progress_callback(stage: str, message: str):
            progress_updates.append((stage, message))
            print(f"   [{stage}] {message}")

        # Run with progress callback
        result = await analyze_fraud_report_with_progress(
            raw_report,
            openai_client,
            async_knowledgebase,
            gemini_grounding,
            progress_callback=progress_callback,
        )

        # Verify output
        assert isinstance(result, FraudAssessment)
        assert result.verdict in ["LIKELY_FRAUD", "SUSPICIOUS", "LIKELY_LEGITIMATE"]

        # Verify progress updates were called
        assert len(progress_updates) > 0
        stages = [stage for stage, _ in progress_updates]
        assert "intake" in stages
        assert "planning" in stages
        assert "specialists" in stages
        assert "reasoning" in stages
        assert "report" in stages

        print(f"\n✅ Orchestrator - Progress Callback Test:")
        print(f"   Total progress updates: {len(progress_updates)}")
        print(f"   Stages tracked: {set(stages)}")
        print(f"   Final verdict: {result.verdict}")


# ============================================================================
# UNIT TESTS
# ============================================================================


class TestOrchestratorStructure:
    """Test orchestrator structure and configuration."""

    def test_orchestrator_functions_exist(self):
        """Test that orchestrator functions are defined."""
        assert callable(analyze_fraud_report)
        assert callable(analyze_fraud_report_with_progress)

    def test_orchestrator_function_signatures(self):
        """Test that orchestrator functions have correct signatures."""
        import inspect

        # Check analyze_fraud_report signature
        sig = inspect.signature(analyze_fraud_report)
        params = list(sig.parameters.keys())
        assert "raw_report" in params
        assert "openai_client" in params
        assert "async_knowledgebase" in params
        assert "gemini_grounding" in params

        # Check analyze_fraud_report_with_progress signature
        sig = inspect.signature(analyze_fraud_report_with_progress)
        params = list(sig.parameters.keys())
        assert "raw_report" in params
        assert "openai_client" in params
        assert "async_knowledgebase" in params
        assert "gemini_grounding" in params
        assert "progress_callback" in params

