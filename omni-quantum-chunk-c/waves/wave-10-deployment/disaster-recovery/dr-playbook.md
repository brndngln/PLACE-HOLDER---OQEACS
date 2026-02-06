# Disaster Recovery Playbook
## OMNI QUANTUM ELITE v3.0

**RTO:** 4 hours | **RPO:** 1 hour

## Critical Data
- PostgreSQL: Hourly backups, 30 day retention
- Qdrant: Daily backups, 14 day retention
- Vault: Hourly backups, 7 day retention

## Recovery Procedures

### Database Restore
```bash
docker stop omni-postgres
pg_restore -d financial_fortress /backups/latest.dump
docker start omni-postgres
```

### Full Infrastructure Recovery
```bash
git clone <repo> /opt/omni-quantum
./scripts/bootstrap.sh --restore
./scripts/restore-databases.sh
./scripts/verify-health.sh
```

## Contacts
- Primary On-Call: Brendan
