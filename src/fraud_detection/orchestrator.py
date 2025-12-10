"""Fraud Detection Orchestrator - Coordinates all agents with streaming support.

This module orchestrates the complete fraud detection pipeline:
1. Intake Agent - Parse and extract signals
2. Planner Agent - Create investigation plan
3. Specialist Agents (parallel) - Typology matching, pattern analysis, entity research
4. Reasoning Agent - Synthesize evidence
5. Report Agent - Generate final assessment

Supports streaming for real-time UI updates.
"""

import asyncio
from typing import AsyncGenerator, Callable

import agents
from openai import AsyncOpenAI

from src.utils.tools.gemini_grounding import GeminiGroundingWithGoogleSearch
from src.utils.tools.kb_weaviate import AsyncWeaviateKnowledgeBase

from .agents import (
    IntakeOutput,
    create_entity_research_agent,
    create_intake_agent,
    create_pattern_analyzer_agent,
    create_planner_agent,
    create_reasoning_agent,
    create_report_agent,
    create_typology_matcher_agent,
    run_entity_research_agent,
    run_pattern_analyzer_agent,
    run_planner_agent,
    run_reasoning_agent,
    run_report_agent,
    run_typology_matcher_agent,
)
from .models import FraudAssessment


async def analyze_fraud_report(
    raw_report: str,
    openai_client: AsyncOpenAI,
    async_knowledgebase: AsyncWeaviateKnowledgeBase,
    gemini_grounding: GeminiGroundingWithGoogleSearch,
) -> FraudAssessment:
    """Run complete fraud detection pipeline without streaming.

    Args:
        raw_report: Raw customer report text
        openai_client: AsyncOpenAI client configured for Gemini API
        async_knowledgebase: Wikipedia knowledge base for specialist agents
        gemini_grounding: Google Search tool for specialist agents

    Returns:
        FraudAssessment with final verdict and recommendations
    """
    # Create all agents
    intake_agent = create_intake_agent(openai_client)
    planner_agent = create_planner_agent(openai_client)
    typology_matcher = create_typology_matcher_agent(
        openai_client, async_knowledgebase, gemini_grounding
    )
    pattern_analyzer = create_pattern_analyzer_agent(
        openai_client, async_knowledgebase, gemini_grounding
    )
    entity_research = create_entity_research_agent(openai_client, gemini_grounding)
    reasoning_agent = create_reasoning_agent(openai_client)
    report_agent = create_report_agent(openai_client)

    # 1. Intake - Parse document and extract signals
    # Note: run_intake_agent expects CustomerReport but we pass raw text
    # The agent will parse it internally
    result = await agents.Runner.run(intake_agent, input=raw_report)
    intake_result = result.final_output_as(IntakeOutput)

    # 2. Planning - Create investigation plan
    plan = await run_planner_agent(planner_agent, intake_result)

    # 3. Parallel specialist execution
    # Construct queries from investigation plan
    typology_query = "\n".join(plan.typology_queries) if plan.typology_queries else "Check for common AML typologies"
    pattern_query = "\n".join(plan.pattern_queries) if plan.pattern_queries else "Identify suspicious patterns"
    entity_query = "\n".join(plan.entities_to_check) if plan.entities_to_check else "Research mentioned entities"

    typology_task = run_typology_matcher_agent(typology_matcher, typology_query)
    pattern_task = run_pattern_analyzer_agent(pattern_analyzer, pattern_query)
    entity_task = run_entity_research_agent(entity_research, entity_query)

    # Run specialists in parallel
    typology_matches, red_flags, entity_checks = await asyncio.gather(
        typology_task, pattern_task, entity_task
    )

    # 4. Reasoning - Synthesize all evidence
    reasoning_result = await run_reasoning_agent(
        reasoning_agent,
        customer_report=raw_report,
        intake_signals=str(intake_result),
        typology_matches=str(typology_matches),
        red_flags=str(red_flags),
        entity_checks=str(entity_checks),
    )

    # 5. Report generation - Final assessment
    final_report = await run_report_agent(
        report_agent,
        customer_report=raw_report,
        intake_signals=str(intake_result),
        typology_matches=str(typology_matches),
        red_flags=str(red_flags),
        entity_checks=str(entity_checks),
        reasoning_output=str(reasoning_result),
    )

    return final_report


async def analyze_fraud_report_with_progress(
    raw_report: str,
    openai_client: AsyncOpenAI,
    async_knowledgebase: AsyncWeaviateKnowledgeBase,
    gemini_grounding: GeminiGroundingWithGoogleSearch,
    progress_callback: Callable[[str, str], None] | None = None,
) -> FraudAssessment:
    """Run complete fraud detection pipeline with progress updates.

    Args:
        raw_report: Raw customer report text
        openai_client: AsyncOpenAI client configured for Gemini API
        async_knowledgebase: Wikipedia knowledge base for specialist agents
        gemini_grounding: Google Search tool for specialist agents
        progress_callback: Optional callback function(stage: str, message: str)

    Returns:
        FraudAssessment with final verdict and recommendations
    """

    def update_progress(stage: str, message: str):
        if progress_callback:
            progress_callback(stage, message)

    # Create all agents
    intake_agent = create_intake_agent(openai_client)
    planner_agent = create_planner_agent(openai_client)
    typology_matcher = create_typology_matcher_agent(
        openai_client, async_knowledgebase, gemini_grounding
    )
    pattern_analyzer = create_pattern_analyzer_agent(
        openai_client, async_knowledgebase, gemini_grounding
    )
    entity_research = create_entity_research_agent(openai_client, gemini_grounding)
    reasoning_agent = create_reasoning_agent(openai_client)
    report_agent = create_report_agent(openai_client)

    # 1. Intake
    update_progress("intake", "📥 Parsing document and extracting signals...")
    result = await agents.Runner.run(intake_agent, input=raw_report)
    intake_result = result.final_output_as(IntakeOutput)
    update_progress("intake", f"✅ Extracted {len(intake_result.signals)} signals")

    # 2. Planning
    update_progress("planning", "📋 Creating investigation plan...")
    plan = await run_planner_agent(planner_agent, intake_result)
    update_progress("planning", f"✅ Plan created with {len(plan.priority_areas)} priority areas")

    # 3. Parallel specialist execution
    update_progress("specialists", "🔍 Running specialist agents in parallel...")

    # Construct queries from investigation plan
    typology_query = "\n".join(plan.typology_queries) if plan.typology_queries else "Check for common AML typologies"
    pattern_query = "\n".join(plan.pattern_queries) if plan.pattern_queries else "Identify suspicious patterns"
    entity_query = "\n".join(plan.entities_to_check) if plan.entities_to_check else "Research mentioned entities"

    typology_task = run_typology_matcher_agent(typology_matcher, typology_query)
    pattern_task = run_pattern_analyzer_agent(pattern_analyzer, pattern_query)
    entity_task = run_entity_research_agent(entity_research, entity_query)

    # Run specialists in parallel
    typology_matches, red_flags, entity_checks = await asyncio.gather(
        typology_task, pattern_task, entity_task
    )

    update_progress(
        "specialists",
        f"✅ Specialists complete: {len(typology_matches)} typologies, "
        f"{len(red_flags)} red flags, {len(entity_checks)} entity checks",
    )

    # 4. Reasoning - Synthesize all evidence
    update_progress("reasoning", "🧠 Analyzing evidence and weighing factors...")
    reasoning_result = await run_reasoning_agent(
        reasoning_agent,
        customer_report=raw_report,
        intake_signals=str(intake_result),
        typology_matches=str(typology_matches),
        red_flags=str(red_flags),
        entity_checks=str(entity_checks),
    )
    update_progress("reasoning", f"✅ Reasoning complete: {reasoning_result.verdict}")

    # 5. Report generation - Final assessment
    update_progress("report", "📝 Generating final fraud assessment report...")
    final_report = await run_report_agent(
        report_agent,
        customer_report=raw_report,
        intake_signals=str(intake_result),
        typology_matches=str(typology_matches),
        red_flags=str(red_flags),
        entity_checks=str(entity_checks),
        reasoning_output=str(reasoning_result),
    )
    update_progress(
        "report",
        f"✅ Report complete: {final_report.verdict} ({final_report.confidence_score}% confidence)",
    )

    return final_report

