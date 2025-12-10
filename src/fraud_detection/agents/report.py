"""Report Agent - Generates final fraud assessment reports.

This agent takes all investigation findings and reasoning output to produce
a comprehensive, professionally formatted fraud assessment report.
"""

import agents
from openai import AsyncOpenAI

from ..models import FraudAssessment
from ..prompts import REPORT_AGENT_INSTRUCTIONS


def create_report_agent(
    openai_client: AsyncOpenAI,
    model: str = "gemini-2.5-flash",
) -> agents.Agent:
    """Create a Report Agent that generates final fraud assessment reports.

    This agent consolidates all investigation findings into a professional
    AML compliance report with structured output.

    Args:
        openai_client: AsyncOpenAI client configured for Gemini API
        model: Model to use (default: gemini-2.5-flash for fast report generation)

    Returns:
        Configured Report Agent with structured output
    """
    return agents.Agent(
        name="ReportAgent",
        instructions=REPORT_AGENT_INSTRUCTIONS,
        output_type=FraudAssessment,
        model=agents.OpenAIChatCompletionsModel(model=model, openai_client=openai_client),
        # NO TOOLS - pure report generation
    )


async def run_report_agent(
    agent: agents.Agent,
    customer_report: str,
    intake_signals: str,
    typology_matches: str,
    red_flags: str,
    entity_checks: str,
    reasoning_output: str,
) -> FraudAssessment:
    """Run the Report Agent to generate final fraud assessment.

    Args:
        agent: Configured Report Agent
        customer_report: Original customer report text
        intake_signals: Extracted signals from Intake Agent
        typology_matches: Results from Typology Matcher
        red_flags: Results from Pattern Analyzer
        entity_checks: Results from Entity Research
        reasoning_output: Synthesized analysis from Reasoning Agent

    Returns:
        FraudAssessment with final verdict and comprehensive report
    """
    # Construct comprehensive input for report generation
    report_input = f"""
# CUSTOMER REPORT
{customer_report}

# INTAKE SIGNALS
{intake_signals}

# TYPOLOGY MATCHES
{typology_matches}

# RED FLAGS IDENTIFIED
{red_flags}

# ENTITY CHECK RESULTS
{entity_checks}

# REASONING ANALYSIS
{reasoning_output}

---

Generate the final fraud assessment report based on all the above evidence.
"""

    result = await agents.Runner.run(agent, input=report_input)
    return result.final_output

