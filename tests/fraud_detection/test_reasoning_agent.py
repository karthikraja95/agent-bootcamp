"""Tests for Reasoning Agent."""

import pytest
import pytest_asyncio
from dotenv import load_dotenv
from openai import AsyncOpenAI

from src.fraud_detection.agents.reasoning import create_reasoning_agent, run_reasoning_agent
from src.fraud_detection.models import ReasoningOutput

# Load environment variables
load_dotenv(verbose=True)


@pytest_asyncio.fixture(scope="module")
async def openai_client():
    """Create AsyncOpenAI client configured for Gemini."""
    client = AsyncOpenAI()
    yield client
    await client.close()


# ============================================================================
# CREATION TESTS
# ============================================================================


class TestReasoningAgentCreation:
    """Test Reasoning Agent creation and configuration."""

    def test_create_reasoning_agent(self, openai_client):
        """Test that reasoning agent is created with correct configuration."""
        agent = create_reasoning_agent(openai_client)

        assert agent is not None
        assert agent.name == "ReasoningAgent"
        assert agent.output_type == ReasoningOutput
        assert agent.tools == []  # No tools - pure LLM reasoning


# ============================================================================
# STRUCTURE TESTS
# ============================================================================


class TestReasoningOutputStructure:
    """Test ReasoningOutput model structure."""

    def test_reasoning_output_structure(self):
        """Test that ReasoningOutput has all required fields."""
        output = ReasoningOutput(
            evidence_analysis="Detailed analysis of all evidence...",
            incriminating_factors=["Factor 1", "Factor 2"],
            exculpatory_factors=["Factor 3"],
            confidence_score=75.0,
            verdict="SUSPICIOUS",
            verdict_reasoning="Based on the evidence...",
        )

        assert output.evidence_analysis == "Detailed analysis of all evidence..."
        assert len(output.incriminating_factors) == 2
        assert len(output.exculpatory_factors) == 1
        assert output.confidence_score == 75.0
        assert output.verdict == "SUSPICIOUS"
        assert output.verdict_reasoning == "Based on the evidence..."

    def test_reasoning_output_verdict_values(self):
        """Test that verdict accepts only valid literal values."""
        # Valid verdicts
        for verdict in ["LIKELY_FRAUD", "SUSPICIOUS", "LIKELY_LEGITIMATE"]:
            output = ReasoningOutput(
                evidence_analysis="Test",
                incriminating_factors=[],
                exculpatory_factors=[],
                confidence_score=50.0,
                verdict=verdict,
                verdict_reasoning="Test",
            )
            assert output.verdict == verdict

    def test_reasoning_output_confidence_bounds(self):
        """Test that confidence score is bounded 0-100."""
        # Valid confidence scores
        for score in [0.0, 50.0, 100.0]:
            output = ReasoningOutput(
                evidence_analysis="Test",
                incriminating_factors=[],
                exculpatory_factors=[],
                confidence_score=score,
                verdict="SUSPICIOUS",
                verdict_reasoning="Test",
            )
            assert output.confidence_score == score

        # Invalid confidence scores should raise validation error
        with pytest.raises(Exception):  # Pydantic ValidationError
            ReasoningOutput(
                evidence_analysis="Test",
                incriminating_factors=[],
                exculpatory_factors=[],
                confidence_score=150.0,  # > 100
                verdict="SUSPICIOUS",
                verdict_reasoning="Test",
            )


# ============================================================================
# API INTEGRATION TESTS
# ============================================================================


@pytest.mark.slow
@pytest.mark.asyncio
class TestReasoningAgentAPI:
    """Test Reasoning Agent with real API calls."""

    async def test_reasoning_fraud_structuring(self, openai_client):
        """Test reasoning agent on a clear fraud case (structuring)."""
        agent = create_reasoning_agent(openai_client)

        # Simulate outputs from previous agents
        customer_report = """
        Customer: Maya Singh
        Account Type: Personal
        Location: Toronto, Canada
        Profile: Freelance graphic designer
        """

        intake_signals = """
        - Multiple deposits just under $10,000 CAD reporting threshold
        - Frequent round-number transactions
        - High transaction velocity
        """

        typology_matches = """
        1. Structuring (Smurfing) - Confidence: 95%
           Evidence: 15 deposits between $9,500-$9,900 over 30 days
        """

        red_flags = """
        1. Structured deposits to avoid reporting - Severity: HIGH
        2. Round-number transactions - Severity: MEDIUM
        """

        entity_checks = """
        Maya Singh: No adverse media, no sanctions, not a PEP
        """

        result = await run_reasoning_agent(
            agent, customer_report, intake_signals, typology_matches, red_flags, entity_checks
        )

        assert isinstance(result, ReasoningOutput)
        assert result.verdict in ["LIKELY_FRAUD", "SUSPICIOUS"]
        assert result.confidence_score > 60.0
        assert len(result.incriminating_factors) > 0
        assert "structuring" in result.evidence_analysis.lower() or "smurfing" in result.evidence_analysis.lower()

        print(f"\n✅ Reasoning Agent - Fraud Structuring Test:")
        print(f"   Verdict: {result.verdict}")
        print(f"   Confidence: {result.confidence_score}%")
        print(f"   Incriminating Factors: {len(result.incriminating_factors)}")
        print(f"   Exculpatory Factors: {len(result.exculpatory_factors)}")
        print(f"   Reasoning: {result.verdict_reasoning[:100]}...")

    async def test_reasoning_legitimate_freelancer(self, openai_client):
        """Test reasoning agent on a legitimate case (freelancer)."""
        agent = create_reasoning_agent(openai_client)

        # Simulate outputs from previous agents
        customer_report = """
        Customer: Chen Lee
        Account Type: Business
        Location: Vancouver, Canada
        Profile: Freelance software developer with international clients
        """

        intake_signals = """
        - International wire transfers from known tech companies
        - Regular monthly payment patterns
        - Crypto purchases aligned with investment profile
        """

        typology_matches = """
        No strong typology matches found.
        Crypto purchases are consistent with stated investment profile.
        """

        red_flags = """
        No significant red flags identified.
        Activity is consistent with freelance business profile.
        """

        entity_checks = """
        Chen Lee: No adverse media, no sanctions, not a PEP
        Client companies: All legitimate tech firms, no adverse findings
        """

        result = await run_reasoning_agent(
            agent, customer_report, intake_signals, typology_matches, red_flags, entity_checks
        )

        assert isinstance(result, ReasoningOutput)
        assert result.verdict in ["LIKELY_LEGITIMATE", "SUSPICIOUS"]
        assert len(result.exculpatory_factors) > 0
        assert result.evidence_analysis is not None

        print(f"\n✅ Reasoning Agent - Legitimate Freelancer Test:")
        print(f"   Verdict: {result.verdict}")
        print(f"   Confidence: {result.confidence_score}%")
        print(f"   Incriminating Factors: {len(result.incriminating_factors)}")
        print(f"   Exculpatory Factors: {len(result.exculpatory_factors)}")
        print(f"   Reasoning: {result.verdict_reasoning[:100]}...")

    async def test_reasoning_output_completeness(self, openai_client):
        """Test that reasoning agent provides complete output."""
        agent = create_reasoning_agent(openai_client)

        # Minimal test case
        customer_report = "Customer: Test User"
        intake_signals = "No significant signals"
        typology_matches = "No matches"
        red_flags = "No red flags"
        entity_checks = "No adverse findings"

        result = await run_reasoning_agent(
            agent, customer_report, intake_signals, typology_matches, red_flags, entity_checks
        )

        # Verify all required fields are present and non-empty
        assert isinstance(result, ReasoningOutput)
        assert result.evidence_analysis is not None
        assert len(result.evidence_analysis) > 0
        assert result.verdict in ["LIKELY_FRAUD", "SUSPICIOUS", "LIKELY_LEGITIMATE"]
        assert 0.0 <= result.confidence_score <= 100.0
        assert result.verdict_reasoning is not None
        assert len(result.verdict_reasoning) > 0

        print(f"\n✅ Reasoning Agent - Output Completeness Test:")
        print(f"   All required fields present: ✓")
        print(f"   Evidence analysis length: {len(result.evidence_analysis)} chars")
        print(f"   Verdict reasoning length: {len(result.verdict_reasoning)} chars")

