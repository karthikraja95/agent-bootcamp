"""AML Fraud Detection Multi-Agent System - Gradio UI.

This module provides a web interface for the fraud detection system with
real-time streaming updates.
"""

import asyncio
import contextlib
import signal
import sys
from pathlib import Path

import agents
import gradio as gr
from dotenv import load_dotenv
from gradio.components.chatbot import ChatMessage
from openai import AsyncOpenAI

from src.utils import (
    AsyncWeaviateKnowledgeBase,
    Configs,
    get_weaviate_async_client,
    oai_agent_stream_to_gradio_messages,
    set_up_logging,
    setup_langfuse_tracer,
)
from src.utils.langfuse.shared_client import langfuse_client
from src.utils.tools.gemini_grounding import GeminiGroundingWithGoogleSearch

from src.fraud_detection.agents import (
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
from src.fraud_detection.models import FraudAssessment, InvestigationPlan, ReasoningOutput


load_dotenv(verbose=True)
set_up_logging()

# Initialize global clients at module level
configs = Configs.from_env_var()
async_openai_client = AsyncOpenAI()

async_weaviate_client = get_weaviate_async_client(
    http_host=configs.weaviate_http_host,
    http_port=configs.weaviate_http_port,
    http_secure=configs.weaviate_http_secure,
    grpc_host=configs.weaviate_grpc_host,
    grpc_port=configs.weaviate_grpc_port,
    grpc_secure=configs.weaviate_grpc_secure,
    api_key=configs.weaviate_api_key,
)
async_knowledgebase = AsyncWeaviateKnowledgeBase(
    async_weaviate_client,
    collection_name="enwiki_20250520",
)
gemini_grounding = GeminiGroundingWithGoogleSearch()


def _handle_sigint(signum, frame):
    """Handle SIGINT gracefully."""
    print("\n🛑 Shutting down gracefully...")
    sys.exit(0)


async def _cleanup_clients():
    """Cleanup async clients on shutdown."""
    if async_openai_client:
        await async_openai_client.close()
    if async_knowledgebase and async_knowledgebase.async_client:
        await async_knowledgebase.async_client.close()


def format_final_report(assessment: FraudAssessment) -> str:
    """Format the final fraud assessment as markdown."""
    verdict_emoji = {
        "LIKELY_FRAUD": "🚨",
        "SUSPICIOUS": "⚠️",
        "LIKELY_LEGITIMATE": "✅",
    }
    
    emoji = verdict_emoji.get(assessment.verdict, "❓")
    
    md = f"""## {emoji} Final Assessment

**Verdict**: {assessment.verdict}  
**Confidence**: {assessment.confidence_score}%

### Risk Summary
{assessment.risk_summary}

"""

    # Display red flags (incriminating evidence)
    if assessment.red_flags:
        md += "### 🔴 Red Flags Identified\n"
        for flag in assessment.red_flags:
            severity_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}
            emoji = severity_emoji.get(flag.severity, "⚪")
            md += f"- {emoji} **{flag.severity.upper()}**: {flag.description}\n"
            if flag.evidence:
                md += f"  - Evidence: {flag.evidence}\n"
        md += "\n"

    if assessment.mitigating_factors:
        md += "### 🟢 Mitigating Factors\n"
        for factor in assessment.mitigating_factors:
            md += f"- {factor}\n"
        md += "\n"
    
    if assessment.recommended_actions:
        md += "### 📋 Recommended Actions\n"
        for i, action in enumerate(assessment.recommended_actions, 1):
            md += f"{i}. {action}\n"
    
    return md


async def analyze_fraud_report_streaming(
    raw_report: str,
    gr_messages: list[ChatMessage],
):
    """Streaming orchestrator that yields intermediate results to UI."""
    global async_openai_client, async_knowledgebase, gemini_grounding

    print("\n" + "="*80)
    print("🚀 Starting fraud detection analysis...")
    print("="*80)

    # Create all agents
    print("📦 Creating agents...")
    intake_agent = create_intake_agent(async_openai_client)
    planner_agent = create_planner_agent(async_openai_client)
    typology_matcher = create_typology_matcher_agent(
        async_openai_client, async_knowledgebase, gemini_grounding
    )
    pattern_analyzer = create_pattern_analyzer_agent(
        async_openai_client, async_knowledgebase, gemini_grounding
    )
    entity_research = create_entity_research_agent(async_openai_client, gemini_grounding)
    reasoning_agent = create_reasoning_agent(async_openai_client)
    report_agent = create_report_agent(async_openai_client)
    print("✅ All agents created\n")

    # 1. Intake - stream status
    print("📥 STEP 1: Running Intake Agent...")
    gr_messages.append(ChatMessage(role="assistant", content="📥 **Intake Agent**: Parsing document and extracting signals..."))
    yield gr_messages

    intake_stream = agents.Runner.run_streamed(intake_agent, input=raw_report)
    async for event in intake_stream.stream_events():
        new_msgs = oai_agent_stream_to_gradio_messages(event)
        if new_msgs:
            gr_messages.extend(new_msgs)
            yield gr_messages
    intake_result = intake_stream.final_output_as(IntakeOutput)
    print(f"✅ Intake complete: {len(intake_result.signals)} signals extracted\n")

    gr_messages.append(ChatMessage(
        role="assistant",
        content=f"✅ Extracted {len(intake_result.signals)} signals from report"
    ))
    yield gr_messages

    # 2. Planning - stream status
    print("📋 STEP 2: Running Planner Agent...")
    gr_messages.append(ChatMessage(role="assistant", content="📋 **Planner Agent**: Creating investigation plan..."))
    yield gr_messages

    plan = await run_planner_agent(planner_agent, intake_result)

    # Count total investigation steps across all query types
    total_steps = (
        len(plan.typology_queries) +
        len(plan.pattern_queries) +
        len(plan.entity_queries)
    )
    print(f"✅ Planning complete: {total_steps} investigation steps")
    print(f"   - Typology queries: {len(plan.typology_queries)}")
    print(f"   - Pattern queries: {len(plan.pattern_queries)}")
    print(f"   - Entity queries: {len(plan.entity_queries)}\n")

    gr_messages.append(ChatMessage(
        role="assistant",
        content=f"✅ Investigation plan created with {total_steps} investigation steps"
    ))
    yield gr_messages

    # 3. Parallel specialist execution
    print("🔍 STEP 3: Running Specialist Agents in parallel...")
    gr_messages.append(ChatMessage(
        role="assistant",
        content="🔍 **Specialist Agents**: Running parallel investigation...\n- Typology Matcher\n- Pattern Analyzer\n- Entity Research"
    ))
    yield gr_messages

    # Construct queries from investigation plan
    typology_query = "\n".join(plan.typology_queries) if plan.typology_queries else "Check for common AML typologies"
    pattern_query = "\n".join(plan.pattern_queries) if plan.pattern_queries else "Identify suspicious patterns"
    entity_query = "\n".join(plan.entity_queries) if plan.entity_queries else "Research mentioned entities"

    print("   🔎 Starting Typology Matcher...")
    print("   🔎 Starting Pattern Analyzer...")
    print("   🔎 Starting Entity Research...")

    # Run specialists in parallel
    typology_matches, red_flags, entity_checks = await asyncio.gather(
        run_typology_matcher_agent(typology_matcher, typology_query),
        run_pattern_analyzer_agent(pattern_analyzer, pattern_query),
        run_entity_research_agent(entity_research, entity_query),
    )

    print(f"✅ Specialists complete:")
    print(f"   - Typology matches: {len(typology_matches)}")
    print(f"   - Red flags: {len(red_flags)}")
    print(f"   - Entity checks: {len(entity_checks)}\n")

    gr_messages.append(ChatMessage(
        role="assistant",
        content=f"✅ Specialists complete:\n- {len(typology_matches)} typology matches\n- {len(red_flags)} red flags\n- {len(entity_checks)} entity checks"
    ))
    yield gr_messages

    # 4. Reasoning - stream the LLM's reasoning process
    print("🧠 STEP 4: Running Reasoning Agent...")
    gr_messages.append(ChatMessage(role="assistant", content="🧠 **Reasoning Agent**: Analyzing evidence..."))
    yield gr_messages

    reasoning_result = await run_reasoning_agent(
        reasoning_agent,
        customer_report=raw_report,
        intake_signals=str(intake_result),
        typology_matches=str(typology_matches),
        red_flags=str(red_flags),
        entity_checks=str(entity_checks),
    )

    print(f"✅ Reasoning complete: {reasoning_result.verdict} ({reasoning_result.confidence_score}% confidence)\n")

    gr_messages.append(ChatMessage(
        role="assistant",
        content=f"✅ Reasoning complete: {reasoning_result.verdict} ({reasoning_result.confidence_score}% confidence)"
    ))
    yield gr_messages

    # 5. Report generation
    print("📝 STEP 5: Running Report Agent...")
    gr_messages.append(ChatMessage(role="assistant", content="📝 **Report Agent**: Generating final assessment..."))
    yield gr_messages

    final_report = await run_report_agent(
        report_agent,
        customer_report=raw_report,
        intake_signals=str(intake_result),
        typology_matches=str(typology_matches),
        red_flags=str(red_flags),
        entity_checks=str(entity_checks),
        reasoning_output=reasoning_result,
    )

    print(f"✅ Report generation complete!")
    print(f"   Final verdict: {final_report.verdict}")
    print(f"   Confidence: {final_report.confidence_score}%")
    print("="*80)
    print("🎉 Analysis complete!\n")

    # Final output
    gr_messages.append(ChatMessage(
        role="assistant",
        content=format_final_report(final_report)
    ))
    yield gr_messages


async def _main(report_text: str, gr_messages: list[ChatMessage]):
    """Main entry point for Gradio with streaming."""
    if not report_text or not report_text.strip():
        gr_messages.append(ChatMessage(
            role="assistant",
            content="⚠️ Please provide a customer report to analyze."
        ))
        yield gr_messages
        return

    # Setup LangFuse tracing (skip if it fails due to event loop issues)
    try:
        setup_langfuse_tracer()
        use_tracing = True
    except (ValueError, RuntimeError) as e:
        # nest_asyncio doesn't work with uvloop in Gradio
        print(f"⚠️ LangFuse tracing disabled: {e}")
        use_tracing = False

    if use_tracing:
        with langfuse_client.start_as_current_span(name="FraudDetection-Trace") as span:
            span.update(input=report_text[:500])  # Log first 500 chars

            async for messages in analyze_fraud_report_streaming(report_text, gr_messages):
                yield messages

            span.update(output="Analysis complete")
    else:
        # Run without tracing
        async for messages in analyze_fraud_report_streaming(report_text, gr_messages):
            yield messages


def load_document(file):
    """Load document content from uploaded file."""
    if file is None:
        return ""

    file_path = Path(file.name)

    if file_path.suffix == '.txt':
        with open(file.name, 'r', encoding='utf-8') as f:
            return f.read()
    elif file_path.suffix == '.docx':
        # Use python-docx to extract text
        try:
            import docx
            doc = docx.Document(file.name)
            return '\n'.join([para.text for para in doc.paragraphs])
        except ImportError:
            return "⚠️ python-docx not installed. Please install it to read .docx files."

    return ""


# Gradio UI
with gr.Blocks(title="AML Fraud Detection Agent") as demo:
    gr.Markdown("# 🔍 AML Fraud Detection Multi-Agent System")
    gr.Markdown("Upload a customer transaction report or paste the text directly.")

    with gr.Row():
        file_upload = gr.File(label="Upload Report (.txt)", file_types=[".txt"])

    report_input = gr.Textbox(
        label="Or paste report text here",
        lines=10,
        placeholder="Paste customer report content...",
    )

    file_upload.change(fn=load_document, inputs=file_upload, outputs=report_input)

    chatbot = gr.Chatbot(type="messages", label="Analysis Progress", height=600)

    submit_btn = gr.Button("🔍 Analyze Report", variant="primary")

    submit_btn.click(
        fn=_main,
        inputs=[report_input, chatbot],
        outputs=chatbot,
    )

    # Load example from test data
    example_path = Path(__file__).parent.parent.parent / "test_data" / "case_01_legitimate_freelancer.txt"
    example_text = ""
    if example_path.exists():
        example_text = example_path.read_text(encoding="utf-8")[:500] + "..."

    gr.Examples(
        examples=[
            [example_text] if example_text else ["Paste a customer transaction report here..."],
        ],
        inputs=report_input,
    )


if __name__ == "__main__":
    # Clients are already initialized at module level
    signal.signal(signal.SIGINT, _handle_sigint)

    try:
        demo.launch(share=True)
    finally:
        asyncio.run(_cleanup_clients())


