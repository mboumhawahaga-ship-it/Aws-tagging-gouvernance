# AWS Tagging Governance

[![Quality & Security Check](https://github.com/mboumhawahaga-ship-it/Aws-tagging-gouvernance/actions/workflows/ci-quality.yml/badge.svg)](https://github.com/mboumhawahaga-ship-it/Aws-tagging-gouvernance/actions/workflows/ci-quality.yml)

> **Business problem**: according to the Flexera State of the Cloud Report 2024, around **32% of global cloud spend is wasted** on under‑used, orphaned or untracked resources — largely because of missing tags to identify owners and associated costs. FinOps case studies (Duckbill Group, CloudQuery) show that organizations without enforced tagging policies typically have **~30% “unallocated” spend**. After implementing strict tagging + automation, this ratio often drops to **below 5%**.

This project implements **end‑to‑end, automated tagging governance** on AWS to address this problem: IaC enforcement, auto‑cleanup of non‑compliant resources, FinOps metrics collection and cost visualization per team.

---

## What this project solves in practice

| Problem without tagging | Implemented solution |
|---|---|
| Costs can’t be allocated per team | `Squad` + `CostCenter` tags enforced at creation time |
| Zombie resources nobody can identify | Cleanup Lambda + 24h grace period + SNS report |
| No visibility on waste | Grafana dashboard: compliance, costs per squad, AutoShutdown savings |
| Dev environments running all night | `AutoShutdown: true` tag → estimated savings (~$48/month on a dev env) |
| RDS secrets stored in plain text in state | AWS Secrets Manager + automatic rotation |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        GitHub Actions CI                        │
│           flake8 · terraform fmt · terraform validate           │
└─────────────────────────┬───────────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────────┐
│                   Terraform (IaC)                               │
│   modules/tagged-resources · cleanup-lambda · metrics-lambda    │
└──────┬──────────────────┬──────────────────┬────────────────────┘
       │                  │                  │
  ┌────▼────┐        ┌────▼────┐       ┌────▼──────┐
  │   EC2   │        │   RDS   │       │  S3 · λ   │
  │  tags   │        │  tags + │       │   tags    │
  │enforced │        │Secrets  │       │ enforced  │
  └─────────┘        │Manager  │       └───────────┘
                     └─────────┘
                          │
         ┌────────────────┼─────────────────┐
         │                │                 │
  ┌──────▼──────┐  ┌──────▼──────┐  ┌──────▼──────┐
  │   Lambda    │  │   Lambda    │  │ EventBridge │
  │   cleanup   │  │   metrics   │  │  cron 2h/6h │
  │ DRY_RUN=true│  │every 6h    │  └─────────────┘
  │ grace: 24h  │  └──────┬──────┘
  └──────┬──────┘         │
         │          ┌─────▼──────────────────┐
         │          │      CloudWatch         │
         │          │ TagCompliance · Costs   │
         │          └─────┬──────────────────┘
         │                │
  ┌──────▼────────────────▼──────┐
  │         Grafana              │
  │  compliance · costs/squad    │
  │  AutoShutdown savings        │
  └──────────────────────────────┘
```

---

## Mandatory tags

All AWS resources **must** have these tags — Terraform rejects creation if one is missing or empty.

| Tag | Validation | Example | FinOps impact |
|-----|------------|---------|---------------|
| `Owner` | email regex `@company.com` | `john.doe@company.com` | Clear accountability |
| `Squad` | non‑empty | `Data`, `Backend`, `DevOps` | Team‑level chargeback |
| `CostCenter` | non‑empty | `CC-123` | Financial showback |
| `AutoShutdown` | boolean | `true` / `false` | ~50% savings on dev envs |
| `Environment` | `dev`/`staging`/`prod` | `dev` | Cost separation per environment |

**Automatic tags**: `ManagedBy: Terraform` · `CreatedAt: <stable timestamp>`

---

## FinOps features

### 1. Strict enforcement at creation (Terraform)
- Regex validation on `Owner` (email `@company.com`)
- Deployment is rejected if any tag is missing or the environment is invalid
- Encryption on by default for RDS (KMS) and S3 (AES‑256)
- RDS password randomly generated (32 chars) → stored in Secrets Manager

### 2. Auto‑cleanup of non‑compliant resources (Lambda)
- Scans EC2, RDS, S3, Lambda every night at 2 AM (EventBridge)
- **24h grace period** before actually acting (protects against false positives)
- **`DRY_RUN=true` mode by default** — simulation with no real deletions
- Detailed report sent via SNS after each run

### 3. Real‑time FinOps metrics (Lambda + CloudWatch)
- Global tag compliance rate (namespace `TagCompliance`)
- Spend per `Squad` and `CostCenter` via Cost Explorer API
- Estimated savings from the `AutoShutdown` tag
- Top 10 most expensive AWS services
- Automatic execution every 6 hours

### 4. Grafana dashboard
- Total monthly cost for the current month
- Tag compliance gauge (target: > 95%)
- Cost breakdown by Squad (donut chart)
- 30‑day cost evolution (time series)
- Non‑compliant resources with colored background (red if > 5)

docs-en-rewrite
--
```bash
# 1. Cloner le projet
git clone git clone https://github.com/mboumhawahaga-ship-it/Aws-tagging-gouvernance.git
 
 main

## Results on demo environment

These numbers are generated by `scripts/publish_mock_metrics.py` on a simulated environment representative of a 3–5‑developer team.

| Metric | Value |
|--------|-------|
| Resources scanned | 24 |
| Initial compliance rate (before project) | ~30% (industry estimate) |
| Target compliance rate | > 95% |
| Total monthly cost (dev env) | ~$971 |
| Estimated savings via AutoShutdown | **~$48/month** |
| “Unallocated” costs after tagging | < 5% |

> **Industry reference**: Flexera 2024 — 32% of cloud spend wasted on untracked resources. Mature organizations reach 85–95% “taggable” spend. Source: [Flexera State of the Cloud 2024](https://info.flexera.com/CM-RESEARCH-State-of-the-Cloud-Report)

---

## Financial impact / ROI (estimates)

The goal of this project is **not** to promise exact savings, but to provide a realistic mechanism to reduce the kind of waste highlighted by Flexera and FinOps case studies.

- Flexera 2024 reports **~32% of cloud spend is wasted** on under‑used or untracked resources.
- In many organizations, **~30% of spend is “unallocated”** (no clear owner or cost center).
- With strict tagging + automation, that “unallocated” share often drops to **< 5%**.

In the **demo dev environment** simulated here (~$971/month):

- If we apply the Flexera 32% waste ratio as an upper bound, that would mean **up to ~$310/month of potential waste**.
- The current AutoShutdown logic alone estimates **~$48/month** in savings for a small 3–5‑developer team — roughly **5% of the total dev bill**.
- As environments grow (more squads, more projects), the same mechanisms (tag enforcement, nightly cleanup, AutoShutdown) tend to scale almost linearly with usage, while operational overhead stays low (Lambdas + Terraform).

These numbers are **illustrative only** and based on:

- a typical development account with a handful of EC2/RDS/S3/Lambda resources,
- conservative assumptions on instance types and schedules,
- public industry benchmarks (Flexera, FinOps case studies).

In a real organization, the exact ROI will depend on:

- how aggressively you enable AutoShutdown and cleanup outside of production,
- how disciplined teams are at tagging new resources,
- how much existing “zombie” infrastructure is present when you roll this out.

The project is designed so that:

- you can start in **safe mode** (`DRY_RUN=true`, 24h grace period, dev‑only),
- measure impact via CloudWatch/Grafana,
- then gradually extend to more environments as you gain confidence.

---

## 🚨 Production Limitations

**~10% of AWS resources do not support tags**:
- IAM Groups/Roles → use Organizations Tag Policies
- CloudFormation Stacks → naming conventions + child resource tags
- AWS Organizations → store metadata in Parameter Store

**This project covers 85–90% of total AWS costs** (EC2/RDS/S3/Lambda represent 80%+ of the spend).  
To reach 100% → combine with AWS Config Rules + Tag Policies.


---

## Project structure

```
aws-tagging-governance/
├── .github/workflows/
│   └── ci-quality.yml              # CI: Flake8 + terraform fmt/validate
├── terraform/
│   ├── modules/
│   │   ├── tagged-resources/       # Core module — tag enforcement
│   │   ├── cleanup-lambda/         # Auto‑cleanup Lambda module
│   │   └── metrics-lambda/         # CloudWatch metrics Lambda module
│   └── environments/
│       └── dev/                    # Demo environment
├── lambda/
│   ├── cleanup/                    # Auto‑cleanup + unit tests (moto)
│   └── metrics/                    # Metrics collection + Cost Explorer
├── grafana/
│   ├── dashboards/                 # Dashboard JSON (CloudWatch datasource)
│   └── provisioning/               # Auto‑configured CloudWatch datasource
├── scripts/
│   ├── publish_mock_metrics.py     # Feeds the dashboard for demos
│   ├── validate-tags.sh            # Manual tag validation
│   └── setup-cost-explorer.ps1     # Cost Allocation Tags activation
└── docs/
    ├── GETTING_STARTED.md   # Getting started guide
    ├── SECURITY.md          # Security best practices
    └── ENGINEERING_LOG.md   # Engineering / incident log
```

---

## Quick start

```bash
# 1. Clone
git clone https://github.com/mboumhawahaga-ship-it/Aws-tagging-gouvernance.git

# 2. Configure AWS credentials
cp sensible/.env.example sensible/.env
# Edit sensible/.env with your credentials

# 3. Deploy the infrastructure
cd terraform/environments/dev
terraform init
terraform plan
terraform apply

# 4. Launch the Grafana dashboard (local demo)
cd ../../..
docker-compose up -d
python scripts/publish_mock_metrics.py  # Feed with realistic demo data
# → http://localhost:3000
```

---

## Tests

```bash
# Lambda unit tests (moto — AWS simulation, zero cost)
cd lambda/cleanup
pip install pytest moto boto3
pytest test_handler.py -v

# Terraform validation
terraform validate

# Tag validation on existing resources
bash scripts/validate-tags.sh
```

---

## Notable technical choices

| Decision | Rationale |
|----------|-----------|
| `DRY_RUN=true` by default | Avoids any accidental deletion during first rollout |
| 24h grace period | Protects legitimate resources created recently |
| `time_static` for `CreatedAt` | Stable tag across re‑creations (no noisy Terraform diffs) |
| `arm64` for Lambdas | ~20% cheaper than x86 on AWS Graviton |
| S3 Intelligent‑Tiering | Automatic archiving after 90 days → lower storage costs |
| Secrets Manager for RDS | Zero secrets in Terraform state or environment variables |

---

## Next steps

- [ ] Terraform remote state (encrypted S3 backend + DynamoDB lock)
- [ ] Infracost in CI (cost estimation on each PR)
- [ ] AWS Config rules for continuous compliance audit
- [ ] ECS/EKS support in the `tagged-resources` module
- [ ] Multi‑environment setup (staging, prod) with Terraform workspaces

---

## License

MIT License
