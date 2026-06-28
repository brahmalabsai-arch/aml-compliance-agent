# Internal AML & Sanctions Compliance Policy
Institution: Meridian Pay Inc. (illustrative US-based payments institution)
Jurisdiction: United States (OFAC / FinCEN / Bank Secrecy Act regime)
Document ID: AML-POL-2026 | Version 4.2 | Owner: Financial Crime Compliance

> NOTE: This is a SYNTHETIC policy written for a portfolio demo. It is modeled on
> the real structure of US AML/KYC regulation (BSA, OFAC sanctions, SAR filing,
> FATF guidance) but is not the policy of any real institution.

## Section 1 — Purpose and Scope
This policy governs all outbound and cross-border payments processed by Meridian
Pay Inc., a US-regulated payments institution. It applies to every transaction
initiated on behalf of a customer, counterparty, or vendor, regardless of
channel or amount. As a US entity, the institution is bound by OFAC sanctions
and FinCEN reporting obligations under the Bank Secrecy Act.

## Section 2 — Transaction Thresholds
2.1 Any single transaction at or above USD 10,000 (or local-currency
equivalent) to a counterparty in a HIGH-RISK jurisdiction requires Enhanced Due
Diligence (EDD) before release.

2.2 Aggregated transactions to the same counterparty exceeding USD 10,000
within a rolling 24-hour window are treated as a single transaction for
threshold purposes (anti-structuring rule).

2.3 Transactions below USD 1,000 to non-high-risk jurisdictions may be
auto-approved provided no sanctions hit is present.

## Section 3 — Sanctions Screening
3.1 The institution must NEVER transact with any entity, individual, or vessel
that appears on an applicable sanctions list (OFAC SDN, EU Consolidated, UN, or
UK HMT). Any positive match results in an immediate BLOCK and a mandatory SAR
(Suspicious Activity Report) filing.

3.2 A "fuzzy" or partial name match (score below full confidence) must be
routed to manual REVIEW rather than auto-blocked, to allow for false-positive
clearance by an analyst.

3.3 Screening must be performed against live, current sanctions data at the
time of the transaction. Cached lists older than 24 hours are not acceptable.

## Section 4 — High-Risk Jurisdictions
4.1 The following are treated as HIGH-RISK jurisdictions for the purposes of
this policy: Iran, North Korea, Syria, Cuba, Crimea region, Myanmar, and any
jurisdiction on the FATF "Call for Action" list.

4.2 Payments to high-risk jurisdictions are never auto-approved and always
require, at minimum, EDD and senior analyst sign-off.

## Section 5 — Decision Outcomes
5.1 ALLOW — No sanctions hit, amount below EDD threshold, non-high-risk
jurisdiction.

5.2 REVIEW — Fuzzy sanctions match, OR amount at/above EDD threshold, OR
high-risk jurisdiction without a confirmed sanctions hit. Requires human analyst
action before release.

5.3 BLOCK — Confirmed sanctions match on counterparty or jurisdiction. Payment
is stopped and escalated to the Financial Crime team with a SAR filing.

## Section 6 — Record Keeping
6.1 Every screening decision, including the policy clauses applied and the live
data retrieved, must be logged and retained for a minimum of 5 years.
