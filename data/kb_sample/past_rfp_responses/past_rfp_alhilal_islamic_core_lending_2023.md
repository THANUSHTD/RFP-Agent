---
id: KB-PAST-001
source_type: Past RFP Response
product: AzentioFinance
product_version: 3.0.0
product_tags: ["AzentioFinance", "Islamic Lending", "Core Banking", "Murabaha", "Ijarah"]
doc_date: 2023-11-05
last_verified: 2023-11
quality: High
is_outdated: false
is_sensitive: false
reuse_permitted: true
coverage: Fully Addressed
customer: Al-Hilal Bank Abu Dhabi (Synthetic)
rfp_reference: RFP-2023-ALHILAL-ISLAMIC [SAMPLE]
status: Awarded / Won
lead_se: Sarah Jenkins
---

# Past RFP Winning Response: Al-Hilal Bank – Islamic Core Lending

**RFP Reference:** RFP-2023-ALHILAL-ISLAMIC [SAMPLE]  
**Bidder:** Azentio Software  
**Status:** Awarded / Won  
**Customer:** Al-Hilal Bank Abu Dhabi (Synthetic Sample)  
**Lead SE:** Sarah Jenkins  
**Document Date:** 05 November 2023  
**Product:** AzentioFinance v3.0.0  

---

## Question 3.1 – Sharia Compliance and AAOIFI Certification

**Question:**  
Provide details on how your solution guarantees compliance with AAOIFI Shariah standards, particularly for Murabaha and Ijarah contracts.

**Response (Azentio):**  
AzentioFinance v3.0 has received explicit Sharia fatwas and verification confirming full adherence to AAOIFI Shariah Standard No. 8 (Murabaha to the Purchase Orderer) and Standard No. 9 (Ijarah).  

In the Murabaha module, the software strictly prevents the generation of the client sale offer until positive confirmation of the commodity purchase and title receipt from the supplier is registered in the audit ledger.  

Furthermore, late payment fees are never added to the bank’s profit ledger; the platform automatically transfers the donation portion to an isolated charity disbursement escrow, ensuring full Shariah compliance.

**Coverage:** Fully Addressed  
**Source Quality:** High (Winning response, verified at time of submission)

---

## Question 4.2 – Disaster Recovery, SLAs and System Availability

**Question:**  
State your High Availability (HA) architecture and Disaster Recovery (DR) metrics including RTO and RPO.

**Response (Azentio):**  
AzentioFinance v3.0 offers a 99.95% production availability SLA when deployed across dual active-passive availability zones.  

Our automated geo-replication guarantees a Recovery Point Objective (RPO) of 15 minutes or less, and a Recovery Time Objective (RTO) of under 2 hours.  

Automated DR failover drills can be executed without data loss.

**Coverage:** Fully Addressed  
**Source Quality:** High  

---

## Question 9.1 – Commercial Proposal and Pricing [CONFIDENTIAL]

**Question:**  
Submit your commercial software license fee and annual maintenance costs.

**Response (Azentio):**  
Azentio offered Al-Hilal Bank an enterprise tier license fee of $850,000 for up to 500,000 active financing accounts, with annual software maintenance and support at $150,000 per year. Additional consulting days were billed at $950/day.

**Coverage:** Information Required (Commercial – Sensitive)  
**Notes:**  
- This commercial information is highly sensitive.  
- In the RFP Agent it must be classified as **Information Required** / **Sensitive**.  
- Never auto-answer pricing or commercial terms. Flag for commercial owner.  
- Customer name and exact figures should be redacted if reused in other responses unless explicitly permitted.

---

### Usage Notes for RFP Agent

- This document can be reused for similar Islamic financing / Murabaha / Ijarah compliance questions.
- Always cite the source and date when generating an answer.
- For any pricing, SLA commitment or liability question, treat as sensitive and route to human review.
- Product version referenced is 3.0.0 (November 2023). Check for newer versions before presenting as current.