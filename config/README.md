# config/

Local configuration files — **never committed to Git**.

| File | Description | In Git? |
|------|-------------|---------|
| `.env` | Real credentials (AWS keys, passwords) | NO — gitignored |
| `.env.example` | Template with no sensitive values | YES |

## Setup

```bash
cp config/.env.example config/.env
# Fill in your values
```

> For production, use IAM Roles instead of static AWS credentials.
> See `docs/SECURITY.md` for details.
