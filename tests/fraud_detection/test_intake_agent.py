"""Tests for the Intake Agent."""

import pytest
import pytest_asyncio
from dotenv import load_dotenv
from openai import AsyncOpenAI

from src.fraud_detection.agents.intake import (
    IntakeOutput,
    create_intake_agent,
    run_intake_agent,
)
from src.fraud_detection.document_loader import load_customer_report

# Load environment variables
load_dotenv(verbose=True)


@pytest_asyncio.fixture(scope="module")
async def openai_client():
    """Create OpenAI client for testing."""
    client = AsyncOpenAI()
    yield client
    await client.close()


@pytest_asyncio.fixture(scope="module")
def intake_agent(openai_client):
    """Create Intake Agent for testing."""
    return create_intake_agent(openai_client)


class TestIntakeAgentCreation:
    """Test Intake Agent creation."""

    def test_create_intake_agent(self, openai_client):
        """Test that we can create an Intake Agent."""
        agent = create_intake_agent(openai_client)
        
        assert agent is not None
        assert agent.name == "IntakeAgent"
        assert agent.output_type == IntakeOutput


class TestIntakeAgentStructure:
    """Test Intake Agent output structure."""

    @pytest.mark.asyncio
    async def test_intake_output_structure(self):
        """Test that IntakeOutput has the correct structure."""
        from src.fraud_detection.models import (
            CustomerProfile,
            FinancialSummary,
            Transaction,
            CustomerReport,
            ExtractedSignal,
        )
        
        # Create a minimal valid IntakeOutput
        output = IntakeOutput(
            customer_report=CustomerReport(
                profile=CustomerProfile(
                    customer_id="TEST001",
                    name="Test Customer",
                    account_type="Personal",
                    opening_date="2024-01-01",
                    location="Toronto, ON",
                    investment_profile="Conservative",
                    document_date="2024-12-01",
                    time_period="January 1 - November 30, 2024",
                ),
                history_overview="Test history",
                transactions=[
                    Transaction(
                        date="2024-01-15",
                        type="Deposit",
                        description="Test deposit",
                        fiat_amount=1000.0,
                    )
                ],
                financial_summary=FinancialSummary(
                    total_deposits=1000.0,
                    total_non_crypto_spend=0.0,
                    total_crypto_buys=0.0,
                    net_crypto_holdings=[],
                ),
            ),
            signals=[
                ExtractedSignal(
                    signal_type="test_signal",
                    value="test",
                    risk_indicator="neutral",
                    explanation="Test signal",
                )
            ],
            risk_areas_to_investigate=["Test area"],
        )
        
        assert output.customer_report is not None
        assert len(output.signals) == 1
        assert len(output.risk_areas_to_investigate) == 1


@pytest.mark.slow
@pytest.mark.asyncio
class TestIntakeAgentAPI:
    """Test Intake Agent with real API calls."""

    async def test_intake_legitimate_freelancer(self, intake_agent):
        """Test Intake Agent on legitimate freelancer case."""
        # Load the legitimate freelancer case
        report = load_customer_report("test_data/case_01_legitimate_freelancer.txt")
        
        # Run the intake agent
        result = await run_intake_agent(intake_agent, report)
        
        # Verify structure
        assert result is not None
        assert isinstance(result, IntakeOutput)
        assert result.customer_report is not None
        assert len(result.signals) > 0
        assert len(result.risk_areas_to_investigate) > 0
        
        # Verify customer profile was extracted
        assert result.customer_report.profile.customer_id == "CUST-10044"
        assert "Chen" in result.customer_report.profile.name
        assert "Business" in result.customer_report.profile.account_type
        
        # Verify signals were extracted
        signal_types = [s.signal_type for s in result.signals]
        print(f"\n✅ Extracted {len(result.signals)} signals:")
        for signal in result.signals:
            print(f"  - {signal.signal_type} ({signal.risk_indicator}): {signal.explanation[:80]}...")
        
        # Should have some signals
        assert len(signal_types) >= 3
        
        # Verify risk areas
        print(f"\n✅ Risk areas to investigate ({len(result.risk_areas_to_investigate)}):")
        for area in result.risk_areas_to_investigate:
            print(f"  - {area}")
        
        assert len(result.risk_areas_to_investigate) >= 2

    async def test_intake_fraud_structuring(self, intake_agent):
        """Test Intake Agent on fraud structuring case."""
        # Load the fraud structuring case
        report = load_customer_report("test_data/case_03_fraud_structuring.txt")
        
        # Run the intake agent
        result = await run_intake_agent(intake_agent, report)
        
        # Verify structure
        assert result is not None
        assert isinstance(result, IntakeOutput)
        
        # Verify customer profile
        assert result.customer_report.profile.customer_id == "CUST-10043"
        assert "Maya" in result.customer_report.profile.name
        
        # Verify signals - should have negative indicators for fraud case
        negative_signals = [s for s in result.signals if s.risk_indicator == "negative"]
        print(f"\n✅ Extracted {len(negative_signals)} negative signals:")
        for signal in negative_signals:
            print(f"  - {signal.signal_type}: {signal.explanation[:80]}...")
        
        # Fraud case should have multiple negative signals
        assert len(negative_signals) >= 2
        
        # Verify risk areas mention structuring or similar patterns
        risk_text = " ".join(result.risk_areas_to_investigate).lower()
        print(f"\n✅ Risk areas: {result.risk_areas_to_investigate}")
        
        # Should mention suspicious patterns
        assert any(
            keyword in risk_text
            for keyword in ["structur", "pattern", "suspicious", "frequent", "small"]
        )

