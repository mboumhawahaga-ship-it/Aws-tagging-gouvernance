# Red Queen - AWS Tag Governance Platform

## Overview

Red Queen is a serverless cloud governance platform designed to automate AWS tagging compliance at scale.

The platform continuously detects non-compliant resources, automatically applies default tags, notifies responsible teams, and enforces remediation Service Level Agreements (SLAs).

If resources remain non-compliant beyond their remediation window, Red Queen automatically quarantines them to prevent unmanaged cloud consumption and improve cost accountability.

The platform enables organizations to establish proactive cloud governance without slowing down engineering teams.

---

## Business Problem

Cloud cost allocation, security governance, and operational ownership heavily depend on tagging.

In practice, engineering teams frequently deploy resources without the required metadata due to:

* Deployment speed pressures.
* Infrastructure automation gaps.
* Human error.
* Inconsistent governance processes.

Missing tags create several problems:

* Cloud costs cannot be attributed accurately.
* Ownership becomes unclear.
* Compliance requirements cannot be enforced.
* Unmanaged resources accumulate over time.

Red Queen automates the entire tagging governance lifecycle.

---

## Key Features

* Automatic resource tagging at creation time.
* Continuous compliance evaluation using AWS Config.
* Criticality classification based on workload type and business metadata.
* SLA-driven remediation workflows.
* Automated quarantine for unresolved violations.
* Multi-channel notifications (Email + Slack).
* Manual governance feedback API.
* Real-time governance dashboards.
* Dry-run mode for safe validation.
* End-to-end encryption using AWS KMS.

---

## Architecture

Governance workflow:

```
CloudTrail Resource Creation
                ↓
         EventBridge
                ↓
        Auto-Tagging Lambda
                ↓
          AWS Config
                ↓
    Compliance Evaluation
                ↓
      SLA-based Notifications
                ↓
      EventBridge Scheduler
                ↓
Automatic Remediation or Quarantine
```

The entire platform operates using a fully serverless architecture.

---

## AWS Services

* AWS Lambda
* Amazon EventBridge
* AWS Config
* AWS CloudTrail
* Amazon DynamoDB
* Amazon SNS
* Amazon API Gateway
* AWS KMS
* Amazon CloudWatch
* AWS IAM

---

## Governance Model

### Mandatory Tags

The platform enforces the following business metadata:

* Owner
* Squad
* CostCenter
* Environment

### Criticality Classification

Resources are classified automatically:

**Critical**

* RDS instances.
* Production EC2 instances.
* Resources tagged `CriticalWorkload=true`.

**Non-Critical**

* Development and non-production workloads.

### SLA Enforcement

| Resource Type | SLA |
|---|---|
| Critical workloads | 36 hours |
| Non-critical workloads | 7 days |

---

## Automated Remediation Workflow

1. Resource created.
2. Tags validated.
3. Missing tags automatically applied.
4. Non-compliant resources detected.
5. Teams notified.
6. SLA timer started.
7. Resource re-evaluated.
8. Automatic quarantine applied if still non-compliant.

---

## Lambda Functions

| Function | Trigger | Role |
|---|---|---|
| `auto-tagger` | EventBridge (CloudTrail creates) | Applies default tags on resource creation |
| `compliance-evaluator` | EventBridge (Config NON_COMPLIANT) + Scheduler | Evaluates, alerts, quarantines |
| `feedback-api` | API Gateway v2 | Manual approval and correction interface |

---

## FinOps Capabilities

| Capability | Status |
|---|---|
| Tag Compliance Automation | ✓ |
| Cost Attribution Enforcement | ✓ |
| Automated Remediation | ✓ |
| Governance SLA Management | ✓ |
| Quarantine Workflow | ✓ |
| Cost Visibility Dashboard | ✓ |
| Serverless Governance | ✓ |
| Budget Governance | Planned |

---

## Estimated Business Impact

Conservative estimates based on FinOps industry practices:

* Improve enterprise tag compliance rates from an estimated 50–70% to more than 90%.
* Increase cloud cost allocation coverage to above 90%.
* Reduce manual governance effort by an estimated 60–80%.
* Accelerate remediation of governance violations through automated workflows.
* Reduce unmanaged cloud resources and orphaned spend.

---

## Example Scenario

Organization size:

* 500 AWS resources.
* 10 engineering teams.

Typical situation without governance:

* 30–50% of resources partially or completely untagged.
* Multiple days required for remediation.

With Red Queen:

* Continuous compliance monitoring.
* Automated remediation.
* SLA enforcement.
* Full audit history for every governance event.

---

## Security Controls

### Encryption

* Customer-managed KMS key with automatic rotation.
* Encryption applied to DynamoDB, SNS and CloudWatch Logs.

### Identity & Access

* Dedicated IAM role per Lambda.
* Least-privilege permissions model.

### Input Validation

* Resource identifier sanitization.
* Log injection protection.
* SSRF protection for external webhooks.

### Safe Operations

* DRY_RUN mode preventing accidental modifications.
* Strict EventBridge routing preventing race conditions between auto-tagger and compliance-evaluator.

---

## DevOps & Quality

* Infrastructure as Code with Terraform (flat + modular architecture).
* Automated CI pipeline with GitHub Actions (flake8, terraform fmt, terraform validate).
* Unit tests with pytest.
* Local Grafana dashboards (CloudWatch datasource, Docker Compose).
* Modular Terraform architecture under `terraform/modules/`.

---

## Getting Started

```bash
# 1. Copy and configure variables
cp infra/terraform.tfvars.example infra/terraform.tfvars

# 2. Deploy (dry-run enabled by default)
cd infra
terraform init
terraform apply \
  -var="sns_email=your@email.com"

# 3. Start local Grafana dashboard
cd sensible
cp .env.example .env
# fill in AWS credentials and Grafana password
cd ..
docker-compose up -d
# Open http://localhost:3000
```

---

## Technical Highlights

* Event-driven serverless architecture.
* SLA-based automation workflows.
* Governance-as-Code principles.
* Automated compliance remediation.
* Serverless API layer.
* FinOps-driven governance model.
* Cloud-native observability.

---

## Future Improvements

* AWS Organizations multi-account support.
* Budget governance integration.
* Automated exception workflows.
* FinOps scorecards.
* Policy-as-Code integration.
* Service Catalog integration.

---

## License

MIT
