# Quickstart Guide: Regal POS Backend

**Date**: 2026-01-28
**Feature**: Regal POS Backend Clone

## Prerequisites

- Docker and Docker Compose v3.8+
- Python 3.10+ (for local development without containers)
- Git

## Local Development Setup

### 1. Clone and Navigate
```bash
git clone <repository-url>
cd <repository-directory>
```

### 2. Environment Variables
Create a `.env` file in the root directory:
```env
# Database
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/regal_pos_dev
NEON_DATABASE_URL=postgresql+asyncpg://username:password@ep-xxx.us-east-1.aws.neon.tech/regal_pos_prod

# JWT Secrets
ACCESS_TOKEN_SECRET_KEY=your-access-token-secret-key-here
REFRESH_TOKEN_SECRET_KEY=your-refresh-token-secret-key-here

# Redis
REDIS_URL=redis://localhost:6379

# Application
APP_ENV=development
DEBUG=true
```

### 3. Start Development Environment
```bash
# Build and start all services
docker-compose up --build

# Or run in detached mode
docker-compose up --build -d
```

### 4. Initialize Database
```bash
# Run migrations
docker-compose exec api alembic upgrade head

# Or create initial migration if needed
docker-compose exec api alembic revision --autogenerate -m "Initial migration"
docker-compose exec api alembic upgrade head
```

## Development Workflow

### Hot Reload Development
The development environment uses bind mounts to enable hot reloading:
- Code changes in the `./api` directory are automatically reflected in the container
- The FastAPI server restarts automatically when code changes are detected
- No need to rebuild the container for code changes

### Running Tests
```bash
# Run unit tests
docker-compose exec api pytest tests/unit/

# Run integration tests
docker-compose exec api pytest tests/integration/

# Run all tests
docker-compose exec api pytest
```

### Database Migrations
```bash
# Create a new migration
docker-compose exec api alembic revision --autogenerate -m "Migration description"

# Apply migrations
docker-compose exec api alembic upgrade head

# Check current migration status
docker-compose exec api alembic current
```

## Service Architecture

### Available Services
- `api`: FastAPI application (port 8000)
- `postgres`: PostgreSQL database (port 5432)
- `redis`: Redis cache/broker (port 6379)
- `nginx`: Optional reverse proxy (port 80)

### API Endpoints
- Main API: http://localhost:8000
- API Documentation: http://localhost:8000/docs
- Alternative API Documentation: http://localhost:8000/redoc

## Common Commands

### Development
```bash
# View service logs
docker-compose logs -f api

# Execute commands in the API container
docker-compose exec api bash

# Install new Python packages
docker-compose exec api pip install package-name
docker-compose exec api pip freeze > requirements.txt
```

### Database Management
```bash
# Connect to database
docker-compose exec postgres psql -U postgres -d regal_pos_dev

# Backup database
docker-compose exec postgres pg_dump -U postgres regal_pos_dev > backup.sql

# Restore database
cat backup.sql | docker-compose exec -T postgres psql -U postgres regal_pos_dev
```

## Troubleshooting

### Common Issues
1. **Permission errors on macOS**: Add `:delegated` to bind mounts in docker-compose.yml
2. **Database connection errors**: Ensure PostgreSQL service is running and credentials are correct
3. **Port conflicts**: Modify port mappings in docker-compose.yml if ports are in use

### Reset Development Environment
```bash
# Stop all services
docker-compose down

# Remove volumes (WARNING: This will delete all data)
docker-compose down -v

# Restart environment
docker-compose up --build
```

## Production Notes

### Neon PostgreSQL Configuration
For production deployment with Neon:
- Use connection pooling recommendations from Neon
- Implement proper SSL settings
- Monitor connection limits
- Set up proper backup and retention policies

### Security Considerations
- Use strong, unique secret keys for JWT tokens
- Enable HTTPS in production
- Implement rate limiting
- Regular security audits of dependencies