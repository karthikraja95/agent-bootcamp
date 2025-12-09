"""Tests for fraud detection data models.

This test suite validates:
1. Model instantiation with valid data
2. Field validation (types, constraints)
3. Serialization/deserialization (JSON round-trip)
4. Edge cases and error handling
"""

import pytest
from pydantic import ValidationError

from src.fraud_detection.models import (
    CryptoHolding,
    CustomerProfile,
    CustomerReport,
    EntityCheckResult,
    ExtractedSignal,
    FinancialSummary,
    FraudAssessment,
    RedFlag,
    Transaction,
    TypologyMatch,
)


class TestCustomerProfile:
    """Test CustomerProfile model."""

    def test_valid_profile(self):
        """Test creating a valid customer profile."""
        profile = CustomerProfile(
            customer_id="CUST-10044",
            name="Chen Lee",
            account_type="Business Digital & Personal Savings",
            opening_date="2020-08-10",
            location="Vancouver, BC, Canada",
            registered_business="Lee Digital Art & Design (Freelancer)",
            investment_profile="High-Volume Business/Routine Crypto Holdings",
            document_date="2025-12-09",
            time_period="Sep 1, 2025 - Nov 30, 2025",
        )
        assert profile.customer_id == "CUST-10044"
        assert profile.name == "Chen Lee"
        assert profile.registered_business is not None

    def test_profile_without_business(self):
        """Test profile without registered business (optional field)."""
        profile = CustomerProfile(
            customer_id="CUST-99999",
            name="John Doe",
            account_type="Personal Savings",
            opening_date="2023-01-01",
            location="Toronto, ON, Canada",
            investment_profile="Low-Risk Saver",
            document_date="2025-12-09",
            time_period="Jan 1, 2025 - Dec 31, 2025",
        )
        assert profile.registered_business is None

    def test_profile_json_roundtrip(self):
        """Test JSON serialization and deserialization."""
        profile = CustomerProfile(
            customer_id="CUST-10044",
            name="Chen Lee",
            account_type="Business Digital",
            opening_date="2020-08-10",
            location="Vancouver, BC, Canada",
            investment_profile="High-Volume Business",
            document_date="2025-12-09",
            time_period="Sep 1, 2025 - Nov 30, 2025",
        )
        json_str = profile.model_dump_json()
        restored = CustomerProfile.model_validate_json(json_str)
        assert restored == profile


class TestTransaction:
    """Test Transaction model."""

    def test_fiat_transaction(self):
        """Test FIAT-only transaction."""
        txn = Transaction(
            date="2025-09-05",
            type="Deposit",
            description="Freelance payment from XYZ Corp",
            fiat_amount=12500.00,
            fiat_currency="CAD",
        )
        assert txn.crypto_asset is None
        assert txn.crypto_qty is None

    def test_crypto_transaction(self):
        """Test crypto purchase transaction."""
        txn = Transaction(
            date="2025-09-10",
            type="Crypto Buy",
            description="BTC purchase via CoinExchange",
            fiat_amount=-1000.00,
            fiat_currency="CAD",
            crypto_asset="BTC",
            crypto_qty=0.018,
        )
        assert txn.crypto_asset == "BTC"
        assert txn.crypto_qty == 0.018
        assert txn.fiat_amount < 0  # Outflow

    def test_multi_currency(self):
        """Test transaction with different currency."""
        txn = Transaction(
            date="2025-10-01",
            type="Deposit",
            description="Cash deposit",
            fiat_amount=4950.00,
            fiat_currency="GBP",
        )
        assert txn.fiat_currency == "GBP"


class TestFinancialSummary:
    """Test FinancialSummary model."""

    def test_valid_summary(self):
        """Test creating a valid financial summary."""
        summary = FinancialSummary(
            total_deposits=40800.00,
            total_non_crypto_spend=25950.00,
            total_crypto_buys=3000.00,
            net_crypto_holdings=[CryptoHolding(asset="BTC", quantity=0.052)],
            currency="CAD",
        )
        assert summary.total_deposits == 40800.00
        assert len(summary.net_crypto_holdings) == 1
        assert summary.net_crypto_holdings[0].asset == "BTC"
        assert summary.net_crypto_holdings[0].quantity == 0.052

    def test_multiple_crypto_assets(self):
        """Test summary with multiple crypto assets."""
        summary = FinancialSummary(
            total_deposits=50000.00,
            total_non_crypto_spend=10000.00,
            total_crypto_buys=5000.00,
            net_crypto_holdings=[
                CryptoHolding(asset="BTC", quantity=0.052),
                CryptoHolding(asset="ETH", quantity=1.5),
                CryptoHolding(asset="USDT", quantity=1000.0),
            ],
            currency="USD",
        )
        assert len(summary.net_crypto_holdings) == 3


class TestCustomerReport:
    """Test CustomerReport model (composite)."""

    def test_complete_report(self):
        """Test creating a complete customer report."""
        profile = CustomerProfile(
            customer_id="CUST-10044",
            name="Chen Lee",
            account_type="Business Digital",
            opening_date="2020-08-10",
            location="Vancouver, BC, Canada",
            investment_profile="High-Volume Business",
            document_date="2025-12-09",
            time_period="Sep 1, 2025 - Nov 30, 2025",
        )
        transactions = [
            Transaction(
                date="2025-09-05",
                type="Deposit",
                description="Freelance payment",
                fiat_amount=12500.00,
                fiat_currency="CAD",
            )
        ]
        summary = FinancialSummary(
            total_deposits=12500.00,
            total_non_crypto_spend=0.00,
            total_crypto_buys=0.00,
            net_crypto_holdings=[],
            currency="CAD",
        )
        report = CustomerReport(
            profile=profile,
            history_overview="Customer is a freelance digital artist...",
            transactions=transactions,
            financial_summary=summary,
        )
        assert report.profile.customer_id == "CUST-10044"
        assert len(report.transactions) == 1


class TestExtractedSignal:
    """Test ExtractedSignal model."""

    def test_valid_signal(self):
        """Test creating a valid extracted signal."""
        signal = ExtractedSignal(
            signal_type="high_volume_international",
            value="$40,800 in international deposits",
            risk_indicator="neutral",
            explanation="High volume consistent with freelance business profile",
        )
        assert signal.risk_indicator == "neutral"

    def test_invalid_risk_indicator(self):
        """Test that invalid risk_indicator raises ValidationError."""
        with pytest.raises(ValidationError):
            ExtractedSignal(
                signal_type="test",
                value="test",
                risk_indicator="invalid",  # type: ignore
                explanation="test",
            )


class TestTypologyMatch:
    """Test TypologyMatch model."""

    def test_matched_typology(self):
        """Test a matched typology."""
        match = TypologyMatch(
            name="Structuring",
            matched=True,
            confidence=0.85,
            explanation="Multiple deposits just under reporting threshold",
            source="Wikipedia: Structuring (money laundering)",
        )
        assert match.matched is True
        assert 0.0 <= match.confidence <= 1.0

    def test_confidence_validation(self):
        """Test confidence score validation."""
        with pytest.raises(ValidationError):
            TypologyMatch(
                name="Test",
                matched=False,
                confidence=1.5,  # Invalid: > 1.0
                explanation="Test",
                source="Test",
            )


class TestRedFlag:
    """Test RedFlag model."""

    def test_valid_red_flag(self):
        """Test creating a valid red flag."""
        flag = RedFlag(
            description="Cash deposits just under £10,000 threshold",
            severity="high",
            evidence="Deposits of £9,950, £4,950, £4,900",
            source="Pattern analysis",
        )
        assert flag.severity == "high"


class TestEntityCheckResult:
    """Test EntityCheckResult model."""

    def test_clean_entity(self):
        """Test entity with no adverse findings."""
        result = EntityCheckResult(
            entity_name="Chen Lee",
            entity_type="customer",
            adverse_media=False,
            sanctions_hit=False,
            pep_status=False,
            findings="No adverse media or sanctions hits found",
            sources=["Google Search: Chen Lee Vancouver artist"],
        )
        assert result.adverse_media is False
        assert result.sanctions_hit is False

    def test_adverse_entity(self):
        """Test entity with adverse findings."""
        result = EntityCheckResult(
            entity_name="Suspicious Corp",
            entity_type="business",
            adverse_media=True,
            sanctions_hit=True,
            pep_status=False,
            findings="Entity appears on OFAC sanctions list",
            sources=["OFAC Sanctions List", "Reuters: Suspicious Corp investigation"],
        )
        assert result.sanctions_hit is True


class TestFraudAssessment:
    """Test FraudAssessment model (final output)."""

    def test_legitimate_assessment(self):
        """Test a legitimate fraud assessment."""
        assessment = FraudAssessment(
            verdict="LIKELY_LEGITIMATE",
            confidence_score=80.0,
            risk_summary="Activity consistent with legitimate freelance business",
            typologies=[],
            red_flags=[],
            entity_checks=[],
            mitigating_factors=["Consistent business profile", "No adverse media"],
            recommended_actions=["Continue routine monitoring"],
            sources=["Wikipedia: AML typologies", "Google: Chen Lee artist"],
        )
        assert assessment.verdict == "LIKELY_LEGITIMATE"
        assert 0.0 <= assessment.confidence_score <= 100.0

    def test_fraud_assessment(self):
        """Test a fraud assessment."""
        assessment = FraudAssessment(
            verdict="LIKELY_FRAUD",
            confidence_score=90.0,
            risk_summary="Classic structuring pattern detected",
            typologies=[
                TypologyMatch(
                    name="Structuring",
                    matched=True,
                    confidence=0.9,
                    explanation="Deposits under threshold",
                    source="Wikipedia",
                )
            ],
            red_flags=[
                RedFlag(
                    description="Structured deposits",
                    severity="high",
                    evidence="£9,950 deposits",
                )
            ],
            entity_checks=[],
            mitigating_factors=[],
            recommended_actions=["File SAR", "Enhanced monitoring"],
            sources=["Wikipedia: Structuring"],
        )
        assert assessment.verdict == "LIKELY_FRAUD"
        assert len(assessment.typologies) == 1

    def test_confidence_score_validation(self):
        """Test confidence score must be 0-100."""
        with pytest.raises(ValidationError):
            FraudAssessment(
                verdict="SUSPICIOUS",
                confidence_score=150.0,  # Invalid: > 100
                risk_summary="Test",
            )

