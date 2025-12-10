"""Pydantic data models for AML fraud detection system.

This module defines all input and output models used throughout the
fraud detection pipeline.
"""

from typing import Literal

from pydantic import BaseModel, Field


# ============================================================================
# INPUT MODELS - Structured customer report data
# ============================================================================


class CustomerProfile(BaseModel):
    """Customer profile information extracted from report."""

    customer_id: str = Field(..., description="Unique customer identifier")
    name: str = Field(..., description="Customer full name")
    account_type: str = Field(..., description="Type of account")
    opening_date: str = Field(..., description="Account opening date")
    location: str = Field(..., description="Customer location (city, country)")
    registered_business: str | None = Field(
        None, description="Registered business name if applicable"
    )
    investment_profile: str = Field(..., description="Customer investment profile")
    document_date: str = Field(..., description="Date of this report")
    time_period: str = Field(..., description="Time period covered by this report")


class Transaction(BaseModel):
    """Individual transaction record."""

    date: str = Field(..., description="Transaction date")
    type: str = Field(..., description="Transaction type (Deposit, Payment, Transfer, etc.)")
    description: str = Field(..., description="Transaction description")
    fiat_amount: float = Field(..., description="FIAT amount (can be negative for outflows)")
    fiat_currency: str = Field(default="CAD", description="FIAT currency code")
    crypto_asset: str | None = Field(None, description="Crypto asset symbol (BTC, ETH, etc.)")
    crypto_qty: float | None = Field(None, description="Crypto quantity")


class CryptoHolding(BaseModel):
    """Crypto asset holding."""

    asset: str = Field(..., description="Crypto asset symbol (e.g., 'BTC', 'ETH')")
    quantity: float = Field(..., description="Quantity held")


class FinancialSummary(BaseModel):
    """Financial summary metrics from the report."""

    total_deposits: float = Field(..., description="Total deposits in FIAT")
    total_non_crypto_spend: float = Field(..., description="Total non-crypto spending/transfers")
    total_crypto_buys: float = Field(..., description="Total FIAT used for crypto purchases")
    net_crypto_holdings: list[CryptoHolding] = Field(
        default_factory=list, description="Net crypto holdings by asset"
    )
    currency: str = Field(default="CAD", description="Currency for all FIAT amounts")


class CustomerReport(BaseModel):
    """Complete customer transaction report."""

    profile: CustomerProfile = Field(..., description="Customer profile information")
    history_overview: str = Field(..., description="Narrative summary of customer activity")
    transactions: list[Transaction] = Field(..., description="List of all transactions")
    financial_summary: FinancialSummary = Field(..., description="Financial summary metrics")


# ============================================================================
# OUTPUT MODELS - Analysis results
# ============================================================================


class ExtractedSignal(BaseModel):
    """Signal extracted from customer report by Intake Agent."""

    signal_type: str = Field(..., description="Type of signal (e.g., 'high_volume_international')")
    value: str = Field(..., description="Signal value or description")
    risk_indicator: Literal["positive", "neutral", "negative"] = Field(
        ..., description="Risk assessment: positive=low risk, negative=high risk"
    )
    explanation: str = Field(..., description="Explanation of why this signal was extracted")


class InvestigationPlan(BaseModel):
    """Investigation plan created by Planner Agent."""

    typology_queries: list[str] = Field(
        default_factory=list,
        description="Queries for typology matching (e.g., 'structuring money laundering definition')",
    )
    pattern_queries: list[str] = Field(
        default_factory=list,
        description="Queries for pattern analysis (e.g., 'AML red flags international wire transfers')",
    )
    entities_to_check: list[str] = Field(
        default_factory=list,
        description="List of entities to research (customer name, business name, counterparties)",
    )
    entity_queries: list[str] = Field(
        default_factory=list,
        description="Specific entity research queries (e.g., 'Chen Lee Vancouver sanctions')",
    )
    priority_areas: list[str] = Field(
        default_factory=list, description="Priority areas for investigation"
    )
    initial_risk_assessment: Literal["low", "medium", "high"] = Field(
        ..., description="Initial risk assessment based on intake signals"
    )
    reasoning: str = Field(..., description="Reasoning for the investigation plan")


class TypologyMatch(BaseModel):
    """AML typology matching result from Typology Matcher Agent."""

    name: str = Field(..., description="Typology name (e.g., 'Structuring', 'Money Mule')")
    matched: bool = Field(..., description="Whether the activity matches this typology")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score (0.0-1.0)")
    explanation: str = Field(..., description="Explanation of the match/non-match")
    source: str = Field(..., description="Source citation (Wikipedia or Google Search)")


class RedFlag(BaseModel):
    """Red flag identified by Pattern Analyzer Agent."""

    description: str = Field(..., description="Description of the red flag")
    severity: Literal["high", "medium", "low"] = Field(..., description="Severity level")
    evidence: str = Field(..., description="Specific transaction or pattern as evidence")
    source: str | None = Field(None, description="Source citation if applicable")


class EntityCheckResult(BaseModel):
    """Entity due diligence result from Entity Research Agent."""

    entity_name: str = Field(..., description="Name of the entity checked")
    entity_type: Literal["customer", "business", "counterparty"] = Field(
        ..., description="Type of entity"
    )
    adverse_media: bool = Field(..., description="Whether adverse media was found")
    sanctions_hit: bool = Field(..., description="Whether entity appears on sanctions lists")
    pep_status: bool = Field(..., description="Whether entity is a Politically Exposed Person")
    findings: str = Field(..., description="Summary of findings")
    sources: list[str] = Field(default_factory=list, description="List of source citations")


class ReasoningOutput(BaseModel):
    """Output from Reasoning Agent - synthesized analysis of all evidence."""

    evidence_analysis: str = Field(
        ..., description="Detailed reasoning narrative synthesizing all evidence"
    )
    incriminating_factors: list[str] = Field(
        default_factory=list, description="Factors that suggest fraud or suspicious activity"
    )
    exculpatory_factors: list[str] = Field(
        default_factory=list, description="Factors that suggest legitimate activity"
    )
    confidence_score: float = Field(
        ..., ge=0.0, le=100.0, description="Confidence score (0-100) based on evidence strength"
    )
    verdict: Literal["LIKELY_FRAUD", "SUSPICIOUS", "LIKELY_LEGITIMATE"] = Field(
        ..., description="Preliminary verdict based on evidence analysis"
    )
    verdict_reasoning: str = Field(
        ..., description="Explanation of why this verdict was reached"
    )


class FraudAssessment(BaseModel):
    """Final fraud assessment report."""

    verdict: Literal["LIKELY_FRAUD", "SUSPICIOUS", "LIKELY_LEGITIMATE"] = Field(
        ..., description="Final verdict"
    )
    confidence_score: float = Field(..., ge=0.0, le=100.0, description="Confidence score (0-100)")
    risk_summary: str = Field(..., description="Brief narrative risk summary")
    typologies: list[TypologyMatch] = Field(
        default_factory=list, description="Typology matching results"
    )
    red_flags: list[RedFlag] = Field(default_factory=list, description="Red flags identified")
    entity_checks: list[EntityCheckResult] = Field(
        default_factory=list, description="Entity check results"
    )
    mitigating_factors: list[str] = Field(
        default_factory=list,
        description="Mitigating factors (e.g., 'Activity consistent with business profile')",
    )
    recommended_actions: list[str] = Field(
        default_factory=list, description="Recommended actions"
    )
    sources: list[str] = Field(default_factory=list, description="All source citations")

