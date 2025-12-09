# Fraud Detection Multi-Agent System - Implementation Plan

## Executive Summary

Build an AML (Anti-Money Laundering) fraud detection multi-agent system by extending the existing multi-agent framework in `/src/2_frameworks/2_multi_agent/`. The system will analyze suspicious activity reports through specialized agents that leverage Wikipedia vector search (via Weaviate) and Google web search (via Gemini Grounding).

---

## Existing Infrastructure to Leverage

### 1. Multi-Agent Framework (`src/2_frameworks/2_multi_agent/`)

- **`efficient.py`** - Planner-worker pattern with agent-as-tool composition
- **`efficient_multiple_kbs.py`** - Multiple knowledge sources (Wikipedia + Google Search)
- **`fan_out.py`** - Parallel agent execution with O(N) concurrent processing

### 2. Tools Already Available (`src/utils/tools/`)

- **`kb_weaviate.py`** - `AsyncWeaviateKnowledgeBase` for Wikipedia vector search
- **`gemini_grounding.py`** - `GeminiGroundingWithGoogleSearch` for web search

### 3. Utilities (`src/utils/`)

- Async utilities: `gather_with_progress`, `rate_limited`
- Gradio integration: `oai_agent_stream_to_gradio_messages`
- Langfuse tracing: `setup_langfuse_tracer`, `langfuse_client`

---

## Implementation Phases

### Phase 1: Data Models & Core Types

**Location**: `src/fraud_detection/models.py`

Define Pydantic models for:

```python
class ExtractedSignal(BaseModel):
    signal_type: str  # e.g., "transaction_count", "geographic_scope"
    value: str
    raw_text: str

class IntakeReport(BaseModel):
    raw_text: str
    signals: list[ExtractedSignal]

class TypologyMatch(BaseModel):
    name: str  # e.g., "Structuring", "Money Mule"
    confidence: float
    explanation: str
    wikipedia_source: str

class RedFlag(BaseModel):
    description: str
    severity: Literal["high", "medium", "low"]

class EntityCheckResult(BaseModel):
    entity_name: str
    adverse_media: bool
    sanctions_hit: bool
    pep_status: bool
    sources: list[str]

class FraudAssessment(BaseModel):
    verdict: Literal["LIKELY_FRAUD", "SUSPICIOUS", "LIKELY_LEGITIMATE"]
    confidence_score: float  # 0-100
    typologies: list[TypologyMatch]
    red_flags: list[RedFlag]
    entity_checks: list[EntityCheckResult]
    recommended_actions: list[str]
    sources: list[str]
```

---

### Phase 2: Intake Agent

**Location**: `src/fraud_detection/agents/intake.py`

**Purpose**: Parse raw report text and extract key signals

**Implementation**:

- Use `agents.Agent` with structured output (`IntakeReport`)
- No tools needed - pure LLM text extraction
- Model: `gemini-2.5-flash` (fast, cost-effective)

```python
intake_agent = agents.Agent(
    name="IntakeAgent",
    instructions="""Extract structured signals from the fraud report...""",
    output_type=IntakeReport,
    model=agents.OpenAIChatCompletionsModel(model="gemini-2.5-flash", ...)
)
```

---

### Phase 3: Planner Agent

**Location**: `src/fraud_detection/agents/planner.py`

**Purpose**: Analyze signals and route to appropriate specialist agents

**Implementation**:

- Takes `IntakeReport` as input
- Returns routing decisions (which specialists to invoke)
- Model: `gemini-2.5-pro` (better reasoning for planning)

```python
class RoutingPlan(BaseModel):
    run_typology_matcher: bool
    typology_queries: list[str]  # Queries for Wikipedia search
    run_pattern_analyzer: bool
    pattern_queries: list[str]
    run_entity_research: bool
    entities_to_check: list[str]
```

---

### Phase 4: Specialist Agents (Parallel Execution)

**Location**: `src/fraud_detection/agents/specialists/`

#### 4a. Typology Matcher (`typology_matcher.py`)

**Source**: Wikipedia via `AsyncWeaviateKnowledgeBase`
**Purpose**: Match against known fraud typologies

```python
typology_agent = agents.Agent(
    name="TypologyMatcher",
    instructions="""Search for money laundering typologies in Wikipedia...""",
    tools=[agents.function_tool(async_knowledgebase.search_knowledgebase)],
    output_type=list[TypologyMatch],
    model=agents.OpenAIChatCompletionsModel(model="gemini-2.5-flash", ...)
)
```

#### 4b. Pattern Analyzer (`pattern_analyzer.py`)

**Source**: Wikipedia via `AsyncWeaviateKnowledgeBase`
**Purpose**: Identify red flags against known patterns

```python
pattern_agent = agents.Agent(
    name="PatternAnalyzer",
    instructions="""Search for AML red flags and suspicious patterns...""",
    tools=[agents.function_tool(async_knowledgebase.search_knowledgebase)],
    output_type=list[RedFlag],
    ...
)
```

#### 4c. Entity Research (`entity_research.py`)

**Source**: Google Search via `GeminiGroundingWithGoogleSearch`
**Purpose**: Check entities for adverse media, sanctions, PEP status

```python
entity_agent = agents.Agent(
    name="EntityResearch",
    instructions="""Search for adverse media, sanctions, PEP status...""",
    tools=[agents.function_tool(gemini_grounding.get_web_search_grounded_response)],
    output_type=list[EntityCheckResult],
    ...
)
```

---

### Phase 5: Reasoning Agent

**Location**: `src/fraud_detection/agents/reasoning.py`

**Purpose**: Synthesize all specialist outputs and calculate confidence

**Implementation**:

- Takes combined outputs from all specialists
- Weighs evidence and produces final score
- Model: `gemini-2.5-pro` (complex reasoning)

---

### Phase 6: Report Agent

**Location**: `src/fraud_detection/agents/report.py`

**Purpose**: Generate final formatted assessment with citations

**Output**: `FraudAssessment` model formatted as markdown/text

---

### Phase 7: Orchestrator

**Location**: `src/fraud_detection/orchestrator.py`

**Pattern**: Based on `efficient_multiple_kbs.py` + `fan_out.py`

```python
async def analyze_fraud_report(raw_report: str) -> FraudAssessment:
    # 1. Intake
    intake_result = await agents.Runner.run(intake_agent, input=raw_report)

    # 2. Planning
    routing = await agents.Runner.run(planner_agent, input=intake_result)

    # 3. Parallel specialist execution (fan-out pattern)
    tasks = []
    if routing.run_typology_matcher:
        tasks.append(run_typology_matcher(routing.typology_queries))
    if routing.run_pattern_analyzer:
        tasks.append(run_pattern_analyzer(routing.pattern_queries))
    if routing.run_entity_research:
        tasks.append(run_entity_research(routing.entities_to_check))

    specialist_results = await gather_with_progress(tasks)

    # 4. Reasoning
    reasoning_result = await agents.Runner.run(reasoning_agent, input=specialist_results)

    # 5. Report generation
    final_report = await agents.Runner.run(report_agent, input=reasoning_result)

    return final_report
```

---

### Phase 8: Gradio UI

**Location**: `src/fraud_detection/app.py`

**Pattern**: Based on `efficient_multiple_kbs.py` Gradio setup

```python
demo = gr.ChatInterface(
    analyze_fraud_report_streaming,
    title="AML Fraud Detection Agent",
    type="messages",
    examples=[
        "Customer opened account 3 months ago. Received 47 wire transfers...",
    ],
)
```

---

## File Structure

```
src/fraud_detection/
├── __init__.py
├── models.py              # Pydantic data models
├── agents/
│   ├── __init__.py
│   ├── intake.py          # IntakeAgent
│   ├── planner.py         # PlannerAgent
│   ├── reasoning.py       # ReasoningAgent
│   ├── report.py          # ReportAgent
│   └── specialists/
│       ├── __init__.py
│       ├── typology_matcher.py
│       ├── pattern_analyzer.py
│       └── entity_research.py
├── orchestrator.py        # Main workflow coordination
├── prompts.py             # Agent instructions/prompts
└── app.py                 # Gradio UI
```

---

## Implementation Order (Incremental)

| Step | Task                                        | Depends On                      | Est. Effort |
| ---- | ------------------------------------------- | ------------------------------- | ----------- |
| 1    | Create `models.py` with all Pydantic models | -                               | Small       |
| 2    | Create `prompts.py` with agent instructions | -                               | Small       |
| 3    | Implement `IntakeAgent`                     | Step 1, 2                       | Small       |
| 4    | Implement `PlannerAgent`                    | Step 1, 2, 3                    | Small       |
| 5    | Implement `TypologyMatcher` specialist      | Step 1, 2, existing KB tool     | Medium      |
| 6    | Implement `PatternAnalyzer` specialist      | Step 1, 2, existing KB tool     | Medium      |
| 7    | Implement `EntityResearch` specialist       | Step 1, 2, existing Gemini tool | Medium      |
| 8    | Implement `ReasoningAgent`                  | Step 1, 2, 5-7                  | Medium      |
| 9    | Implement `ReportAgent`                     | Step 1, 2, 8                    | Small       |
| 10   | Build `orchestrator.py`                     | Steps 3-9                       | Medium      |
| 11   | Create Gradio `app.py`                      | Step 10                         | Small       |
| 12   | Testing & refinement                        | All                             | Medium      |

---

## Key Reusable Components

| Component                             | From Existing Code    | Usage                         |
| ------------------------------------- | --------------------- | ----------------------------- |
| `AsyncWeaviateKnowledgeBase`          | `kb_weaviate.py`      | Typology & Pattern search     |
| `GeminiGroundingWithGoogleSearch`     | `gemini_grounding.py` | Entity research               |
| `gather_with_progress`                | `async_utils.py`      | Parallel specialist execution |
| `rate_limited`                        | `async_utils.py`      | Concurrency control           |
| `oai_agent_stream_to_gradio_messages` | `gradio/messages.py`  | UI streaming                  |
| `setup_langfuse_tracer`               | `langfuse/`           | Observability                 |
| Agent-as-tool pattern                 | `efficient.py`        | Worker agent composition      |

---

## Questions to Clarify

1. **Data Source for Typologies**: Should we create a custom Weaviate collection with AML-specific typologies, or rely on the existing Wikipedia collection (`enwiki_20250520`)?

2. **Entity Research Scope**: For entity checks, should we:

   - Search for specific sanctions lists (OFAC, EU, UN)?
   - Check specific adverse media databases?
   - Or rely on general Google search grounding?

3. **Confidence Score Calculation**: Should the reasoning agent use:

   - A rule-based scoring system (e.g., weighted red flags)?
   - LLM-based reasoning to output confidence?
   - A hybrid approach?

4. **UI Preferences**:

   - Should intermediate agent outputs be shown in real-time (streaming)?
   - Should there be a "detailed" vs "summary" view toggle?

5. **Persistence & History**:
   - Should we store analysis results (e.g., Langfuse traces)?
   - Is there a need for batch processing multiple reports?

---

## Dependencies (Already in pyproject.toml)

All required dependencies are present:

- `openai-agents>=0.1.0` - Agent framework
- `weaviate-client>=4.15.4` - Vector DB
- `gradio>=5.37.0` - UI
- `langfuse>=3.1.3` - Tracing
- `pydantic>=2.11.7` - Data models

---

## Success Criteria

1. ✅ Given a sample fraud report, system produces structured `FraudAssessment`
2. ✅ Typologies matched against Wikipedia content with citations
3. ✅ Entity checks return adverse media/sanctions results from web
4. ✅ Confidence score reasonably reflects evidence strength
5. ✅ Final report includes actionable recommendations
6. ✅ All sources properly cited
7. ✅ Gradio UI allows interactive testing
