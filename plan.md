# Fraud Detection Multi-Agent System - Implementation Plan

## Executive Summary

Build an AML (Anti-Money Laundering) fraud detection multi-agent system by extending the existing multi-agent framework in `/src/2_frameworks/2_multi_agent/`. The system will analyze customer transaction reports (`.docx`/`.txt` format) through specialized agents that leverage **Google Search grounding (via Gemini)** for all external knowledge lookups.

---

## Input Data Format

The system will process structured customer reports containing:

### Sample Input Structure (`.docx` or `.txt`)

```
I. Customer Profile
- Customer ID, Name, Account Type, Opening Date, Location
- Registered Business, Investment Profile, Document Date, Time Period

II. Customer History Overview
- Narrative summary of customer activity patterns
- Monthly behavioral analysis

III. Transaction History Detail
- Date, Type, Description, FIAT Amount, Crypto Asset, Crypto QTY
- All transactions with categorization

IV. Financial & Crypto Summary
- Total Business Deposits
- Total Non-Crypto Spend/Transfers
- Total FIAT used for Crypto Buys
- Net Crypto Holdings Change
```

### Example Customer Profile

| Field               | Value                                 |
| ------------------- | ------------------------------------- |
| Customer ID         | CUST-10044                            |
| Name                | Chen Lee                              |
| Account Type        | Business Digital & Personal Savings   |
| Location            | Vancouver, BC, Canada                 |
| Registered Business | Lee Digital Art & Design (Freelancer) |
| Time Period         | Sep 1, 2025 - Nov 30, 2025            |

---

## Existing Infrastructure to Leverage

### 1. Multi-Agent Framework (`src/2_frameworks/2_multi_agent/`)

- **`efficient.py`** - Planner-worker pattern with agent-as-tool composition
- **`efficient_multiple_kbs.py`** - **KEY REFERENCE**: Demonstrates dual knowledge sources (Wikipedia + Google Search)
- **`fan_out.py`** - Parallel agent execution with O(N) concurrent processing

### 2. Tools Already Available (`src/utils/tools/`)

- **`gemini_grounding.py`** - `GeminiGroundingWithGoogleSearch` for real-time web search
- **`kb_weaviate.py`** - `AsyncWeaviateKnowledgeBase` for Wikipedia vector search (`enwiki_20250520`)

### 3. Utilities (`src/utils/`)

- Async utilities: `gather_with_progress`, `rate_limited`
- Gradio integration: `oai_agent_stream_to_gradio_messages`
- Langfuse tracing: `setup_langfuse_tracer`, `langfuse_client`

---

## Dual Knowledge Source Strategy

The system will have **both** knowledge sources available, and agents can intelligently choose:

| Knowledge Source           | Best For                                                              | Examples                                                               |
| -------------------------- | --------------------------------------------------------------------- | ---------------------------------------------------------------------- |
| **Wikipedia (Weaviate)**   | Established AML concepts, typology definitions, regulatory frameworks | "What is structuring in money laundering?", "FATF red flag indicators" |
| **Google Search (Gemini)** | Current events, entity checks, recent sanctions, adverse media        | "Chen Lee Vancouver fraud", "OFAC sanctions list 2025"                 |

### Agent Decision Logic

```
IF query is about:
  - AML typology definitions → Wikipedia
  - Regulatory guidance/frameworks → Wikipedia
  - Historical patterns → Wikipedia
  - Specific entity/person lookup → Google Search
  - Recent news/adverse media → Google Search
  - Sanctions lists (current) → Google Search
  - PEP status checks → Google Search
```

This mirrors the existing `efficient_multiple_kbs.py` pattern where the agent has both tools and decides contextually.

---

## Implementation Phases

### Phase 1: Data Models & Core Types

**Location**: `src/fraud_detection/models.py`

Define Pydantic models for structured input and output:

```python
# === INPUT MODELS ===
class CustomerProfile(BaseModel):
    customer_id: str
    name: str
    account_type: str
    opening_date: str
    location: str
    registered_business: str | None
    investment_profile: str
    document_date: str
    time_period: str

class Transaction(BaseModel):
    date: str
    type: str  # Deposit, Payment, Transfer, Crypto Buy
    description: str
    fiat_amount: float  # CAD
    crypto_asset: str | None  # BTC, ETH, etc.
    crypto_qty: float | None

class FinancialSummary(BaseModel):
    total_deposits: float
    total_non_crypto_spend: float
    total_crypto_buys: float
    net_crypto_holdings: dict[str, float]  # e.g., {"BTC": 0.052}

class CustomerReport(BaseModel):
    profile: CustomerProfile
    history_overview: str  # Narrative summary
    transactions: list[Transaction]
    financial_summary: FinancialSummary

# === OUTPUT MODELS ===
class ExtractedSignal(BaseModel):
    signal_type: str  # e.g., "high_volume_international", "crypto_conversion"
    value: str
    risk_indicator: Literal["positive", "neutral", "negative"]
    explanation: str

class TypologyMatch(BaseModel):
    name: str  # e.g., "Structuring", "Money Mule", "Layering"
    matched: bool
    confidence: float  # 0.0 - 1.0
    explanation: str
    source: str  # Google search citation

class RedFlag(BaseModel):
    description: str
    severity: Literal["high", "medium", "low"]
    evidence: str  # Specific transaction or pattern
    source: str | None

class EntityCheckResult(BaseModel):
    entity_name: str
    entity_type: Literal["customer", "business", "counterparty"]
    adverse_media: bool
    sanctions_hit: bool
    pep_status: bool
    findings: str
    sources: list[str]

class FraudAssessment(BaseModel):
    verdict: Literal["LIKELY_FRAUD", "SUSPICIOUS", "LIKELY_LEGITIMATE"]
    confidence_score: float  # 0-100
    risk_summary: str  # Brief narrative
    typologies: list[TypologyMatch]
    red_flags: list[RedFlag]
    entity_checks: list[EntityCheckResult]
    mitigating_factors: list[str]  # e.g., "Activity consistent with business profile"
    recommended_actions: list[str]
    sources: list[str]
```

---

### Phase 2: Intake Agent

**Location**: `src/fraud_detection/agents/intake.py`

**Purpose**: Parse raw document (`.docx`/`.txt`) and extract structured data + key signals

**Implementation**:

- Use `agents.Agent` with structured output (`CustomerReport` + `list[ExtractedSignal]`)
- No external tools needed - pure LLM document parsing
- Model: `gemini-2.5-flash` (fast, cost-effective for parsing)

```python
class IntakeOutput(BaseModel):
    customer_report: CustomerReport
    signals: list[ExtractedSignal]
    risk_areas_to_investigate: list[str]  # Hints for planner

intake_agent = agents.Agent(
    name="IntakeAgent",
    instructions="""
    Parse the customer transaction report and extract:
    1. Structured customer profile data
    2. All transactions with amounts and types
    3. Financial summary metrics
    4. Key signals that may indicate suspicious activity OR legitimate business

    Identify both positive indicators (consistent with profile) and negative
    indicators (potential red flags). Be objective - not all activity is suspicious.
    """,
    output_type=IntakeOutput,
    model=agents.OpenAIChatCompletionsModel(model="gemini-2.5-flash", ...)
)
```

---

### Phase 3: Planner Agent

**Location**: `src/fraud_detection/agents/planner.py`

**Purpose**: Analyze extracted signals and determine investigation strategy

**Implementation**:

- Takes `IntakeOutput` as input
- Generates specific search queries for Google Search grounding
- Model: `gemini-2.5-pro` (better reasoning for planning)

```python
class InvestigationPlan(BaseModel):
    # Typology matching queries
    typology_queries: list[str]  # e.g., ["structuring money laundering definition", "crypto layering AML"]

    # Pattern/red flag queries
    pattern_queries: list[str]  # e.g., ["AML red flags international wire transfers", "crypto business reporting requirements Canada"]

    # Entity research queries
    entities_to_check: list[str]  # Customer name, business name, counterparties
    entity_queries: list[str]  # e.g., ["Chen Lee Vancouver sanctions", "Lee Digital Art adverse media"]

    # Investigation notes
    priority_areas: list[str]
    initial_risk_assessment: Literal["low", "medium", "high"]
    reasoning: str

planner_agent = agents.Agent(
    name="PlannerAgent",
    instructions="""
    Based on the intake signals, create an investigation plan:
    1. Identify which AML typologies to check against (structuring, layering, money mule, etc.)
    2. Determine red flag patterns to search for
    3. List entities requiring adverse media/sanctions checks

    Consider BOTH suspicious indicators AND legitimate explanations.
    A freelancer with international clients may have legitimate high-volume transfers.
    """,
    output_type=InvestigationPlan,
    model=agents.OpenAIChatCompletionsModel(model="gemini-2.5-pro", ...)
)
```

---

### Phase 4: Specialist Agents (Parallel Execution)

**Location**: `src/fraud_detection/agents/specialists/`

**All specialists have BOTH tools available - agent decides which to use:**

- `search_wikipedia` - For established AML concepts, typology definitions
- `search_web` - For current events, entity checks, recent news

#### 4a. Typology Matcher (`typology_matcher.py`)

**Tools**: Wikipedia (primary for definitions) + Google Search (for current guidance)
**Purpose**: Match customer activity against known AML typologies

```python
typology_agent = agents.Agent(
    name="TypologyMatcher",
    instructions="""
    You have TWO knowledge sources - use them appropriately:

    USE WIKIPEDIA (search_wikipedia) for:
    - AML typology definitions and explanations
    - Historical money laundering patterns
    - Academic/established frameworks

    USE GOOGLE SEARCH (search_web) for:
    - Recent regulatory updates
    - Current enforcement trends
    - Jurisdiction-specific guidance

    Typologies to check:
    - Structuring (smurfing): Breaking transactions to avoid reporting thresholds
    - Layering: Complex transfers to obscure money trail
    - Money Mule: Acting as intermediary for illicit funds
    - Trade-based laundering: Using trade transactions to move value
    - Crypto layering: Using cryptocurrency to obscure source

    For each typology, assess:
    - Does the activity pattern match?
    - What evidence supports or contradicts the match?
    - Cite your sources.
    """,
    tools=[
        agents.function_tool(async_knowledgebase.search_knowledgebase),  # Wikipedia
        agents.function_tool(gemini_grounding.get_web_search_grounded_response),  # Google
    ],
    output_type=list[TypologyMatch],
    model=agents.OpenAIChatCompletionsModel(model="gemini-2.5-flash", ...)
)
```

#### 4b. Pattern Analyzer (`pattern_analyzer.py`)

**Tools**: Wikipedia (for regulatory frameworks) + Google Search (for current guidance)
**Purpose**: Identify red flags and compare against regulatory guidance

```python
pattern_agent = agents.Agent(
    name="PatternAnalyzer",
    instructions="""
    You have TWO knowledge sources - use them appropriately:

    USE WIKIPEDIA (search_wikipedia) for:
    - FATF recommendations and framework
    - Standard AML red flag indicators
    - Regulatory body descriptions

    USE GOOGLE SEARCH (search_web) for:
    - Current FINTRAC guidance (Canada-specific)
    - Recent FinCEN advisories
    - Updated reporting thresholds
    - Crypto-specific AML guidance (evolving rapidly)

    Assess these patterns:
    - Transaction patterns (amounts, frequency, timing)
    - Geographic risk (high-risk jurisdictions)
    - Customer profile consistency (income vs activity)
    - Crypto-specific red flags

    Distinguish between true red flags and normal business activity.
    """,
    tools=[
        agents.function_tool(async_knowledgebase.search_knowledgebase),  # Wikipedia
        agents.function_tool(gemini_grounding.get_web_search_grounded_response),  # Google
    ],
    output_type=list[RedFlag],
    model=agents.OpenAIChatCompletionsModel(model="gemini-2.5-flash", ...)
)
```

#### 4c. Entity Research (`entity_research.py`)

**Tools**: Google Search ONLY (entity checks require current information)
**Purpose**: Check entities for adverse media, sanctions, PEP status

```python
entity_agent = agents.Agent(
    name="EntityResearch",
    instructions="""
    USE GOOGLE SEARCH (search_web) for ALL entity checks.
    Wikipedia is NOT suitable for entity due diligence.

    Conduct due diligence searches on the provided entities:
    - Customer name + location
    - Registered business name
    - Any mentioned counterparties or exchanges

    Check for:
    - Adverse media (news articles, legal issues)
    - Sanctions lists (OFAC, EU, UN, Canada)
    - PEP (Politically Exposed Person) status
    - Regulatory actions or warnings

    Report findings with sources. "No adverse findings" is a valid result.
    """,
    tools=[agents.function_tool(gemini_grounding.get_web_search_grounded_response)],
    output_type=list[EntityCheckResult],
    model=agents.OpenAIChatCompletionsModel(model="gemini-2.5-flash", ...)
)
```

---

### Phase 5: Reasoning Agent (Pure LLM)

**Location**: `src/fraud_detection/agents/reasoning.py`

**Purpose**: Synthesize all specialist outputs using pure LLM reasoning (no tools)

**Implementation**:

- Takes combined outputs from all specialists
- Uses LLM reasoning to weigh evidence (no rule-based scoring)
- Considers both incriminating and exculpatory evidence
- Model: `gemini-2.5-pro` (best reasoning capabilities)

```python
class ReasoningOutput(BaseModel):
    evidence_analysis: str  # Detailed reasoning narrative
    incriminating_factors: list[str]
    exculpatory_factors: list[str]
    confidence_score: float  # 0-100, LLM-determined
    verdict: Literal["LIKELY_FRAUD", "SUSPICIOUS", "LIKELY_LEGITIMATE"]
    verdict_reasoning: str

reasoning_agent = agents.Agent(
    name="ReasoningAgent",
    instructions="""
    You are an AML analyst synthesizing investigation findings. Apply pure reasoning
    to weigh all evidence:

    INPUTS:
    - Customer profile and transaction history
    - Typology matching results (which patterns were/weren't matched)
    - Red flag analysis (what was flagged and what wasn't)
    - Entity research (adverse media, sanctions, PEP findings)

    YOUR TASK:
    1. Consider ALL evidence - both suspicious indicators AND legitimate explanations
    2. Weigh the strength of each piece of evidence
    3. Apply professional AML judgment to reach a conclusion
    4. Calculate a confidence score (0-100) based on evidence strength

    IMPORTANT:
    - A freelancer with international clients may legitimately receive many international transfers
    - Crypto purchases aligned with a stated investment profile are not inherently suspicious
    - Absence of adverse media/sanctions is a positive indicator
    - Consider if activity is CONSISTENT with the stated business profile

    Your reasoning must be thorough, balanced, and cite specific evidence.
    """,
    output_type=ReasoningOutput,
    model=agents.OpenAIChatCompletionsModel(model="gemini-2.5-pro", ...),
    # NO TOOLS - pure LLM reasoning
)
```

---

### Phase 6: Report Agent

**Location**: `src/fraud_detection/agents/report.py`

**Purpose**: Generate final formatted assessment with all citations consolidated

**Output**: `FraudAssessment` model with formatted markdown report

```python
report_agent = agents.Agent(
    name="ReportAgent",
    instructions="""
    Generate a comprehensive AML assessment report that includes:
    1. Executive summary with verdict and confidence
    2. Customer profile summary
    3. Typology analysis results
    4. Red flags identified (or lack thereof)
    5. Entity check results
    6. Mitigating factors (if any)
    7. Recommended actions
    8. All sources cited

    Format for compliance review - professional, thorough, actionable.
    """,
    output_type=FraudAssessment,
    model=agents.OpenAIChatCompletionsModel(model="gemini-2.5-flash", ...)
)
```

---

### Phase 7: Orchestrator (with Streaming Support)

**Location**: `src/fraud_detection/orchestrator.py`

**Pattern**: Based on `efficient_multiple_kbs.py` + `fan_out.py` with streaming

```python
from typing import AsyncGenerator
from gradio.components.chatbot import ChatMessage

async def analyze_fraud_report_streaming(
    raw_report: str,
    gr_messages: list[ChatMessage]
) -> AsyncGenerator[list[ChatMessage], None]:
    """
    Streaming orchestrator that yields intermediate results to UI.
    """

    # 1. Intake - stream status
    gr_messages.append(ChatMessage(role="assistant", content="📥 **Intake Agent**: Parsing document..."))
    yield gr_messages

    intake_stream = agents.Runner.run_streamed(intake_agent, input=raw_report)
    async for event in intake_stream.stream_events():
        gr_messages += oai_agent_stream_to_gradio_messages(event)
        yield gr_messages
    intake_result = intake_stream.final_output_as(IntakeOutput)

    # 2. Planning - stream status
    gr_messages.append(ChatMessage(role="assistant", content="📋 **Planner Agent**: Creating investigation plan..."))
    yield gr_messages

    plan_stream = agents.Runner.run_streamed(planner_agent, input=intake_result)
    async for event in plan_stream.stream_events():
        gr_messages += oai_agent_stream_to_gradio_messages(event)
        yield gr_messages
    plan = plan_stream.final_output_as(InvestigationPlan)

    # 3. Parallel specialist execution with progress updates
    gr_messages.append(ChatMessage(
        role="assistant",
        content="🔍 **Specialist Agents**: Running parallel investigation...\n"
                "- Typology Matcher\n- Pattern Analyzer\n- Entity Research"
    ))
    yield gr_messages

    # Run specialists in parallel, stream each result as it completes
    specialist_results = await run_specialists_with_streaming(
        plan, gr_messages, yield_callback=lambda msgs: msgs
    )
    yield gr_messages

    # 4. Reasoning - stream the LLM's reasoning process
    gr_messages.append(ChatMessage(role="assistant", content="🧠 **Reasoning Agent**: Analyzing evidence..."))
    yield gr_messages

    reasoning_stream = agents.Runner.run_streamed(reasoning_agent, input=specialist_results)
    async for event in reasoning_stream.stream_events():
        gr_messages += oai_agent_stream_to_gradio_messages(event)
        yield gr_messages
    reasoning_result = reasoning_stream.final_output_as(ReasoningOutput)

    # 5. Report generation
    gr_messages.append(ChatMessage(role="assistant", content="📝 **Report Agent**: Generating final assessment..."))
    yield gr_messages

    report_stream = agents.Runner.run_streamed(report_agent, input=reasoning_result)
    async for event in report_stream.stream_events():
        gr_messages += oai_agent_stream_to_gradio_messages(event)
        yield gr_messages

    # Final output
    final_report = report_stream.final_output_as(FraudAssessment)
    gr_messages.append(ChatMessage(
        role="assistant",
        content=format_final_report(final_report)  # Markdown formatted
    ))
    yield gr_messages
```

---

### Phase 8: Gradio UI (with Real-time Streaming)

**Location**: `src/fraud_detection/app.py`

**Pattern**: Based on `efficient_multiple_kbs.py` with enhanced streaming display

```python
import gradio as gr
from gradio.components.chatbot import ChatMessage

async def _main(report_text: str, gr_messages: list[ChatMessage]):
    """Main entry point for Gradio with streaming."""
    setup_langfuse_tracer()

    with langfuse_client.start_as_current_span(name="FraudDetection-Trace") as span:
        span.update(input=report_text[:500])  # Log first 500 chars

        async for messages in analyze_fraud_report_streaming(report_text, gr_messages):
            yield messages

        span.update(output="Analysis complete")

# File upload support for .docx/.txt
def load_document(file):
    """Load document content from uploaded file."""
    if file is None:
        return ""
    if file.name.endswith('.txt'):
        return file.read().decode('utf-8')
    elif file.name.endswith('.docx'):
        # Use python-docx to extract text
        import docx
        doc = docx.Document(file)
        return '\n'.join([para.text for para in doc.paragraphs])
    return ""

with gr.Blocks(title="AML Fraud Detection Agent") as demo:
    gr.Markdown("# 🔍 AML Fraud Detection Multi-Agent System")
    gr.Markdown("Upload a customer transaction report or paste the text directly.")

    with gr.Row():
        file_upload = gr.File(label="Upload Report (.docx or .txt)", file_types=[".docx", ".txt"])

    report_input = gr.Textbox(
        label="Or paste report text here",
        lines=10,
        placeholder="Paste customer report content..."
    )

    file_upload.change(fn=load_document, inputs=file_upload, outputs=report_input)

    chatbot = gr.Chatbot(type="messages", label="Analysis Progress", height=600)

    submit_btn = gr.Button("🔍 Analyze Report", variant="primary")

    submit_btn.click(
        fn=_main,
        inputs=[report_input, chatbot],
        outputs=chatbot
    )

    gr.Examples(
        examples=[
            ["Customer opened account 3 months ago. Received 47 wire transfers from 12 different countries..."],
            # Add sample Chen Lee report as example
        ],
        inputs=report_input
    )
```

---

## File Structure

```
src/fraud_detection/
├── __init__.py
├── models.py              # Pydantic data models (input + output)
├── document_loader.py     # .docx/.txt file loading utilities
├── agents/
│   ├── __init__.py
│   ├── intake.py          # IntakeAgent - document parsing
│   ├── planner.py         # PlannerAgent - investigation routing
│   ├── reasoning.py       # ReasoningAgent - pure LLM evidence synthesis
│   ├── report.py          # ReportAgent - final report generation
│   └── specialists/
│       ├── __init__.py
│       ├── typology_matcher.py  # Wikipedia + Google Search
│       ├── pattern_analyzer.py  # Wikipedia + Google Search
│       └── entity_research.py   # Google Search only (current info)
├── orchestrator.py        # Main workflow coordination with streaming
├── prompts.py             # Centralized agent instructions
└── app.py                 # Gradio UI with file upload + streaming
```

---

## Implementation Order (Incremental)

| Step | Task                                        | Depends On                    | Est. Effort |
| ---- | ------------------------------------------- | ----------------------------- | ----------- |
| 1    | Create `models.py` with all Pydantic models | -                             | Small       |
| 2    | Create `document_loader.py` for .docx/.txt  | -                             | Small       |
| 3    | Create `prompts.py` with agent instructions | -                             | Small       |
| 4    | Implement `IntakeAgent`                     | Step 1, 3                     | Small       |
| 5    | Implement `PlannerAgent`                    | Step 1, 3, 4                  | Small       |
| 6    | Implement `TypologyMatcher` specialist      | Step 1, 3, Wikipedia + Gemini | Medium      |
| 7    | Implement `PatternAnalyzer` specialist      | Step 1, 3, Wikipedia + Gemini | Medium      |
| 8    | Implement `EntityResearch` specialist       | Step 1, 3, Gemini tool        | Medium      |
| 9    | Implement `ReasoningAgent` (pure LLM)       | Step 1, 3, 6-8                | Medium      |
| 10   | Implement `ReportAgent`                     | Step 1, 3, 9                  | Small       |
| 11   | Build `orchestrator.py` with streaming      | Steps 4-10                    | Medium      |
| 12   | Create Gradio `app.py` with file upload     | Step 2, 11                    | Medium      |
| 13   | Testing with sample Chen Lee report         | All                           | Medium      |

---

## Key Reusable Components

| Component                             | From Existing Code          | Usage                                            |
| ------------------------------------- | --------------------------- | ------------------------------------------------ |
| `AsyncWeaviateKnowledgeBase`          | `kb_weaviate.py`            | Wikipedia search for AML concepts/typologies     |
| `GeminiGroundingWithGoogleSearch`     | `gemini_grounding.py`       | Web search for entities, current info            |
| `gather_with_progress`                | `async_utils.py`            | Parallel specialist execution                    |
| `rate_limited`                        | `async_utils.py`            | Concurrency control for API calls                |
| `oai_agent_stream_to_gradio_messages` | `gradio/messages.py`        | Real-time UI streaming                           |
| `setup_langfuse_tracer`               | `langfuse/`                 | Observability & tracing                          |
| Agent-as-tool pattern                 | `efficient.py`              | Worker agent composition                         |
| Dual KB pattern                       | `efficient_multiple_kbs.py` | Agent choosing between Wikipedia & Google Search |

---

## Design Decisions (Resolved)

| Decision               | Choice                                     | Rationale                                                      |
| ---------------------- | ------------------------------------------ | -------------------------------------------------------------- |
| **Knowledge Source**   | Dual: Wikipedia (Weaviate) + Google Search | Agent chooses: Wikipedia for concepts, Google for current info |
| **Confidence Scoring** | Pure LLM reasoning                         | More nuanced, considers context, no rigid rules                |
| **UI Streaming**       | Real-time intermediate outputs             | User sees agent progress, better UX                            |
| **Input Format**       | Structured .docx/.txt reports              | Matches real-world AML workflow                                |
| **Tool Selection**     | Agent decides which KB to use per query    | Mirrors `efficient_multiple_kbs.py` pattern                    |

---

## Dependencies

### Already in pyproject.toml:

- `openai-agents>=0.1.0` - Agent framework
- `weaviate-client>=4.15.4` - Vector DB for Wikipedia
- `gradio>=5.37.0` - UI with file upload
- `langfuse>=3.1.3` - Tracing
- `pydantic>=2.11.7` - Data models

### May need to add:

- `python-docx` - For .docx file parsing (check if needed)

---

## Success Criteria

1. ✅ Parse structured customer reports (.docx/.txt) into `CustomerReport` model
2. ✅ Identify relevant AML typologies via **Wikipedia OR Google Search** (agent decides)
3. ✅ Detect red flags using regulatory guidance from **Wikipedia OR Google Search**
4. ✅ Perform entity due diligence via **Google Search** (adverse media, sanctions, PEP)
5. ✅ Apply pure LLM reasoning to weigh evidence and calculate confidence
6. ✅ Generate comprehensive `FraudAssessment` with recommended actions
7. ✅ Stream intermediate agent outputs in Gradio UI
8. ✅ Correctly identify Chen Lee case as LIKELY_LEGITIMATE (activity consistent with freelancer profile)

---

## Sample Expected Output (Chen Lee Case)

```
┌─────────────────────────────────────────────────────────────────┐
│ ASSESSMENT: LIKELY LEGITIMATE                                   │
│ Confidence: 78%                                                 │
├─────────────────────────────────────────────────────────────────┤
│ Risk Summary:                                                   │
│ Customer activity is consistent with stated business profile    │
│ as an international digital freelancer. No adverse findings.    │
├─────────────────────────────────────────────────────────────────┤
│ Typology Analysis:                                              │
│ • Structuring: NOT MATCHED - Transactions vary in size          │
│ • Money Mule: NOT MATCHED - Activity consistent with profile    │
│ • Layering: NOT MATCHED - Clear business purpose for transfers  │
├─────────────────────────────────────────────────────────────────┤
│ Red Flags Detected: NONE                                        │
│ ✓ International transfers explained by client base              │
│ ✓ Crypto purchases align with stated investment profile         │
│ ✓ Transaction amounts consistent with freelance income          │
├─────────────────────────────────────────────────────────────────┤
│ Mitigating Factors:                                             │
│ • Registered business matches activity type                     │
│ • Consistent monthly patterns over 3-month period               │
│ • Scheduled crypto purchases (DCA strategy)                     │
├─────────────────────────────────────────────────────────────────┤
│ Entity Check:                                                   │
│ • Chen Lee: No adverse media found                              │
│ • Lee Digital Art & Design: No regulatory issues                │
├─────────────────────────────────────────────────────────────────┤
│ Recommended Actions:                                            │
│ • Continue standard monitoring                                  │
│ • No enhanced due diligence required at this time               │
│ • Document rationale for file                                   │
└─────────────────────────────────────────────────────────────────┘
```
