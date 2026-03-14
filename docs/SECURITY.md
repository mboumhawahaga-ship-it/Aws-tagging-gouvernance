# 🔒 AWS Security Guide – Best Practices

This document describes all the security measures implemented in the project and the recommended best practices.

---

## ✅ Security Measures Implemented

### 🔐 1. Secrets and Password Management

#### AWS Secrets Manager (RDS)

**✅ Implemented:**

- Automatic generation of random passwords (32 characters)
- Secure storage in AWS Secrets Manager
- Encryption at rest with AWS KMS
- Optional rotation (to be configured)

**Configuration:**

```hcl
module "my_database" {
  source = "../../modules/tagged-resources"

  resource_type = "rds"
  resource_name = "my-db"

  # ✅ Automatic generation enabled by default
  rds_generate_random_password = true
}
```

**Secure retrieval:**

```bash
# Get the secret name
terraform output rds_secret_name

# Retrieve the credentials
aws secretsmanager get-secret-value \
  --secret-id dev-my-db-rds-credentials \
  --query SecretString --output text | jq .
```

---

### 🔒 2. Encryption

#### RDS – Encryption at Rest

**✅ Enabled by default:**

```hcl
rds_storage_encrypted = true  # Default
```

- Uses AWS KMS to encrypt data
- Automatically encrypts backups
- Encrypts snapshots

#### S3 – Server-Side Encryption

**✅ Enabled automatically:**

- Algorithm: AES-256
- Applied to all objects
- No extra configuration needed

#### Secrets Manager

**✅ Encrypted automatically:**

- Encryption with AWS KMS
- Default KMS key or custom key

---

### 🌐 3. Network Access

#### RDS – No Public Access

**✅ Disabled by default:**

```hcl
rds_publicly_accessible = false  # Default
```

**Recommendations:**

- ✅ Use VPCs and private subnets
- ✅ Configure restrictive Security Groups
- ✅ Use AWS PrivateLink or VPN for access

#### S3 – Block Public Access

**⚠️ To be configured manually:**

```hcl
resource "aws_s3_bucket_public_access_block" "this" {
  bucket = aws_s3_bucket.this.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
```

---

### 💾 4. Backups and Recovery

#### RDS – Automatic Backups

**✅ Configured:**

```hcl
# In production: minimum 7 days
backup_retention_period = var.environment == "prod" ? 7 : 1

# Backup window (UTC)
backup_window = "03:00-04:00"
```

**Final Snapshot:**

- ✅ Automatically created in production before deletion
- ❌ Disabled in dev/staging (to save costs)

#### S3 – Versioning

**✅ Enabled by default:**

```hcl
s3_versioning_enabled = true
```

---

### 🔄 5. High Availability

#### RDS – Multi-AZ

**✅ Automatically enabled in production:**

```hcl
multi_az = var.environment == "prod" ? true : false
```

**Benefits:**

- Synchronous replication in another AZ
- Automatic failover in case of failure
- Maintenance with minimal downtime

---

### 🛡️ 6. Deletion Protection

#### RDS – Deletion Protection

**✅ Automatically enabled in production:**

```hcl
deletion_protection = var.environment == "prod" ? true : false
```

**Behavior:**

- Production: impossible to delete without explicitly disabling protection
- Dev/Staging: deletion allowed (to save costs)

---

### 📊 7. Monitoring and Audit

#### CloudWatch Logs

**✅ Enabled automatically:**

**PostgreSQL:**

- PostgreSQL logs
- Upgrade logs

**MySQL:**

- Error logs
- General logs
- Slow query logs

#### Required Tags

**✅ Enforced on all resources:**

```hcl
Owner        = "email@company.com"   # Accountability
Squad        = "Team-Name"           # Traceability
CostCenter   = "CC-XXX"              # Billing
Environment  = "dev/staging/prod"    # Environment
AutoShutdown = "true/false"          # Cost optimization
```

---

## 🚨 Identified Risks and Mitigations

### ❌ Risk 1: Terraform State Contains Secrets

**Problem:**

The `terraform.tfstate` file can contain:

- RDS passwords
- Resource ARNs
- Sensitive configurations

**✅ Implemented Mitigation:**

```hcl
# .gitignore
*.tfstate
*.tfstate.*
*.tfvars
```

**✅ Recommended Solution – S3 Backend:**

```hcl
# terraform/backend.tf
terraform {
  backend "s3" {
    bucket         = "my-tfstate-bucket"
    key            = "aws-tagging-governance/terraform.tfstate"
    region         = "eu-west-1"
    encrypt        = true                    # Encryption
    dynamodb_table = "terraform-state-lock"  # Locking
    kms_key_id     = "arn:aws:kms:..."       # Custom KMS key (optional)
  }
}
```

**Bucket configuration:**

```bash
# 1. Create the bucket
aws s3api create-bucket \
  --bucket my-tfstate-bucket \
  --region eu-west-1 \
  --create-bucket-configuration LocationConstraint=eu-west-1

# 2. Enable versioning
aws s3api put-bucket-versioning \
  --bucket my-tfstate-bucket \
  --versioning-configuration Status=Enabled

# 3. Enable encryption
aws s3api put-bucket-encryption \
  --bucket my-tfstate-bucket \
  --server-side-encryption-configuration '{
    "Rules": [{
      "ApplyServerSideEncryptionByDefault": {
        "SSEAlgorithm": "AES256"
      }
    }]
  }'

# 4. Block public access
aws s3api put-public-access-block \
  --bucket my-tfstate-bucket \
  --public-access-block-configuration \
    BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true

# 5. Create the DynamoDB table for state locking
aws dynamodb create-table \
  --table-name terraform-state-lock \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST
```

---

### ❌ Risk 2: Sensitive Variables in `.tfvars` Files

**Problem:**

`.tfvars` files can contain secrets.

**✅ Implemented Mitigation:**

```bash
# .gitignore
*.tfvars
!*.tfvars.example  # Examples are OK
```

**✅ Best Practice:**

```bash
# Use environment variables
export TF_VAR_rds_master_password="..."

# Or use AWS Secrets Manager in Terraform
data "aws_secretsmanager_secret_version" "var" {
  secret_id = "terraform/variables"
}
```

---

### ❌ Risk 3: Unauthorized Access to Secrets

**Problem:**

Anyone with broad AWS access might read secrets.

**✅ Recommended Solution – Restrictive IAM Policy:**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": "arn:aws:secretsmanager:*:*:secret:*-rds-credentials-*",
      "Condition": {
        "StringEquals": {
          "aws:RequestedRegion": "eu-west-1"
        }
      }
    }
  ]
}
```

---

## 📋 Security Checklist

### Before Deploying to Production

- [ ] **Terraform S3 backend configured** with encryption
- [ ] **IAM Roles** configured with the principle of least privilege
- [ ] **VPC and Security Groups** created and configured
- [ ] **RDS**:
  - [ ] `rds_storage_encrypted = true`
  - [ ] `rds_publicly_accessible = false`
  - [ ] `rds_multi_az = true`
  - [ ] `rds_backup_retention_period >= 7`
  - [ ] `rds_deletion_protection = true`
- [ ] **S3**:
  - [ ] Versioning enabled
  - [ ] Public access block configured
  - [ ] Lifecycle policies configured
- [ ] **Secrets Manager**:
  - [ ] Secret rotation configured (optional)
  - [ ] Restrictive IAM policies
- [ ] **CloudWatch**:
  - [ ] Alarms configured
  - [ ] Logs enabled and retention configured
- [ ] **AWS Config**:
  - [ ] Compliance rules enabled
  - [ ] Audit of required tags
- [ ] **Documentation**:
  - [ ] Incident recovery runbook
  - [ ] Emergency contacts documented

---

## 🔄 Maintenance and Secret Rotation

### Manual Rotation of RDS Passwords

```bash
# 1. Generate a new password
NEW_PASSWORD=$(openssl rand -base64 32)

# 2. Update the secret
aws secretsmanager update-secret \
  --secret-id dev-my-db-rds-credentials \
  --secret-string "{\"password\":\"$NEW_PASSWORD\"}"

# 3. Update RDS
aws rds modify-db-instance \
  --db-instance-identifier dev-my-db \
  --master-user-password "$NEW_PASSWORD" \
  --apply-immediately
```

### Automatic Rotation (Recommended)

```hcl
resource "aws_secretsmanager_secret" "rds_credentials" {
  # ...

  rotation_rules {
    automatically_after_days = 30
  }
}

resource "aws_secretsmanager_secret_rotation" "rds" {
  secret_id           = aws_secretsmanager_secret.rds_credentials.id
  rotation_lambda_arn = aws_lambda_function.rotate_secret.arn

  rotation_rules {
    automatically_after_days = 30
  }
}
```

---

## 📞 Support and Resources

### AWS Documentation

- [AWS Secrets Manager Best Practices](https://docs.aws.amazon.com/secretsmanager/latest/userguide/best-practices.html)
- [RDS Security Best Practices](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/CHAP_BestPractices.Security.html)
- [S3 Security Best Practices](https://docs.aws.amazon.com/AmazonS3/latest/userguide/security-best-practices.html)
- [Terraform Security Best Practices](https://developer.hashicorp.com/terraform/tutorials/cloud/terraform-security)

### Audit Tools

- [AWS Trusted Advisor](https://aws.amazon.com/premiumsupport/technology/trusted-advisor/)
- [AWS Security Hub](https://aws.amazon.com/security-hub/)
- [Checkov](https://www.checkov.io/) – Terraform security scanner
- [tfsec](https://github.com/aquasecurity/tfsec) – Terraform security scanner

### Contact

- 📧 Email: cloud-governance@company.com
- 💬 Slack: `#aws-security`
- 🚨 Incidents: `#aws-incidents`

---

**Last updated:** 2026-02-09  
**Version:** 1.0  
**Author:** Cloud Governance Team
