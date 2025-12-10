# AML Fraud Detection Multi-Agent System - Dataflow Documentation

## Overview

The AML (Anti-Money Laundering) Fraud Detection system is a multi-agent pipeline that analyzes customer transaction reports to detect potential fraud, money laundering, and suspicious activities. It uses **6 specialized AI agents** working in a coordinated pipeline with parallel execution for specialist agents.

## Architecture Diagram

```
                            ┌─────────────────────┐
                            │   Customer Report   │
                            │   (Raw Text/File)   │
                            └──────────┬──────────┘
                                       │
                                       ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                           STEP 1: INTAKE AGENT                               │
│  ┌─────────────────────────────────────────────────────────────────────┐     │
│  │ • Parses document and extracts structured signals                    │     │
│  │ • Identifies risk indicators (positive/neutral/negative)             │     │
│  │ • Suggests areas for further investigation                           │     │
│  │ Model: gemini-2.5-flash                                              │     │
│  └─────────────────────────────────────────────────────────────────────┘     │
└──────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼ IntakeOutput
                                       │
┌──────────────────────────────────────────────────────────────────────────────┐
│                          STEP 2: PLANNER AGENT                               │
│  ┌─────────────────────────────────────────────────────────────────────┐     │
│  │ • Creates investigation plan based on intake signals                 │     │
│  │ • Generates queries for specialist agents                            │     │
│  │ • Prioritizes investigation areas                                    │     │
│  │ Model: gemini-2.5-pro                                                │     │
│  └─────────────────────────────────────────────────────────────────────┘     │
└──────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼ InvestigationPlan
                                       │
       ┌───────────────────────────────┼───────────────────────────────┐
       │                               │                               │
       ▼                               ▼                               ▼
┌────────────────┐            ┌────────────────┐            ┌────────────────┐
│   TYPOLOGY     │            │    PATTERN     │            │    ENTITY      │
│    MATCHER     │            │   ANALYZER     │            │   RESEARCH     │
│                │            │                │            │                │
│ STEP 3a        │            │ STEP 3b        │            │ STEP 3c        │
│ (Parallel)     │            │ (Parallel)     │            │ (Parallel)     │
└───────┬────────┘            └───────┬────────┘            └───────┬────────┘
        │                             │                             │
        │TypologyMatch[]              │ RedFlag[]                   │ EntityCheckResult[]
        └───────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                         STEP 4: REASONING AGENT                              │
│  ┌─────────────────────────────────────────────────────────────────────┐     │
│  │ • Synthesizes all specialist findings                                │     │
│  │ • Weighs incriminating vs exculpatory factors                        │     │
│  │ • Generates preliminary verdict with confidence score                │     │
│  │ • Pure LLM reasoning (no tools)                                      │     │
│  │ Model: gemini-2.5-pro                                                │     │
│  └─────────────────────────────────────────────────────────────────────┘     │
└──────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼ ReasoningOutput
                                       │
┌──────────────────────────────────────────────────────────────────────────────┐
│                          STEP 5: REPORT AGENT                                │
│  ┌─────────────────────────────────────────────────────────────────────┐     │
│  │ • Generates final fraud assessment report                            │     │
│  │ • Consolidates all findings into professional format                 │     │
│  │ • Provides actionable recommendations                                │     │
│  │ Model: gemini-2.5-flash                                              │     │
│  └─────────────────────────────────────────────────────────────────────┘     │
└──────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
                            ┌─────────────────────┐
                            │   FraudAssessment   │
                            │   (Final Report)    │
                            └─────────────────────┘
```

## Step-by-Step Dataflow

### Step 1: Intake Agent

**Purpose**: Parse and analyze raw customer transaction reports to extract structured signals.

**Input**: Raw customer report text (from file upload or direct input)

**Processing**:
1. Reviews customer profile (ID, name, account type, location, business info)
2. Analyzes transaction history (dates, types, amounts, crypto activity)
3. Extracts financial summary metrics
4. Identifies signals in categories:
   - `transaction_pattern` - Frequency/amount patterns
   - `geographic_risk` - Location-based risks
   - `customer_behavior` - Behavioral indicators
   - `crypto_activity` - Cryptocurrency signals
   - `cash_usage` - Cash patterns
   - `counterparty` - Third-party entities

**Output**: `IntakeOutput`
```python
class IntakeOutput:
    customer_report: CustomerReport     # Structured report data
    signals: list[ExtractedSignal]      # Extracted risk signals
    risk_areas_to_investigate: list[str] # Suggested investigation areas
```

**Model**: `gemini-2.5-flash`

---

### Step 2: Planner Agent

**Purpose**: Create a strategic investigation plan based on intake signals.

**Input**: `IntakeOutput` from Step 1

**Processing**:
1. Analyzes extracted signals and risk areas
2. Generates targeted queries for each specialist agent:
   - Typology queries (structuring, layering, smurfing detection)
   - Pattern queries (transaction anomalies)
   - Entity queries (adverse media, sanctions, PEP checks)
3. Prioritizes investigation areas
4. Provides initial risk assessment (low/medium/high)

**Output**: `InvestigationPlan`
```python
class InvestigationPlan:
    typology_queries: list[str]         # Queries for Typology Matcher
    pattern_queries: list[str]          # Queries for Pattern Analyzer
    entities_to_check: list[str]        # Entities to research
    entity_queries: list[str]           # Specific entity queries
    priority_areas: list[str]           # Priority investigation areas
    initial_risk_assessment: Literal["low", "medium", "high"]
    reasoning: str                      # Reasoning for the plan
```

**Model**: `gemini-2.5-pro`

---

### Step 3: Specialist Agents (Parallel Execution)

Three specialist agents run **concurrently** using `asyncio.gather()`:

#### Step 3a: Typology Matcher Agent

**Purpose**: Match customer activity against known AML typologies.

**Input**: Typology queries from `InvestigationPlan`

**Tools Available**:
- `search_knowledgebase` - Wikipedia subset (May 2025) for AML definitions
- `get_web_search_grounded_response` - Google Search for current information

**Processing**:
1. Searches knowledge base for typology definitions
2. Compares customer activity against known patterns
3. Checks for: Structuring, Layering, Smurfing, Money Mule, Trade-based laundering

**Output**: `list[TypologyMatch]`
```python
class TypologyMatch:
    name: str                           # Typology name
    matched: bool                       # Whether activity matches
    confidence: float                   # 0.0-1.0 confidence score
    explanation: str                    # Why it matches/doesn't match
    source: str                         # Source citation
```

**Model**: `gemini-2.5-flash`

#### Step 3b: Pattern Analyzer Agent

**Purpose**: Identify suspicious transaction patterns and red flags.

**Input**: Pattern queries from `InvestigationPlan`

**Tools Available**:
- `search_knowledgebase` - Wikipedia subset for pattern analysis concepts
- `get_web_search_grounded_response` - Google Search for current fraud patterns

**Processing**:
1. Analyzes transaction frequency, timing, amounts
2. Identifies patterns: just-below-threshold, clustering, velocity spikes
3. Checks for red flags based on regulatory guidance

**Output**: `list[RedFlag]`
```python
class RedFlag:
    description: str                    # Red flag description
    severity: Literal["high", "medium", "low"]
    evidence: str                       # Specific evidence from transactions
    source: str | None                  # Source citation
```

**Model**: `gemini-2.5-flash`

#### Step 3c: Entity Research Agent

**Purpose**: Research entities for adverse media, sanctions, and PEP status.

**Input**: Entity queries from `InvestigationPlan`

**Tools Available**:
- `get_web_search_grounded_response` - Google Search for entity research

**Processing**:
1. Searches for adverse media (fraud allegations, criminal activity)
2. Checks sanctions lists (OFAC, UN, EU)
3. Verifies PEP (Politically Exposed Person) status
4. Validates business legitimacy

**Output**: `list[EntityCheckResult]`
```python
class EntityCheckResult:
    entity_name: str                    # Entity being checked
    entity_type: Literal["customer", "business", "counterparty"]
    adverse_media: bool                 # Adverse media found
    sanctions_hit: bool                 # On sanctions list
    pep_status: bool                    # Is a PEP
    findings: str                       # Summary of findings
    sources: list[str]                  # Source citations
```

**Model**: `gemini-2.5-flash`

---

### Step 4: Reasoning Agent

**Purpose**: Synthesize all evidence using pure LLM reasoning.

**Input**: All outputs from previous steps:
- Original customer report
- Intake signals
- Typology matches
- Red flags
- Entity check results

**Processing** (No tools - pure reasoning):
1. Analyzes all evidence holistically
2. Weighs incriminating factors vs exculpatory factors
3. Considers totality of circumstances
4. Reaches preliminary verdict with confidence score

**Output**: `ReasoningOutput`
```python
class ReasoningOutput:
    evidence_analysis: str              # Detailed reasoning narrative
    incriminating_factors: list[str]    # Factors suggesting fraud
    exculpatory_factors: list[str]      # Factors suggesting legitimacy
    confidence_score: float             # 0-100 confidence
    verdict: Literal["LIKELY_FRAUD", "SUSPICIOUS", "LIKELY_LEGITIMATE"]
    verdict_reasoning: str              # Explanation of verdict
```

**Model**: `gemini-2.5-pro`

---

### Step 5: Report Agent

**Purpose**: Generate final professional fraud assessment report.

**Input**: All investigation findings + Reasoning output

**Processing** (No tools - report generation):
1. Consolidates all findings into structured report
2. Applies verdict guidelines:
   - `LIKELY_FRAUD` (80-100 confidence): Strong evidence, multiple typologies
   - `SUSPICIOUS` (50-79 confidence): Some indicators, warrants investigation
   - `LIKELY_LEGITIMATE` (0-49 confidence): Legitimate activity
3. Generates actionable recommendations
4. Compiles all source citations

**Output**: `FraudAssessment`
```python
class FraudAssessment:
    verdict: Literal["LIKELY_FRAUD", "SUSPICIOUS", "LIKELY_LEGITIMATE"]
    confidence_score: float             # 0-100
    risk_summary: str                   # Executive summary
    typologies: list[TypologyMatch]     # Matched typologies
    red_flags: list[RedFlag]            # Identified red flags
    entity_checks: list[EntityCheckResult]
    mitigating_factors: list[str]       # Legitimate explanations
    recommended_actions: list[str]      # Next steps
    sources: list[str]                  # All citations
```

**Model**: `gemini-2.5-flash`

---

## Dependencies from `agent-bootcamp/src/utils/`

The fraud detection system leverages several shared utilities:

### 1. Weaviate Knowledge Base (`src/utils/tools/kb_weaviate.py`)

```python
from src.utils import AsyncWeaviateKnowledgeBase, get_weaviate_async_client
```

- **Purpose**: Provides semantic search over a Wikipedia knowledge base (May 2025 snapshot)
- **Used by**: Typology Matcher, Pattern Analyzer
- **Features**:
  - Hybrid search (keyword + vector)
  - BGE-M3 embeddings for vectorization
  - Rate limiting and backoff
- **Collection**: `enwiki_20250520`

### 2. Gemini Grounding with Google Search (`src/utils/tools/gemini_grounding.py`)

```python
from src.utils.tools.gemini_grounding import GeminiGroundingWithGoogleSearch
```

- **Purpose**: Real-time web search via Gemini API with grounding
- **Used by**: All specialist agents
- **Features**:
  - Google Search integration
  - Citation extraction and formatting
  - Automatic query expansion
  - Retries with exponential backoff

### 3. Configuration Management (`src/utils/env_vars.py`)

```python
from src.utils import Configs
```

- **Purpose**: Load configuration from environment variables
- **Provides**:
  - Weaviate connection settings
  - API keys
  - Service endpoints

### 4. Gradio Integration (`src/utils/gradio/messages.py`)

```python
from src.utils import oai_agent_stream_to_gradio_messages
```

- **Purpose**: Convert OpenAI Agent SDK events to Gradio chat messages
- **Features**:
  - Stream event handling
  - Tool call visualization
  - Response formatting

### 5. LangFuse Tracing (`src/utils/langfuse/`)

```python
from src.utils import setup_langfuse_tracer
from src.utils.langfuse.shared_client import langfuse_client
```

- **Purpose**: Observability and tracing for agent execution
- **Features**:
  - Span tracking
  - Input/output logging
  - Performance monitoring

### 6. Logging (`src/utils/logging.py`)

```python
from src.utils import set_up_logging
```

- **Purpose**: Configure structured logging for the application

---

## External Dependencies

### OpenAI Agents SDK

```python
import agents
from agents import Agent, Runner, function_tool
```

- Creates and runs AI agents
- Manages tool calling
- Handles streaming responses
- Structured output parsing

### Gradio

- Web UI framework
- File upload support
- Real-time streaming chat interface

### Pydantic

- Data validation and serialization
- Structured output models

---

## UI Flow (Gradio)

1. **User uploads report** (`.txt` or `.docx`) or pastes text
2. **Clicks "Analyze Report"**
3. **Streaming updates** show progress:
   - "Intake Agent: Parsing document..."
   - "Planner Agent: Creating investigation plan..."
   - "Specialist Agents: Running parallel investigation..."
   - "Reasoning Agent: Analyzing evidence..."
   - "Report Agent: Generating final assessment..."
4. **Final report displayed** with:
   - Verdict emoji (LIKELY_FRAUD, SUSPICIOUS, LIKELY_LEGITIMATE)
   - Confidence score
   - Risk summary
   - Red flags with severity
   - Mitigating factors
   - Recommended actions

---

## Example Data Flow

```
Input: "Customer John Doe made 8 cash deposits of $9,500 each over 2 months..."

Step 1 - Intake:
  → Signals: [
      {type: "cash_usage", value: "multiple deposits near threshold", risk: "negative"},
      {type: "transaction_pattern", value: "consistent amounts", risk: "negative"}
    ]

Step 2 - Planner:
  → Plan: {
      typology_queries: ["structuring money laundering pattern"],
      pattern_queries: ["cash deposits below reporting threshold"],
      entity_queries: ["John Doe adverse media sanctions"]
    }

Step 3 - Specialists (parallel):
  → Typology: [{name: "Structuring", matched: true, confidence: 0.85}]
  → Patterns: [{description: "Just-below-threshold deposits", severity: "high"}]
  → Entity: [{entity_name: "John Doe", adverse_media: false, sanctions_hit: false}]

Step 4 - Reasoning:
  → ReasoningOutput: {
      verdict: "LIKELY_FRAUD",
      confidence: 85,
      incriminating: ["Classic structuring pattern", "8 deposits just below $10K"],
      exculpatory: ["No adverse media on customer"]
    }

Step 5 - Report:
  → FraudAssessment: {
      verdict: "LIKELY_FRAUD",
      confidence: 85,
      recommended_actions: ["File SAR", "Enhanced monitoring", "Restrict account"]
    }
```

---

## Environment Variables Required

```bash
# OpenAI/Gemini API
OPENAI_API_KEY=
OPENAI_BASE_URL=       # For Gemini compatibility

# Weaviate Knowledge Base
WEAVIATE_HTTP_HOST=
WEAVIATE_HTTP_PORT=
WEAVIATE_GRPC_HOST=
WEAVIATE_GRPC_PORT=
WEAVIATE_API_KEY=

# Embeddings
EMBEDDING_API_KEY=
EMBEDDING_BASE_URL=

# Web Search (Gemini Grounding)
WEB_SEARCH_API_KEY=
WEB_SEARCH_BASE_URL=

# Observability (optional)
LANGFUSE_SECRET_KEY=
LANGFUSE_PUBLIC_KEY=
```

---

## Key Design Decisions

1. **Multi-Agent Architecture**: Separates concerns into specialized agents for modularity
2. **Parallel Execution**: Specialist agents run concurrently for efficiency
3. **Dual Knowledge Sources**: Wikipedia (static) + Google Search (dynamic) for comprehensive research
4. **Pure LLM Reasoning**: Reasoning agent uses no tools - pure analytical capability
5. **Structured Outputs**: Pydantic models ensure type safety throughout pipeline
6. **Streaming UI**: Real-time progress updates for user feedback
7. **Source Citations**: All findings include source attribution for auditability
