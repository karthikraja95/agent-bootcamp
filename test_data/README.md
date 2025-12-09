# AML Fraud Detection Test Data

This directory contains comprehensive test cases for the multi-agent fraud detection system. Each case is designed to test different aspects of the system's ability to identify fraud, legitimate activity, and grey area cases requiring deeper investigation.

## Test Case Overview

| Case # | File Name | Category | Expected Verdict | Key Features |
|--------|-----------|----------|------------------|--------------|
| 01 | `case_01_legitimate_freelancer.txt` | **LEGITIMATE** | LIKELY_LEGITIMATE | International freelancer with consistent business profile |
| 02 | `case_02_legitimate_executive.txt` | **LEGITIMATE** | LIKELY_LEGITIMATE | High-income executive with documented investment strategy |
| 03 | `case_03_fraud_structuring.txt` | **FRAUD** | LIKELY_FRAUD | Classic structuring pattern with offshore crypto exchange |
| 04 | `case_04_grey_area_sudden_change.txt` | **GREY AREA** | SUSPICIOUS | Sudden behavior change, income inconsistency |
| 05 | `case_05_company_legitimate_tech.txt` | **LEGITIMATE** | LIKELY_LEGITIMATE | Venture-backed SaaS company with normal operations |
| 06 | `case_06_company_fraud_shell.txt` | **FRAUD** | LIKELY_FRAUD | Shell company with no real business operations |
| 07 | `case_07_grey_area_crypto_trader.txt` | **GREY AREA** | SUSPICIOUS | Legitimate trader with concerning P2P activity |
| 08 | `case_08_fraud_money_mule.txt` | **FRAUD** | LIKELY_FRAUD | Classic money mule pattern |
| 09 | `case_09_company_grey_area_nft.txt` | **GREY AREA** | SUSPICIOUS | NFT business with potential wash trading |
| 10 | `case_10_legitimate_immigrant_remittance.txt` | **LEGITIMATE** | LIKELY_LEGITIMATE | Healthcare worker with family remittances |

## Case Details

### LEGITIMATE Cases (Expected: LIKELY_LEGITIMATE)

#### Case 01: Chen Lee - International Freelancer
- **Profile**: Digital art freelancer with international clients
- **Key Patterns**: Regular business deposits, scheduled crypto DCA, consistent with profile
- **Test Focus**: System should recognize legitimate international business activity
- **Red Flags to Dismiss**: High-volume international transfers (explained by business)
- **Expected Confidence**: 75-85%

#### Case 02: Emily Smith - Tech Executive
- **Profile**: High-income executive with established investment plan
- **Key Patterns**: Predictable salary, scheduled investments, documented tuition payment
- **Test Focus**: System should recognize legitimate wealth management
- **Red Flags to Dismiss**: Large international transfer (documented tuition)
- **Expected Confidence**: 80-90%

#### Case 05: NeuralSync Technologies - SaaS Company
- **Profile**: Venture-backed AI software company
- **Key Patterns**: Regular payroll, client subscriptions, Series A funding, EU expansion
- **Test Focus**: System should verify company legitimacy via Google Search
- **Red Flags to Dismiss**: Large funding round, international transfers (business expansion)
- **Expected Confidence**: 85-95%

#### Case 10: Maria Gonzalez - Healthcare Worker
- **Profile**: CNA sending family remittances
- **Key Patterns**: Consistent salary, regular remittances, documented medical emergency
- **Test Focus**: System should distinguish legitimate remittances from money laundering
- **Red Flags to Dismiss**: International transfers (family support, not business)
- **Expected Confidence**: 80-90%

---

### FRAUD Cases (Expected: LIKELY_FRAUD)

#### Case 03: Maya Singh - Structuring
- **Profile**: Low-risk customer with sudden structured crypto activity
- **Key Patterns**: Cash deposits under threshold, transfers to offshore exchange, rapid liquidation
- **Test Focus**: System should identify structuring typology
- **Critical Red Flags**: 
  - Frequent cash deposits just under reporting threshold
  - Transfers to high-risk offshore exchange (DigitalGulf)
  - Unexplained large cash withdrawal
  - Travel to Dubai with no documented business
- **Expected Confidence**: 85-95%

#### Case 06: Global Trade Solutions - Shell Company
- **Profile**: Recently incorporated LLC with no real operations
- **Key Patterns**: No payroll, rapid pass-through of $3.6M, 15+ countries, immediate closure
- **Test Focus**: System should identify shell company and layering
- **Critical Red Flags**:
  - No employees or operating expenses
  - Registered agent address only
  - Rapid pass-through (same-day transfers)
  - Multiple offshore tax havens
  - Account closure immediately after activity
- **Expected Confidence**: 90-98%

#### Case 08: Sarah Thompson - Money Mule
- **Profile**: Recent graduate "processing payments"
- **Key Patterns**: 90% forwarding rate, 28 unknown companies, 25 countries, <4 hour turnaround
- **Test Focus**: System should identify money mule typology
- **Critical Red Flags**:
  - Unemployed processing $491K in 3 months
  - 10% retention (classic mule commission)
  - Immediate forwarding of funds
  - Unable to provide business documentation
  - "Work from home payment processing" (common mule pitch)
- **Expected Confidence**: 90-98%

---

### GREY AREA Cases (Expected: SUSPICIOUS)

#### Case 04: Marcus Johnson - Sudden Behavior Change
- **Profile**: 7-year stable account with sudden dramatic shift
- **Key Patterns**: $87K in international wires (vs $55K salary), immediate crypto conversion, large cash withdrawals
- **Test Focus**: System should flag inconsistency and recommend investigation
- **Concerning Factors**:
  - Income inconsistency (wires from Nigeria, UAE, Hong Kong)
  - No prior crypto activity, then sudden high-volume
  - Multiple exchange accounts opened simultaneously
  - Cash withdrawals just under $10K threshold
- **Mitigating Factors**: None documented (no business, no explanation)
- **Expected Confidence**: 60-75% (requires investigation)

#### Case 07: Alex Rivera - Crypto Trader with P2P Activity
- **Profile**: Documented day trader with concerning patterns
- **Key Patterns**: Legitimate trading mixed with P2P receipts, privacy coins, mixing services
- **Test Focus**: System should identify mixed legitimate/suspicious activity
- **Concerning Factors**:
  - $167K in P2P transfers from unknown sources
  - Privacy coin purchases (Monero, Zcash)
  - Mixing service usage (Tornado Cash)
  - Transfers to non-KYC exchanges
  - Large cash withdrawals
- **Mitigating Factors**:
  - 3-year trading history
  - Tax returns filed
  - Legitimate trading is profitable
  - Uses regulated exchanges for majority
- **Expected Confidence**: 55-70% (requires investigation)

#### Case 09: MetaVerse Galleries - NFT Business
- **Profile**: NFT gallery with legitimate operations and suspicious sales
- **Key Patterns**: Mix of real gallery business and ultra-high-value anonymous NFT sales
- **Test Focus**: System should navigate complex legitimate/suspicious mix
- **Concerning Factors**:
  - $2.45M in sales to wallets with no history
  - Immediate conversion and offshore distribution
  - Anonymous DAO contributions
  - Potential wash trading
  - Privacy coin conversions
- **Mitigating Factors**:
  - Physical gallery with real operations
  - Regular payroll (12 employees)
  - Verified artist collaborations
  - 2+ years operating history
  - NFT market legitimately volatile
- **Expected Confidence**: 50-65% (difficult to assess)

---

## Testing Strategy

### Agent Capabilities to Test

1. **Intake Agent**: Parse structured reports accurately
2. **Planner Agent**: Identify appropriate investigation areas
3. **Typology Matcher**: Match patterns to AML typologies (structuring, money mule, layering, shell company)
4. **Pattern Analyzer**: Identify red flags and distinguish from legitimate activity
5. **Entity Research**: Use Google Search to verify companies, individuals, and check for adverse media
6. **Reasoning Agent**: Weigh evidence and reach balanced conclusions
7. **Report Agent**: Generate comprehensive, actionable assessments

### Expected System Behaviors

#### For Legitimate Cases:
- Identify potential red flags but explain them with context
- Verify entities via Google Search (companies, funding rounds, etc.)
- Recognize patterns consistent with stated business/employment
- Provide high confidence scores (75-95%)
- Recommend standard monitoring (no escalation)

#### For Fraud Cases:
- Identify multiple AML typologies
- Flag critical red flags with strong evidence
- Note absence of legitimate business documentation
- Provide high confidence scores (85-98%)
- Recommend immediate escalation and SAR filing

#### For Grey Area Cases:
- Identify both suspicious and mitigating factors
- Acknowledge uncertainty and complexity
- Provide moderate confidence scores (50-75%)
- Recommend enhanced due diligence and investigation
- Suggest specific follow-up actions

---

## Usage

Each `.txt` file can be:
1. Uploaded directly to the Gradio UI
2. Copy-pasted into the text input field
3. Used for automated testing and evaluation

The system should process each case and generate a `FraudAssessment` with:
- Verdict (LIKELY_FRAUD / SUSPICIOUS / LIKELY_LEGITIMATE)
- Confidence score (0-100)
- Typology matches
- Red flags identified
- Entity check results
- Mitigating factors
- Recommended actions
- Source citations

---

## Real-World Accuracy

These cases are based on:
- Actual AML typologies from FATF guidance
- Real-world fraud patterns from FinCEN advisories
- Legitimate business scenarios from various industries
- Common false positive scenarios in AML systems
- Grey area cases that challenge human analysts

The data is synthetic but designed to closely mirror real-world complexity.

