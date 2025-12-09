"""Document loader for customer transaction reports.

This module parses structured .txt customer reports into CustomerReport objects.
"""

import re
from pathlib import Path

from .models import CustomerProfile, CustomerReport, FinancialSummary, Transaction


def load_customer_report(file_path: str | Path) -> CustomerReport:
    """Load and parse a customer transaction report from a .txt file.

    Parameters
    ----------
    file_path : str | Path
        Path to the .txt customer report file.

    Returns
    -------
    CustomerReport
        Parsed customer report with profile, history, transactions, and summary.

    Raises
    ------
    FileNotFoundError
        If the file does not exist.
    ValueError
        If the file format is invalid or required sections are missing.
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    content = file_path.read_text(encoding="utf-8")

    # Parse the 4 sections
    profile = _parse_customer_profile(content)
    history_overview = _parse_history_overview(content)
    transactions = _parse_transactions(content)
    financial_summary = _parse_financial_summary(content, transactions)

    return CustomerReport(
        profile=profile,
        history_overview=history_overview,
        transactions=transactions,
        financial_summary=financial_summary,
    )


def _parse_customer_profile(content: str) -> CustomerProfile:
    """Parse Section I: Customer Profile."""
    section_match = re.search(
        r"I\.\s+Customer Profile\s+(.*?)(?=\n\n|\nII\.)", content, re.DOTALL
    )
    if not section_match:
        raise ValueError("Section I: Customer Profile not found")

    section_text = section_match.group(1)

    # Extract fields using regex
    def extract_field(field_name: str) -> str | None:
        pattern = rf"{field_name}\s+(.+?)(?=\n|$)"
        match = re.search(pattern, section_text)
        return match.group(1).strip() if match else None

    customer_id = extract_field("Customer ID")
    name = extract_field("Name")
    account_type = extract_field("Account Type")
    opening_date = extract_field("Opening Date")
    location = extract_field("Location")
    registered_business = extract_field("Registered Business")
    investment_profile = extract_field("Investment Profile")
    document_date = extract_field("Document Date")
    time_period = extract_field("Time Period")

    if not all([customer_id, name, account_type, opening_date, location,
                investment_profile, document_date, time_period]):
        raise ValueError("Missing required fields in Customer Profile section")

    return CustomerProfile(
        customer_id=customer_id,
        name=name,
        account_type=account_type,
        opening_date=opening_date,
        location=location,
        registered_business=registered_business if registered_business != "N/A" else None,
        investment_profile=investment_profile,
        document_date=document_date,
        time_period=time_period,
    )


def _parse_history_overview(content: str) -> str:
    """Parse Section II: Customer History Overview."""
    section_match = re.search(
        r"II\.\s+Customer History Overview\s+(.*?)(?=\n\nIII\.)", content, re.DOTALL
    )
    if not section_match:
        raise ValueError("Section II: Customer History Overview not found")

    return section_match.group(1).strip()


def _parse_transactions(content: str) -> list[Transaction]:
    """Parse Section III: Transaction History Detail."""
    section_match = re.search(
        r"III\.\s+Transaction History Detail\s+(.*?)(?=\n\nIV\.)", content, re.DOTALL
    )
    if not section_match:
        raise ValueError("Section III: Transaction History Detail not found")

    section_text = section_match.group(1)

    # Extract currency from the preamble (e.g., "All FIAT amounts are in CAD")
    currency_match = re.search(r"amounts are in ([A-Z]{3})", section_text)
    default_currency = currency_match.group(1) if currency_match else "CAD"

    # Find the transaction table (starts after the header row)
    transactions = []
    # Match transaction lines: Date, Type, Description, Amount, Crypto Asset, Crypto QTY
    pattern = r"(\d{4}-\d{2}-\d{2})\s+(\S+)\s+(.+?)\s+([-+]?[£$€]?[\d,]+\.\d{2})\s+(\S+)\s+(.+?)(?=\n|$)"

    for match in re.finditer(pattern, section_text):
        date = match.group(1).strip()
        txn_type = match.group(2).strip()
        description = match.group(3).strip()
        amount_str = match.group(4).strip()
        crypto_asset = match.group(5).strip()
        crypto_qty_str = match.group(6).strip()

        # Parse FIAT amount (remove currency symbols and commas)
        fiat_amount = float(re.sub(r"[£$€,]", "", amount_str))

        # Parse crypto asset and quantity
        crypto_asset_parsed = None if crypto_asset == "N/A" else crypto_asset
        crypto_qty = None
        if crypto_qty_str and crypto_qty_str != "N/A":
            crypto_qty = float(re.sub(r"[+,]", "", crypto_qty_str))

        transactions.append(
            Transaction(
                date=date,
                type=txn_type,
                description=description,
                fiat_amount=fiat_amount,
                fiat_currency=default_currency,
                crypto_asset=crypto_asset_parsed,
                crypto_qty=crypto_qty,
            )
        )

    return transactions


def _parse_financial_summary(content: str, transactions: list[Transaction]) -> FinancialSummary:
    """Parse Section IV: Financial & Crypto Summary."""
    # Extract currency from transactions
    currency = transactions[0].fiat_currency if transactions else "CAD"

    # Calculate totals from transactions
    total_deposits = sum(t.fiat_amount for t in transactions if t.fiat_amount > 0 and not t.crypto_asset)
    total_non_crypto_spend = abs(sum(t.fiat_amount for t in transactions if t.fiat_amount < 0 and not t.crypto_asset))
    total_crypto_buys = abs(sum(t.fiat_amount for t in transactions if t.fiat_amount < 0 and t.crypto_asset))

    # Calculate net crypto holdings
    net_crypto_holdings: dict[str, float] = {}
    for t in transactions:
        if t.crypto_asset and t.crypto_qty:
            if t.crypto_asset not in net_crypto_holdings:
                net_crypto_holdings[t.crypto_asset] = 0.0
            net_crypto_holdings[t.crypto_asset] += t.crypto_qty

    return FinancialSummary(
        total_deposits=total_deposits,
        total_non_crypto_spend=total_non_crypto_spend,
        total_crypto_buys=total_crypto_buys,
        net_crypto_holdings=net_crypto_holdings,
        currency=currency,
    )

