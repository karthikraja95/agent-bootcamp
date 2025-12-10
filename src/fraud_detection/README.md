# AML Fraud Detection Multi-Agent System

A production-ready multi-agent system for analyzing customer transaction reports and detecting potential money laundering activities.

## 🚀 Quick Start

### Launch the Web UI

```bash
uv run --env-file .env python launch_app.py
```

Access the UI at: http://localhost:7860

**Note**: A public share link will also be generated (expires in 1 week)

### Use the Python API

```python
from openai import AsyncOpenAI
from src.fraud_detection import analyze_fraud_report
from src.utils import AsyncWeaviateKnowledgeBase, Configs, get_weaviate_async_client
from src.utils.tools.gemini_grounding import GeminiGroundingWithGoogleSearch

# Initialize clients
configs = Configs.from_env_var()
async_openai_client = AsyncOpenAI()

async_weaviate_client = get_weaviate_async_client(
    http_host=configs.weaviate_http_host,
    http_port=configs.weaviate_http_port,
    # ... other config
)
async_knowledgebase = AsyncWeaviateKnowledgeBase(
    async_weaviate_client,
    collection_name="enwiki_20250520",
)
gemini_grounding = GeminiGroundingWithGoogleSearch()

# Analyze a report
raw_report = """
I. Customer Profile
Customer ID: CUST-10044
Name: Chen Lee
...
"""

assessment = await analyze_fraud_report(
    raw_report,
    async_openai_client,
    async_knowledgebase,
    gemini_grounding,
)

print(f"Verdict: {assessment.verdict}")
print(f"Confidence: {assessment.confidence_score}%")
```

## 📊 System Architecture

The system uses a multi-agent pipeline with 7 specialized agents:

1. **Intake Agent** (Gemini 2.5 Flash) - Parses raw text and extracts fraud signals
2. **Planner Agent** (Gemini 2.5 Pro) - Creates investigation plan
3. **Specialist Agents** (Gemini 2.5 Flash):
   - **Typology Matcher** - Matches AML typologies using Wikipedia + Google Search
   - **Pattern Analyzer** - Identifies suspicious patterns using Wikipedia + Google Search
   - **Entity Research** - Researches entities for adverse media using Google Search
4. **Reasoning Agent** (Gemini 2.5 Pro) - Synthesizes all evidence
5. **Report Agent** (Gemini 2.5 Flash) - Generates final fraud assessment

## 🔍 Features

- ✅ **Real-time Streaming** - Watch the investigation unfold in real-time
- ✅ **Multi-Source Intelligence** - Combines Wikipedia knowledge + Google Search
- ✅ **Structured Output** - Guaranteed JSON structure with Pydantic validation
- ✅ **Parallel Execution** - Specialist agents run concurrently for speed
- ✅ **LangFuse Tracing** - Full observability and debugging
- ✅ **Production Ready** - 84+ tests passing, comprehensive error handling

## 📝 Input Format

The system expects customer transaction reports in this format:

```
I. Customer Profile
Field                   Value
Customer ID             CUST-10044
Name                    Chen Lee
Account Type            Business Digital & Personal Savings
Opening Date            2020-08-10
...

II. Customer History Overview
[Narrative description of customer activity]

III. Transaction History Detail
Date            Type            Description                             FIAT Amount (CAD)
2025-09-03      Deposit         Incoming Wire (US Client)               +$12,500.00
...
```

See `test_data/` directory for example reports.

## 📤 Output Format

The system returns a `FraudAssessment` with:

- **verdict**: "LIKELY_FRAUD" | "SUSPICIOUS" | "LIKELY_LEGITIMATE"
- **confidence_score**: 0-100
- **risk_summary**: Executive summary of findings
- **incriminating_factors**: List of red flags
- **mitigating_factors**: List of legitimate explanations
- **recommended_actions**: Next steps for compliance team

## 🧪 Testing

```bash
# Run all tests
uv run pytest tests/fraud_detection/ -v

# Run specific test suite
uv run pytest tests/fraud_detection/test_orchestrator.py -v

# Run with coverage
uv run pytest tests/fraud_detection/ --cov=src/fraud_detection
```

## 📚 Documentation

- **Implementation Log**: See `IMPLEMENTATION_LOG.md` for detailed implementation notes
- **Plan**: See `plan.md` for original design specification
- **Test Data**: See `test_data/` for example customer reports

## 🔧 Configuration

Required environment variables (in `.env`):

```bash
# OpenAI API (for Gemini models)
OPENAI_API_KEY=your_key_here
OPENAI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/

# Weaviate (for Wikipedia knowledge base)
WEAVIATE_HTTP_HOST=your_host
WEAVIATE_HTTP_PORT=443
WEAVIATE_GRPC_HOST=your_host
WEAVIATE_GRPC_PORT=443
WEAVIATE_API_KEY=your_key

# LangFuse (for tracing)
LANGFUSE_SECRET_KEY=your_key
LANGFUSE_PUBLIC_KEY=your_key
LANGFUSE_HOST=https://cloud.langfuse.com
```

## 🎯 Use Cases

- **AML Compliance**: Automated first-pass review of customer transaction reports
- **Risk Assessment**: Identify high-risk customers for manual review
- **Investigation Support**: Gather evidence and context for compliance officers
- **Audit Trail**: Full traceability with LangFuse traces and citations

## 🚨 Limitations

- **Not a replacement for human judgment** - Always requires manual review
- **Requires quality input data** - Garbage in, garbage out
- **LLM hallucination risk** - Always verify citations and sources
- **Rate limits** - Subject to API rate limits (Gemini, Google Search)

## 📄 License

See main repository LICENSE file.
