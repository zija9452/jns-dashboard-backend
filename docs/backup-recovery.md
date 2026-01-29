# Backup and Recovery Procedures for Regal POS Backend

## Overview
This document outlines the backup and recovery procedures for the Regal POS Backend system. These procedures ensure data integrity and availability in case of system failures or disasters.

## Backup Strategy

### Database Backups
- **Frequency**: Daily automated backups at 2 AM UTC
- **Retention**: 30 days for daily backups, weekly backups retained for 6 months
- **Location**: Encrypted S3 bucket with cross-region replication
- **Verification**: Automated verification of backup integrity

### Application Backups
- **Configuration**: Version-controlled in Git with protected branches
- **Dependencies**: Lock files (requirements.txt, poetry.lock) maintained
- **Infrastructure**: Terraform state files backed up to S3 with versioning

## Backup Procedures

### Automated Database Backup Script
```bash
#!/bin/bash
# Daily database backup script

BACKUP_DIR="/backups/postgres"
DATE=$(date +%Y%m%d_%H%M%S)
DB_NAME="regalpos"
DB_HOST="localhost"
DB_USER="postgres"

# Create backup
pg_dump -h $DB_HOST -U $DB_USER -d $DB_NAME | gzip > $BACKUP_DIR/${DB_NAME}_${DATE}.sql.gz

# Verify backup
gunzip -t $BACKUP_DIR/${DB_NAME}_${DATE}.sql.gz

# Upload to S3
aws s3 cp $BACKUP_DIR/${DB_NAME}_${DATE}.sql.gz s3://regal-pos-backups/daily/

# Cleanup local files older than 7 days
find $BACKUP_DIR -name "*.sql.gz" -mtime +7 -delete
```

### Redis Backup
- Redis persistence configured with RDB snapshots every 5 minutes
- AOF (Append Only File) enabled for durability
- Daily copy of Redis data to S3

## Recovery Procedures

### Database Recovery
1. **Identify Recovery Point**: Determine the appropriate backup timestamp
2. **Download Backup**: Retrieve backup file from S3
3. **Prepare Database**:
   ```bash
   # Stop application services
   sudo systemctl stop regal-pos-app

   # Drop and recreate database (if needed)
   dropdb regalpos
   createdb regalpos
   ```
4. **Restore Data**:
   ```bash
   gunzip -c backup_file.sql.gz | psql -d regalpos
   ```
5. **Verify Integrity**: Run data validation checks
6. **Restart Services**: Bring application back online

### Application Recovery
1. **Infrastructure Recovery**: Use Terraform to rebuild infrastructure
2. **Configuration Recovery**: Restore from Git version control
3. **Dependency Restoration**: Use lock files to install exact versions
4. **Data Restoration**: Follow database recovery procedure

## Disaster Recovery Plan

### RTO (Recovery Time Objective): 4 hours
### RPO (Recovery Point Objective): 1 hour

### Steps:
1. **Assessment** (0-30 min): Evaluate the scope of the disaster
2. **Notification** (0-15 min): Inform stakeholders and incident response team
3. **Recovery Actions** (30 min - 3 hours):
   - Activate backup systems
   - Restore data from latest backup
   - Validate system functionality
4. **Verification** (30 min): Ensure all systems are operational
5. **Communication** (15 min): Notify users of restored service

## Testing Procedures

### Monthly Backup Restoration Tests
- Select random backup files
- Perform restoration to test environment
- Validate data integrity
- Document any issues and update procedures

### Quarterly Full Disaster Recovery Tests
- Simulate complete system failure
- Execute full recovery procedure
- Measure RTO and RPO compliance
- Update procedures based on lessons learned

## Responsibilities

- **System Administrator**: Execute backup procedures, monitor backup status
- **Database Administrator**: Manage database backups, perform restoration
- **DevOps Engineer**: Maintain backup automation, update procedures
- **Security Team**: Verify encryption and access controls

## Monitoring and Alerts

- Backup completion status monitored via CloudWatch/Sentry
- Failed backup alerts sent to operations team
- Storage capacity alerts to prevent backup failures
- Verification failure alerts for corrupted backups

## Security Considerations

- All backups encrypted at rest using AES-256
- Access to backup storage limited to authorized personnel
- Backup transmission encrypted using TLS
- Regular rotation of encryption keys
- Audit trails for all backup and recovery operations

## Compliance

- GDPR compliance for personal data in backups
- SOX compliance for financial data
- PCI DSS compliance for payment data (if applicable)
- Regular compliance audits of backup procedures

## Appendices

### Appendix A: Emergency Contacts
- Operations Team: ops@company.com
- Database Team: dba@company.com
- Security Team: security@company.com

### Appendix B: Backup Schedule
- Daily: 2:00 AM UTC
- Weekly: Sunday 1:00 AM UTC (full backup)
- Monthly: First Sunday of month (archival backup)