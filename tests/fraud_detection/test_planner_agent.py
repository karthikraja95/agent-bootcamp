"""Tests for the Planner Agent."""

import pytest
import pytest_asyncio
from dotenv import load_dotenv
from openai import AsyncOpenAI

from src.fraud_detection.agents.intake import (
    IntakeOutput,
    create_intake_agent,
    run_intake_agent,
)
from src.fraud_detection.agents.planner import (
    create_planner_agent,
    run_planner_agent,
)
from src.fraud_detection.document_loader import load_customer_report
from src.fraud_detection.models import InvestigationPlan

# Load environment variables
load_dotenv(verbose=True)


@pytest_asyncio.fixture(scope="module")
async def openai_client():
    """Create OpenAI client for testing."""
    client = AsyncOpenAI()
    yield client
    await client.close()


@pytest_asyncio.fixture(scope="module")
def planner_agent(openai_client):
    """Create Planner Agent for testing."""
    return create_planner_agent(openai_client)


@pytest_asyncio.fixture(scope="module")
def intake_agent(openai_client):
    """Create Intake Agent for testing."""
    return create_intake_agent(openai_client)


class TestPlannerAgentCreation:
    """Test Planner Agent creation."""

    def test_create_planner_agent(self, openai_client):
        """Test that we can create a Planner Agent."""
        agent = create_planner_agent(openai_client)
        
        assert agent is not None
        assert agent.name == "PlannerAgent"
        assert agent.output_type == InvestigationPlan


class TestPlannerAgentStructure:
    """Test Planner Agent output structure."""

    @pytest.mark.asyncio
    async def test_investigation_plan_structure(self):
        """Test that InvestigationPlan has the correct structure."""
        # Create a minimal valid InvestigationPlan
        plan = InvestigationPlan(
            typology_queries=["structuring definition"],
            pattern_queries=["AML red flags"],
            entities_to_check=["Test Customer"],
            entity_queries=["Test Customer sanctions"],
            priority_areas=["Transaction patterns"],
            initial_risk_assessment="medium",
            reasoning="Test reasoning",
        )
        
        assert plan.typology_queries == ["structuring definition"]
        assert plan.pattern_queries == ["AML red flags"]
        assert plan.entities_to_check == ["Test Customer"]
        assert plan.entity_queries == ["Test Customer sanctions"]
        assert plan.priority_areas == ["Transaction patterns"]
        assert plan.initial_risk_assessment == "medium"
        assert plan.reasoning == "Test reasoning"


@pytest.mark.slow
@pytest.mark.asyncio
class TestPlannerAgentAPI:
    """Test Planner Agent with real API calls."""

    async def test_planner_legitimate_freelancer(self, intake_agent, planner_agent):
        """Test Planner Agent on legitimate freelancer case."""
        # Load the legitimate freelancer case
        report = load_customer_report("test_data/case_01_legitimate_freelancer.txt")
        
        # Run intake agent first
        intake_result = await run_intake_agent(intake_agent, report)
        
        # Run the planner agent
        plan = await run_planner_agent(planner_agent, intake_result)
        
        # Verify structure
        assert plan is not None
        assert isinstance(plan, InvestigationPlan)
        
        # Verify plan has queries
        print(f"\n✅ Investigation Plan for Chen Lee (Legitimate Freelancer):")
        print(f"  Initial Risk Assessment: {plan.initial_risk_assessment}")
        print(f"  Reasoning: {plan.reasoning[:100]}...")
        
        # Should have some queries
        total_queries = (
            len(plan.typology_queries)
            + len(plan.pattern_queries)
            + len(plan.entity_queries)
        )
        assert total_queries >= 3, "Should have at least 3 queries total"
        
        # Print typology queries
        if plan.typology_queries:
            print(f"\n  Typology Queries ({len(plan.typology_queries)}):")
            for query in plan.typology_queries:
                print(f"    - {query}")
        
        # Print pattern queries
        if plan.pattern_queries:
            print(f"\n  Pattern Queries ({len(plan.pattern_queries)}):")
            for query in plan.pattern_queries:
                print(f"    - {query}")
        
        # Print entity queries
        if plan.entities_to_check:
            print(f"\n  Entities to Check ({len(plan.entities_to_check)}):")
            for entity in plan.entities_to_check:
                print(f"    - {entity}")
        
        if plan.entity_queries:
            print(f"\n  Entity Queries ({len(plan.entity_queries)}):")
            for query in plan.entity_queries:
                print(f"    - {query}")
        
        # Print priority areas
        if plan.priority_areas:
            print(f"\n  Priority Areas ({len(plan.priority_areas)}):")
            for area in plan.priority_areas:
                print(f"    - {area}")
        
        # Should have entities to check (customer, business)
        assert len(plan.entities_to_check) >= 1, "Should have at least 1 entity to check"

        # Should have priority areas
        assert len(plan.priority_areas) >= 1, "Should have at least 1 priority area"

    async def test_planner_fraud_structuring(self, intake_agent, planner_agent):
        """Test Planner Agent on fraud structuring case."""
        # Load the fraud structuring case
        report = load_customer_report("test_data/case_03_fraud_structuring.txt")

        # Run intake agent first
        intake_result = await run_intake_agent(intake_agent, report)

        # Run the planner agent
        plan = await run_planner_agent(planner_agent, intake_result)

        # Verify structure
        assert plan is not None
        assert isinstance(plan, InvestigationPlan)

        print(f"\n✅ Investigation Plan for Maya Singh (Fraud - Structuring):")
        print(f"  Initial Risk Assessment: {plan.initial_risk_assessment}")
        print(f"  Reasoning: {plan.reasoning[:100]}...")

        # Fraud case should have higher risk assessment
        assert plan.initial_risk_assessment in [
            "medium",
            "high",
        ], "Fraud case should have medium or high risk assessment"

        # Should have typology queries (likely including structuring)
        assert len(plan.typology_queries) >= 1, "Should have typology queries for fraud case"

        print(f"\n  Typology Queries ({len(plan.typology_queries)}):")
        for query in plan.typology_queries:
            print(f"    - {query}")

        # Should have pattern queries
        assert len(plan.pattern_queries) >= 1, "Should have pattern queries"

        print(f"\n  Pattern Queries ({len(plan.pattern_queries)}):")
        for query in plan.pattern_queries:
            print(f"    - {query}")

        # Should have entities to check
        assert len(plan.entities_to_check) >= 1, "Should have entities to check"

        print(f"\n  Entities to Check ({len(plan.entities_to_check)}):")
        for entity in plan.entities_to_check:
            print(f"    - {entity}")

        # Should have priority areas
        assert len(plan.priority_areas) >= 1, "Should have priority areas"

        print(f"\n  Priority Areas ({len(plan.priority_areas)}):")
        for area in plan.priority_areas:
            print(f"    - {area}")

    async def test_planner_output_completeness(self, intake_agent, planner_agent):
        """Test that planner produces complete investigation plans."""
        # Load a test case
        report = load_customer_report("test_data/case_01_legitimate_freelancer.txt")

        # Run intake agent
        intake_result = await run_intake_agent(intake_agent, report)

        # Run planner agent
        plan = await run_planner_agent(planner_agent, intake_result)

        # Verify all required fields are present
        assert plan.initial_risk_assessment in ["low", "medium", "high"]
        assert len(plan.reasoning) > 50, "Reasoning should be substantial"

        # At least one of the query types should be populated
        has_queries = (
            len(plan.typology_queries) > 0
            or len(plan.pattern_queries) > 0
            or len(plan.entity_queries) > 0
        )
        assert has_queries, "Should have at least one type of query"

        # Should have priority areas
        assert len(plan.priority_areas) > 0, "Should have priority areas"

        print(f"\n✅ Plan Completeness Check:")
        print(f"  Risk Assessment: {plan.initial_risk_assessment}")
        print(f"  Reasoning Length: {len(plan.reasoning)} chars")
        print(f"  Typology Queries: {len(plan.typology_queries)}")
        print(f"  Pattern Queries: {len(plan.pattern_queries)}")
        print(f"  Entity Queries: {len(plan.entity_queries)}")
        print(f"  Entities to Check: {len(plan.entities_to_check)}")
        print(f"  Priority Areas: {len(plan.priority_areas)}")


