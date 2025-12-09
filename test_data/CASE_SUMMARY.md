# Quick Reference: Test Case Summary

## 📊 Distribution

- **LEGITIMATE**: 4 cases (40%)
- **FRAUD**: 3 cases (30%)
- **GREY AREA**: 3 cases (30%)

---

## ✅ LEGITIMATE CASES

### Case 01: Chen Lee - International Freelancer 🎨
**Verdict**: LIKELY_LEGITIMATE (75-85% confidence)
- Digital art freelancer, Vancouver, Canada
- $40.8K business deposits from international clients
- Scheduled BTC purchases ($3K total)
- **Key Test**: International transfers should NOT trigger false positive

### Case 02: Emily Smith - Tech Executive 💼
**Verdict**: LIKELY_LEGITIMATE (80-90% confidence)
- Tech executive, New York, USA
- $51.2K salary + investments
- $15K international wire (documented tuition)
- **Key Test**: High-value legitimate transactions should be recognized

### Case 05: NeuralSync Technologies - SaaS Company 🚀
**Verdict**: LIKELY_LEGITIMATE (85-95% confidence)
- AI SaaS company, San Francisco, USA
- $2.5M Series A funding (Sequoia Capital - verifiable via Google)
- EU expansion with Ireland subsidiary
- **Key Test**: Google Search should verify company legitimacy

### Case 10: Maria Gonzalez - Healthcare Worker 🏥
**Verdict**: LIKELY_LEGITIMATE (80-90% confidence)
- CNA, Los Angeles, USA
- $22.8K salary, regular remittances to El Salvador/Guatemala
- Documented medical emergency (mother's surgery)
- **Key Test**: Legitimate remittances vs money laundering

---

## 🚨 FRAUD CASES

### Case 03: Maya Singh - Structuring 💰
**Verdict**: LIKELY_FRAUD (85-95% confidence)
- London, UK - Low-risk profile suddenly high-volume
- Cash deposits just under thresholds
- Transfers to offshore exchange (DigitalGulf)
- £9,950 cash withdrawal (just under £10K threshold)
- **Typologies**: Structuring, Crypto Layering
- **Key Test**: Classic structuring pattern detection

### Case 06: Global Trade Solutions - Shell Company 🏢
**Verdict**: LIKELY_FRAUD (90-98% confidence)
- Delaware LLC, no employees, no operations
- $3.6M pass-through in 3 months
- 15 countries, rapid same-day transfers
- Offshore accounts (Cayman, Switzerland, BVI)
- Account closure immediately after activity
- **Typologies**: Shell Company, Layering, Trade-Based Laundering
- **Key Test**: Identify shell company with no real business

### Case 08: Sarah Thompson - Money Mule 📮
**Verdict**: LIKELY_FRAUD (90-98% confidence)
- Phoenix, USA - Recent graduate, unemployed
- $491K processed in 3 months
- 90% forwarding rate, 10% retention (classic mule commission)
- 28 unknown companies, 25 destination countries
- <4 hour turnaround (deposit to transfer)
- **Typologies**: Money Mule, BEC Proceeds Laundering
- **Key Test**: Classic money mule pattern recognition

---

## ⚠️ GREY AREA CASES

### Case 04: Marcus Johnson - Sudden Behavior Change 🔄
**Verdict**: SUSPICIOUS (60-75% confidence)
- Miami, USA - Retail manager ($55K salary)
- $87K in international wires (Nigeria, UAE, Hong Kong)
- No prior crypto activity → sudden $52K crypto purchases
- 4 exchange accounts opened in 2 weeks
- Cash withdrawals just under $10K threshold
- **Concerns**: Income inconsistency, no documentation
- **Mitigating**: None identified
- **Recommendation**: Enhanced due diligence required

### Case 07: Alex Rivera - Crypto Trader with P2P Activity 📈
**Verdict**: SUSPICIOUS (55-70% confidence)
- Austin, USA - Documented day trader (3 years)
- $1.24M legitimate trading volume
- $167K in P2P transfers from unknown wallets
- Privacy coins (Monero, Zcash), mixing services (Tornado Cash)
- $135K cash withdrawals
- **Concerns**: Unknown P2P sources, privacy tools, non-KYC exchanges
- **Mitigating**: Tax returns filed, 3-year history, profitable trading
- **Recommendation**: Investigate P2P sources, monitor privacy coin usage

### Case 09: MetaVerse Galleries - NFT Business 🖼️
**Verdict**: SUSPICIOUS (50-65% confidence)
- Miami, USA - NFT gallery + marketplace
- $3.32M NFT sales (some to anonymous wallets with no history)
- Three ultra-high-value sales: $500K, $750K, $1.2M
- Offshore distributions (Cayman Islands, BVI)
- Privacy coin conversions ($180K)
- **Concerns**: Potential wash trading, anonymous buyers, offshore entities
- **Mitigating**: Physical gallery, 12 employees, 2+ years history, verified artists
- **Recommendation**: Investigate high-value anonymous sales, monitor for wash trading

---

## 🎯 Testing Objectives by Case

| Case | Primary Test Objective |
|------|------------------------|
| 01 | Don't flag legitimate international freelance business |
| 02 | Recognize documented high-income investment activity |
| 03 | Detect classic structuring pattern |
| 04 | Flag sudden unexplained behavior changes |
| 05 | Use Google Search to verify company legitimacy |
| 06 | Identify shell company with no real operations |
| 07 | Navigate mixed legitimate/suspicious activity |
| 08 | Detect money mule typology |
| 09 | Handle complex NFT business grey area |
| 10 | Distinguish legitimate remittances from laundering |

---

## 📋 Expected Agent Actions

### Intake Agent
- Parse all 10 cases successfully
- Extract structured data (profile, transactions, summary)
- Identify initial signals (both positive and negative)

### Planner Agent
- Route to appropriate specialist agents
- Generate relevant search queries
- Prioritize investigation areas

### Typology Matcher (Wikipedia + Google)
- Match Cases 03, 06, 08 to specific typologies
- Explain why Cases 01, 02, 05, 10 don't match typologies
- Provide nuanced assessment for Cases 04, 07, 09

### Pattern Analyzer (Wikipedia + Google)
- Identify red flags in all cases
- Distinguish true red flags from false positives
- Provide context for legitimate explanations

### Entity Research (Google Search)
- Verify NeuralSync Technologies (Case 05) - should find Sequoia funding
- Check Global Trade Solutions (Case 06) - should find no legitimate presence
- Search for adverse media on all individuals/companies
- Check sanctions lists (should find no hits for legitimate cases)

### Reasoning Agent
- Weigh evidence objectively
- Consider both incriminating and exculpatory factors
- Provide confidence scores reflecting evidence strength
- Avoid false positives on legitimate cases
- Avoid false negatives on fraud cases

### Report Agent
- Generate comprehensive assessments
- Include all source citations
- Provide actionable recommendations
- Format professionally for compliance review

---

## 🔍 Key Metrics to Track

1. **Accuracy**: Correct verdict for each case
2. **Confidence Calibration**: Scores match evidence strength
3. **False Positive Rate**: Don't flag Cases 01, 02, 05, 10 as fraud
4. **False Negative Rate**: Don't miss Cases 03, 06, 08 as fraud
5. **Grey Area Handling**: Appropriate uncertainty for Cases 04, 07, 09
6. **Source Quality**: Relevant citations from Wikipedia and Google
7. **Reasoning Quality**: Balanced consideration of all evidence
8. **Actionability**: Clear, specific recommendations

---

## 💡 Expected Challenges

- **Case 04**: High income inconsistency but no clear fraud pattern
- **Case 07**: Legitimate trading mixed with suspicious P2P activity
- **Case 09**: NFT market complexity and valuation subjectivity
- **Case 01**: International transfers might trigger false positive
- **Case 10**: Remittances to high-risk countries (El Salvador, Guatemala)

The system should handle these challenges with nuanced reasoning and appropriate confidence levels.

