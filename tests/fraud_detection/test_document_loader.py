"""Tests for document loader.

This test suite validates:
1. Loading and parsing real test data files
2. Correct extraction of all 4 sections
3. Transaction parsing with different currencies
4. Financial summary calculations
5. Error handling for invalid files
"""

from pathlib import Path

import pytest

from src.fraud_detection.document_loader import load_customer_report
from src.fraud_detection.models import CustomerReport


# Path to test data directory
TEST_DATA_DIR = Path(__file__).parent.parent.parent / "test_data"


class TestDocumentLoader:
    """Test document loader with real test data."""

    def test_load_case_01_legitimate_freelancer(self):
        """Test loading case 01: Chen Lee (legitimate freelancer)."""
        file_path = TEST_DATA_DIR / "case_01_legitimate_freelancer.txt"
        report = load_customer_report(file_path)

        # Verify it returns a CustomerReport
        assert isinstance(report, CustomerReport)

        # Verify Customer Profile
        assert report.profile.customer_id == "CUST-10044"
        assert report.profile.name == "Chen Lee"
        assert report.profile.account_type == "Business Digital & Personal Savings"
        assert report.profile.opening_date == "2020-08-10"
        assert report.profile.location == "Vancouver, BC, Canada"
        assert report.profile.registered_business == "Lee Digital Art & Design (Freelancer)"
        assert report.profile.investment_profile == "High-Volume Business/Routine Crypto Holdings"
        assert report.profile.document_date == "2025-12-09"
        assert report.profile.time_period == "Sep 1, 2025 - Nov 30, 2025"

        # Verify History Overview
        assert "Chen Lee's activity is high-volume" in report.history_overview
        assert "international digital freelancer" in report.history_overview

        # Verify Transactions
        assert len(report.transactions) == 14
        # Check first transaction
        first_txn = report.transactions[0]
        assert first_txn.date == "2025-09-03"
        assert first_txn.type == "Deposit"
        assert first_txn.description == "Incoming Wire (US Client)"
        assert first_txn.fiat_amount == 12500.00
        assert first_txn.fiat_currency == "CAD"
        assert first_txn.crypto_asset is None

        # Check a crypto transaction
        crypto_txn = report.transactions[7]  # 2025-11-01 BTC buy
        assert crypto_txn.type == "Crypto"
        assert crypto_txn.crypto_asset == "BTC"
        assert crypto_txn.crypto_qty == 0.018
        assert crypto_txn.fiat_amount == -1000.00

        # Verify Financial Summary
        assert report.financial_summary.currency == "CAD"
        # Total deposits: $12,500 + $7,800 + $6,500 + $14,000 + $5,000 = $45,800
        assert report.financial_summary.total_deposits == 45800.00
        assert report.financial_summary.total_non_crypto_spend == 25950.00
        assert report.financial_summary.total_crypto_buys == 3000.00
        # Check crypto holdings
        assert len(report.financial_summary.net_crypto_holdings) == 1
        btc_holding = next(h for h in report.financial_summary.net_crypto_holdings if h.asset == "BTC")
        assert abs(btc_holding.quantity - 0.052) < 0.001

    def test_load_case_03_fraud_structuring(self):
        """Test loading case 03: Maya Singh (fraud - structuring)."""
        file_path = TEST_DATA_DIR / "case_03_fraud_structuring.txt"
        report = load_customer_report(file_path)

        # Verify Customer Profile
        assert report.profile.customer_id == "CUST-10043"
        assert report.profile.name == "Maya Singh"
        assert report.profile.location == "London, UK"
        assert report.profile.registered_business is None  # No business registered

        # Verify currency is GBP
        assert report.transactions[0].fiat_currency == "GBP"
        assert report.financial_summary.currency == "GBP"

        # Verify multiple crypto assets
        assert len(report.transactions) == 15
        crypto_assets = {t.crypto_asset for t in report.transactions if t.crypto_asset}
        assert "BTC" in crypto_assets
        assert "ETH" in crypto_assets
        assert "ADA" in crypto_assets

        # Verify net crypto holdings
        assert len(report.financial_summary.net_crypto_holdings) == 3
        crypto_assets = {h.asset for h in report.financial_summary.net_crypto_holdings}
        assert "BTC" in crypto_assets
        assert "ETH" in crypto_assets
        assert "ADA" in crypto_assets
        # BTC: +0.12 - 0.02 = 0.10
        btc_holding = next(h for h in report.financial_summary.net_crypto_holdings if h.asset == "BTC")
        assert abs(btc_holding.quantity - 0.10) < 0.001

    def test_file_not_found(self):
        """Test error handling for non-existent file."""
        with pytest.raises(FileNotFoundError):
            load_customer_report("nonexistent_file.txt")

    def test_transaction_count_case_01(self):
        """Test that all transactions are parsed correctly."""
        file_path = TEST_DATA_DIR / "case_01_legitimate_freelancer.txt"
        report = load_customer_report(file_path)

        # Should have 14 transactions total
        assert len(report.transactions) == 14

        # Count by type
        deposits = [t for t in report.transactions if t.type == "Deposit"]
        crypto_buys = [t for t in report.transactions if t.type == "Crypto"]
        payments = [t for t in report.transactions if t.type == "Payment"]
        transfers = [t for t in report.transactions if t.type == "Transfer"]
        purchases = [t for t in report.transactions if t.type == "Purchase"]

        assert len(deposits) == 5
        assert len(crypto_buys) == 3
        assert len(payments) == 2
        assert len(transfers) == 3
        assert len(purchases) == 1

    def test_financial_calculations_case_01(self):
        """Test financial summary calculations are correct."""
        file_path = TEST_DATA_DIR / "case_01_legitimate_freelancer.txt"
        report = load_customer_report(file_path)

        # Expected values from the report
        # Total Deposits: $12,500 + $7,800 + $6,500 + $14,000 + $5,000 = $45,800
        assert abs(report.financial_summary.total_deposits - 45800.00) < 0.01

        # Total Non-Crypto Spend/Transfers: $(350 + 10,000 + 8,200 + 450 + 950 + 6,000) = $25,950
        assert abs(report.financial_summary.total_non_crypto_spend - 25950.00) < 0.01

        # Total FIAT used for Crypto Buys: $1,000 + 1,000 + 1,000 = $3,000
        assert abs(report.financial_summary.total_crypto_buys - 3000.00) < 0.01

        # Net Crypto Holdings: 0.018 + 0.017 + 0.017 = 0.052 BTC
        btc_holding = next(h for h in report.financial_summary.net_crypto_holdings if h.asset == "BTC")
        assert abs(btc_holding.quantity - 0.052) < 0.001

    def test_negative_amounts_parsed_correctly(self):
        """Test that negative amounts (outflows) are parsed correctly."""
        file_path = TEST_DATA_DIR / "case_01_legitimate_freelancer.txt"
        report = load_customer_report(file_path)

        # Find a payment transaction
        payment = next(t for t in report.transactions if t.type == "Payment")
        assert payment.fiat_amount < 0  # Should be negative

        # Find a deposit
        deposit = next(t for t in report.transactions if t.type == "Deposit")
        assert deposit.fiat_amount > 0  # Should be positive

    def test_crypto_transactions_parsed_correctly(self):
        """Test that crypto transactions have both FIAT and crypto data."""
        file_path = TEST_DATA_DIR / "case_01_legitimate_freelancer.txt"
        report = load_customer_report(file_path)

        crypto_txns = [t for t in report.transactions if t.crypto_asset]
        assert len(crypto_txns) == 3

        for txn in crypto_txns:
            assert txn.crypto_asset == "BTC"
            assert txn.crypto_qty is not None
            assert txn.crypto_qty > 0
            assert txn.fiat_amount < 0  # Buying crypto is an outflow


class TestDocumentLoaderEdgeCases:
    """Test edge cases and error handling."""

    def test_profile_without_registered_business(self):
        """Test parsing profile where registered business is N/A."""
        file_path = TEST_DATA_DIR / "case_03_fraud_structuring.txt"
        report = load_customer_report(file_path)

        # Maya Singh has no registered business
        assert report.profile.registered_business is None

    def test_multiple_currencies(self):
        """Test that different test cases use different currencies."""
        case_01 = load_customer_report(TEST_DATA_DIR / "case_01_legitimate_freelancer.txt")
        case_03 = load_customer_report(TEST_DATA_DIR / "case_03_fraud_structuring.txt")

        assert case_01.financial_summary.currency == "CAD"
        assert case_03.financial_summary.currency == "GBP"

    def test_crypto_sell_transaction(self):
        """Test parsing crypto sell transactions (positive FIAT, negative crypto)."""
        file_path = TEST_DATA_DIR / "case_03_fraud_structuring.txt"
        report = load_customer_report(file_path)

        # Find the BTC sale transaction (2025-11-28)
        btc_sale = next(
            t for t in report.transactions
            if t.date == "2025-11-28" and t.type == "Crypto"
        )
        assert btc_sale.fiat_amount > 0  # Selling crypto is an inflow
        assert btc_sale.crypto_qty == -0.02  # Negative crypto quantity

