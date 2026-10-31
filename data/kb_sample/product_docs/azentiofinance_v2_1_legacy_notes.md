---
source_type: product_doc
product: AzentioFinance
product_version: 2.1.0
doc_date: 2021-06-10
reuse_permitted: true
---

# AzentioFinance v2.1 Architecture and Operational Guide [SAMPLE]
**Notice: Superseded by AzentioFinance v3.0 [SAMPLE]**

## 1. Monolithic Architecture Overview
AzentioFinance v2.1 was designed as an on-premise monolithic Java enterprise application deployed on Oracle WebLogic or IBM WebSphere application servers with Oracle Database 12c. Microservices and containerization were not supported in version 2.1.

## 2. Murabaha Manual Broker Settlement
In version 2.1, commodity broker confirmations for Tawarruq trades required manual upload of CSV transaction files. Automated real-time REST API integration with Bursa Suq Al-Sila was not available and was introduced in version 3.0.

## 3. SLA and Disaster Recovery in v2.1
- High Availability: 99.9% uptime SLA.
- Recovery Point Objective (RPO): RPO = 1 hour (batch replication).
- Recovery Time Objective (RTO): RTO = 4 hours.
- Note: Version 3.0 improves this to 99.95% uptime, RPO <= 15 minutes, and RTO <= 2 hours.

## 4. Database & Deployment Limits
Version 2.1 does not support native multi-tenant database partitioning. Each financial institution required dedicated physical VM clusters. Cloud deployment was limited to raw IaaS virtual machines.
