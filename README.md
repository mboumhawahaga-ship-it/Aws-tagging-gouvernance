# AWS Resource Guardian

> Safe and progressive cleanup of orphaned AWS resources.
> Freeze first. Notify. Resume automatically. Delete only as last resort.

**Never accidentally delete an important resource again.**

---

## The problem this solves

A developer creates an RDS database on a Friday night during an incident — no time for tags.
A naive cleanup tool deletes it at 2 AM. That's a production incident.

AWS Tag Policies and SCPs help at creation time, but they don't handle **resources that already exist**.
This tool does — safely.

---

## How it works at a glance

```
Every 2h
   │
   ▼
┌─────────────────────────────────────────────────────────────────┐
│  Scanner Lambda                                                  │
│  Scans EC2 · RDS · S3 · Lambda                                  │
│  Finds resources missing required tags                          │
└──────────────────────────────┬──────────────────────────────────┘
                               │  1 Step Function per resource
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│  Step Functions — 4-day escalation pipeline                     │
│                                                                  │
│  Day 0 ──► FREEZE + notify owner (Slack + Email)                │
│               │                                                  │
│            48h wait                                              │
│               │                                                  │
│  Day 2 ──► Check tags                                           │
│            ├── Fixed? ──► RESUME automatically ✅               │
│            └── Still missing? ──► Reminder notification         │
│                    │                                             │
│                 48h wait                                         │
│                    │                                             │
│  Day 4 ──► Check tags                                           │
│            ├── Fixed? ──► RESUME automatically ✅               │
│            └── Still missing? ──► DELETE (last resort) 🗑️       │
│                                                                  │
│  Error at any step? ──► NotifyFailure ──► human takes over      │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│  Metrics Lambda (every 6h)                                       │
│  Compliance rate · Cost per team · AutoShutdown savings         │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│  Grafana Dashboard                                               │
│  Real-time costs · Compliance gauge · Top spenders per squad    │
└─────────────────────────────────────────────────────────────────┘
```

---

## What happens to each resource type

| Resource | Day 0 — Freeze | If tags fixed | Day 4 — Last resort |
|----------|---------------|---------------|---------------------|
| **EC2** | `stop_instances` | `start_instances` ✅ | `terminate_instances` |
| **RDS** | Snapshot + `stop_db_instance` | `start_db_instance` ✅ | Final snapshot + `delete_db_instance` |
| **S3** | Block public access + enable versioning | — | **Never auto-deleted** (human decision required) |
| **Lambda** | `reserved_concurrency = 0` | Remove concurrency limit ✅ | `delete_function` |

> RDS always gets a safety snapshot before any deletion — data is never lost silently.

---

## Required tags

Every AWS resource must have these 5 tags. Terraform rejects deployment if any are missing.

| Tag | Format | Example |
|-----|--------|---------|
| `Owner` | email `@company.com` | `john.doe@company.com` |
| `Squad` | non-empty string | `backend`, `data`, `devops` |
| `CostCenter` | non-empty string | `CC-123` |
| `Environment` | `dev` / `staging` / `prod` | `prod` |
| `AutoShutdown` | `true` / `false` | `true` |

Auto-added: `ManagedBy: Terraform` · `CreatedAt: <stable timestamp>`

---

## Why not just use AWS Tag Policies + SCP?

| Capability | Tag Policies | SCP | AWS Resource Guardian |
|------------|-------------|-----|----------------------|
| Enforce tag format at creation | ✅ | ✅ | ✅ via Terraform validation |
| Handle **already existing** resources | ❌ | ❌ | ✅ Scanner Lambda |
| 4-day escalation (freeze → notify → delete) | ❌ | ❌ | ✅ Step Functions |
| RDS snapshot before any action | ❌ | ❌ | ✅ Executor Lambda |
| Slack + Email notifications | ❌ | ❌ | ✅ Controller Lambda |
| FinOps dashboard (cost per team) | ❌ | ❌ | ✅ Grafana + CloudWatch |
| Works **without AWS Organizations** | ✅ | ❌ | ✅ |

---

## Stack

| Component | Technology |
|-----------|-----------|
| Infrastructure | Terraform (modules: `tagged-resources`, `governance-pipeline`, `metrics-lambda`) |
| Escalation pipeline | AWS Step Functions + 3 Lambda functions (Python 3.12) |
| Observability | AWS Lambda Powertools — structured logs, X-Ray tracing, CloudWatch metrics |
| Notifications | SNS (email) + Slack webhook (stored in Secrets Manager) |
| FinOps metrics | CloudWatch custom metrics + Cost Explorer API |
| Dashboard | Grafana (CloudWatch datasource) |
| CI/CD | GitHub Actions — flake8, terraform fmt/validate, Infracost |

---

## Project structure

```
aws-resource-guardian/
├── lambda/
│   ├── scanner/        # Detects non-compliant resources, starts 1 Step Function per resource
│   ├── controller/     # Evaluate · notify (Slack + SNS) · check compliance
│   ├── executor/       # Freeze · resume · delete — DRY_RUN=true by default
│   └── metrics/        # FinOps metrics — compliance rate, cost per squad
├── terraform/
│   ├── modules/
│   │   ├── tagged-resources/     # Tag enforcement on EC2, RDS, S3, Lambda
│   │   ├── governance-pipeline/  # Scanner + Step Functions + Controller + Executor
│   │   ├── step-function/        # State machine ASL definition
│   │   ├── eventbridge/          # Cron trigger every 2h
│   │   └── metrics-lambda/       # CloudWatch metrics + Cost Explorer
│   └── environments/
│       ├── dev/                  # Dev environment
│       └── prod/                 # Production (dry_run=true until validated)
├── grafana/
│   ├── dashboards/               # Dashboard JSON (CloudWatch datasource)
│   └── provisioning/             # Auto-configured datasource
├── scripts/
│   ├── publish_mock_metrics.py   # Feed the dashboard with demo data
│   ├── validate-tags.sh          # Manual tag check on existing resources
│   └── setup-cost-explorer.ps1   # Activate Cost Allocation Tags on AWS
└── docs/
    ├── GUIDE_DEMARRAGE.md
    ├── SECURITY.md
    └── JOURNAL_DE_BORD.md        # Engineering log — errors and solutions
```

---

## Quick start

```bash
# 1. Clone
git clone https://github.com/mboumhawahaga-ship-it/Aws-tagging-gouvernance.git
cd aws-tagging-gouvernance

# 2. Configure AWS credentials
cp config/.env.example config/.env
# Edit config/.env with your AWS credentials and notification email

# 3. Deploy (dev environment — dry_run=true, no real actions taken)
cd terraform/environments/dev
terraform init
terraform plan
terraform apply

# 4. Run the Grafana dashboard locally
cd ../../..
docker-compose up -d
python scripts/publish_mock_metrics.py
# Open http://localhost:3000
```

---

## Safety by design

| Design choice | Why |
|---------------|-----|
| `DRY_RUN=true` by default | Zero risk on first rollout — observe the full pipeline before enabling real actions |
| 48h grace periods × 2 | Realistic time for a developer to add missing tags |
| S3 is never auto-deleted | A bucket can hold data from multiple teams — deletion requires a human decision |
| RDS always snapshots before delete | Data is never lost silently, even as a last resort |
| Slack webhook in Secrets Manager | Webhook URL never exposed in env vars or Terraform state |
| Retry (3× exponential backoff) on every state | Transient AWS errors don't abort the pipeline |
| `NotifyFailure` catch-all | If anything breaks, a human is alerted immediately |

---

## Tests

```bash
# Lambda unit tests (moto — AWS simulation, zero cost)
cd lambda/cleanup
pip install pytest moto boto3
pytest test_handler.py -v
# → 12/12 PASSED

# Terraform validation
cd terraform/environments/dev
terraform validate

# Manual tag check on existing resources
bash scripts/validate-tags.sh
```

---

## License

MIT
