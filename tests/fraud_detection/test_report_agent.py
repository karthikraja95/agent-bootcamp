"""Tests for Report Agent."""

import pytest
import pytest_asyncio
from dotenv import load_dotenv
from openai import AsyncOpenAI

from src.fraud_detection.agents.report import create_report_agent, run_report_agent
from src.fraud_detection.models import FraudAssessment, RedFlag, TypologyMatch, EntityCheckResult

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


class TestReportAgentCreation:
    """Test Report Agent creation and configuration."""

    def test_create_report_agent(self, openai_client):
        """Test that report agent is created with correct configuration."""
        agent = create_report_agent(openai_client)

        assert agent is not None
        assert agent.name == "ReportAgent"
        assert agent.output_type == FraudAssessment
        assert agent.tools == []  # No tools - pure report generation


# ============================================================================
# STRUCTURE TESTS
# ============================================================================


class TestFraudAssessmentStructure:
    """Test FraudAssessment model structure."""

    def test_fraud_assessment_structure(self):
        """Test that FraudAssessment has all required fields."""
        assessment = FraudAssessment(
            verdict="SUSPICIOUS",
            confidence_score=75.0,
            risk_summary="Customer exhibits suspicious patterns...",
            typologies=[],
            red_flags=[],
            entity_checks=[],
            mitigating_factors=["Legitimate business profile"],
            recommended_actions=["Enhanced due diligence"],
            sources=["Wikipedia: Structuring", "Google Search: AML typologies"],
        )

        assert assessment.verdict == "SUSPICIOUS"
        assert assessment.confidence_score == 75.0
        assert assessment.risk_summary == "Customer exhibits suspicious patterns..."
        assert len(assessment.mitigating_factors) == 1
        assert len(assessment.recommended_actions) == 1
        assert len(assessment.sources) == 2

    def test_fraud_assessment_verdict_values(self):
        """Test that verdict accepts only valid literal values."""
        # Valid verdicts
        for verdict in ["LIKELY_FRAUD", "SUSPICIOUS", "LIKELY_LEGITIMATE"]:
            assessment = FraudAssessment(
                verdict=verdict,
                confidence_score=50.0,
                risk_summary="Test summary",
            )
            assert assessment.verdict == verdict

    def test_fraud_assessment_confidence_bounds(self):
        """Test that confidence score is bounded 0-100."""
        # Valid confidence scores
        for score in [0.0, 50.0, 100.0]:
            assessment = FraudAssessment(
                verdict="SUSPICIOUS",
                confidence_score=score,
                risk_summary="Test",
            )
            assert assessment.confidence_score == score

        # Invalid confidence scores should raise validation error
        with pytest.raises(Exception):  # Pydantic ValidationError
            FraudAssessment(
                verdict="SUSPICIOUS",
                confidence_score=150.0,  # > 100
                risk_summary="Test",
            )


# ============================================================================
# API INTEGRATION TESTS
# ============================================================================


@pytest.mark.slow
class TestReportAgentAPI:
    """Test Report Agent with real API calls."""

    @pytest_asyncio.fixture(scope="class")
    async def report_agent(self, openai_client):
        """Create Report Agent for testing."""
        return create_report_agent(openai_client)

    @pytest.mark.asyncio
    async def test_report_fraud_structuring(self, report_agent):
        """Test report generation for fraud structuring case."""
        # Mock inputs from previous agents
        customer_report = """
        Customer: Maya Singh
        Account: ACC-2024-001
        Period: Jan 2024
        
        Transactions:
        - Jan 5: Deposit $9,500 (cash)
        - Jan 12: Deposit $9,800 (cash)
        - Jan 19: Deposit $9,700 (cash)
        - Jan 26: Deposit $9,900 (cash)
        
        Total: $38,900 in cash deposits
        """

        intake_signals = """
        Risk Level: HIGH
        Key Signals:
        - Multiple cash deposits just below $10,000 threshold
        - Consistent pattern over 4 weeks
        - Round-number amounts
        """

        typology_matches = """
        Matched Typologies:
        1. Structuring (Smurfing) - Confidence: 0.95
           Evidence: Four cash deposits between $9,500-$9,900, all below $10,000 reporting threshold
        """

        red_flags = """
        Red Flags Identified:
        1. Threshold Avoidance - Severity: HIGH
           Pattern: Deposits consistently just below $10,000 CTR threshold
        2. Round Numbers - Severity: MEDIUM
           Pattern: All amounts are round hundreds ($9,500, $9,800, etc.)
        """

        entity_checks = """
        Entity Check Results:
        - Maya Singh: No adverse media found
        - Business: Legitimate registered business
        """

        reasoning_output = """
        Verdict: SUSPICIOUS
        Confidence: 95%
        
        Incriminating Factors:
        - Clear structuring pattern to avoid CTR reporting
        - Consistent timing and amounts
        - High-value cash deposits
        - Round number amounts
        
        Exculpatory Factors:
        - No adverse media
        - Legitimate business registration
        """

        # Run report agent
        result = await run_report_agent(
            report_agent,
            customer_report,
            intake_signals,
            typology_matches,
            red_flags,
            entity_checks,
            reasoning_output,
        )

        # Verify output structure
        assert isinstance(result, FraudAssessment)
        assert result.verdict in ["LIKELY_FRAUD", "SUSPICIOUS"]
        assert result.confidence_score >= 70.0  # Should be high confidence
        assert len(result.risk_summary) > 50  # Should have substantial summary
        
        print(f"\n✅ Report Agent - Fraud Structuring Test:")
        print(f"   Verdict: {result.verdict}")
        print(f"   Confidence: {result.confidence_score}%")
        print(f"   Recommended Actions: {len(result.recommended_actions)}")
        print(f"   Summary: {result.risk_summary[:100]}...")

    @pytest.mark.asyncio
    async def test_report_legitimate_freelancer(self, report_agent):
        """Test report generation for legitimate freelancer case."""
        # Mock inputs from previous agents
        customer_report = """
        Customer: Chen Lee
        Account: ACC-2024-002
        Business: Freelance Software Developer
        Period: Jan 2024

        Transactions:
        - Jan 10: Deposit $3,500 (wire from TechCorp Inc)
        - Jan 15: Deposit $2,800 (wire from StartupXYZ)
        - Jan 25: Deposit $4,200 (wire from Enterprise Solutions)

        Total: $10,500 in business payments
        """

        intake_signals = """
        Risk Level: LOW
        Key Signals:
        - All transactions are wire transfers from known companies
        - Amounts vary naturally
        - Consistent with freelance business model
        """

        typology_matches = """
        Matched Typologies: None
        No AML typologies matched.
        """

        red_flags = """
        Red Flags Identified: None
        No suspicious patterns detected.
        """

        entity_checks = """
        Entity Check Results:
        - Chen Lee: No adverse media, legitimate freelancer
        - TechCorp Inc: Established company, no red flags
        - StartupXYZ: Legitimate startup, no concerns
        - Enterprise Solutions: Reputable company
        """

        reasoning_output = """
        Verdict: LIKELY_LEGITIMATE
        Confidence: 98%

        Incriminating Factors: None

        Exculpatory Factors:
        - All payments from legitimate businesses
        - Amounts consistent with freelance work
        - No adverse media findings
        - Natural variation in payment amounts
        - Transparent business model
        """

        # Run report agent
        result = await run_report_agent(
            report_agent,
            customer_report,
            intake_signals,
            typology_matches,
            red_flags,
            entity_checks,
            reasoning_output,
        )

        # Verify output structure
        assert isinstance(result, FraudAssessment)
        assert result.verdict == "LIKELY_LEGITIMATE"
        assert result.confidence_score >= 90.0  # Should be very high confidence
        assert len(result.risk_summary) > 50
        assert len(result.mitigating_factors) > 0  # Should have mitigating factors

        print(f"\n✅ Report Agent - Legitimate Freelancer Test:")
        print(f"   Verdict: {result.verdict}")
        print(f"   Confidence: {result.confidence_score}%")
        print(f"   Mitigating Factors: {len(result.mitigating_factors)}")
        print(f"   Summary: {result.risk_summary[:100]}...")

    @pytest.mark.asyncio
    async def test_report_output_completeness(self, report_agent):
        """Test that report output contains all required fields."""
        # Simple test case
        customer_report = "Customer: Test User\nTransactions: $5,000 deposit"
        intake_signals = "Risk: MEDIUM"
        typology_matches = "None"
        red_flags = "None"
        entity_checks = "No issues"
        reasoning_output = "Verdict: SUSPICIOUS, Confidence: 60%"

        result = await run_report_agent(
            report_agent,
            customer_report,
            intake_signals,
            typology_matches,
            red_flags,
            entity_checks,
            reasoning_output,
        )

        # Verify all required fields are present
        assert result.verdict is not None
        assert result.confidence_score is not None
        assert result.risk_summary is not None
        assert isinstance(result.typologies, list)
        assert isinstance(result.red_flags, list)
        assert isinstance(result.entity_checks, list)
        assert isinstance(result.mitigating_factors, list)
        assert isinstance(result.recommended_actions, list)
        assert isinstance(result.sources, list)

        print(f"\n✅ Report Agent - Output Completeness Test:")
        print(f"   All required fields present: ✓")
        print(f"   Risk summary length: {len(result.risk_summary)} chars")
        print(f"   Recommended actions: {len(result.recommended_actions)}")

