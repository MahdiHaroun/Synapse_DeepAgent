# Docker Compose Setup for Synapse DeepAgent

This guide explains how to run the entire Synapse DeepAgent system using Docker Compose.

## Prerequisites

- Docker Engine 20.10+
- Docker Compose V2+
- AWS CLI configured with credentials in `~/.aws/` (for AWS services)

## Quick Start

### 1. Setup Environment Variables

```bash
# Copy the example env file
cp .env.example .env

# Edit .env with your actual credentials
nano .env  # or use your preferred editor
```

Make sure to set all required values:
- Database credentials
- MongoDB URI (use `mongodb://mongodb:27017` for docker-compose)
- API keys (GROQ, RESEND, TAVILY)
- Google OAuth credentials

**Note:** AWS credentials are automatically mounted from `~/.aws/` on your host machine. Make sure you have run `aws configure` before starting containers.

### 2. Build and Start All Services

```bash
# Build and start all services in detached mode
docker-compose up -d --build

# View logs for all services
docker-compose logs -f

# View logs for specific service
docker-compose logs -f main-api
docker-compose logs -f mcp-gmail
```

### 3. Verify Services Are Running

```bash
# Check status of all containers
docker-compose ps

# Test main API
curl http://localhost:8070/

# Test MCP servers
curl http://localhost:3050/  # Gmail
curl http://localhost:3000/  # S3
curl http://localhost:3030/  # Calendar
curl http://localhost:3040/  # Analysis
curl http://localhost:3060/  # Auth
curl http://localhost:3020/  # Web Search
curl http://localhost:3010/  # RAG
```

## Services Overview

| Service | Container Name | Port | Description |
|---------|---------------|------|-------------|
| postgres | synapse-postgres | 5432 | PostgreSQL database |
| mongodb | synapse-mongodb | 27017 | MongoDB database |
| main-api | synapse-main-api | 8070 | Main FastAPI application |
| mcp-gmail | synapse-mcp-gmail | 3050 | Gmail MCP server |
| mcp-s3 | synapse-mcp-s3 | 3000 | AWS S3 MCP server |
| mcp-calendar | synapse-mcp-calendar | 3030 | Google Calendar MCP server |
| mcp-analysis | synapse-mcp-analysis | 3040 | Analysis Tools MCP server |
| mcp-auth | synapse-mcp-auth | 3060 | Auth MCP server |
| mcp-web | synapse-mcp-web | 3020 | Web Search MCP server |
| mcp-rag | synapse-mcp-rag | 3010 | RAG Service MCP server |

## Shared Volume

All services share a common volume `synapse-shared` mounted at `/shared` for:
- Inter-service file sharing
- Temporary file storage
- Data exchange between MCP servers

## Common Commands

### Start Services
```bash
# Start all services
docker-compose up -d

# Start specific service
docker-compose up -d main-api
```

### Stop Services
```bash
# Stop all services
docker-compose down

# Stop and remove volumes (WARNING: deletes data)
docker-compose down -v
```

### View Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f mcp-gmail

# Last 100 lines
docker-compose logs --tail=100
```

### Restart Services
```bash
# Restart all
docker-compose restart

# Restart specific service
docker-compose restart main-api
```

### Rebuild Services
```bash
# Rebuild all services
docker-compose up -d --build

# Rebuild specific service
docker-compose up -d --build main-api
```

### Execute Commands in Container
```bash
# Access main API container shell
docker-compose exec main-api /bin/bash

# Access MongoDB CLI
docker-compose exec mongodb mongosh

# Access PostgreSQL CLI
docker-compose exec postgres psql -U postgres -d synapse_db
```

### Scale Services (if needed)
```bash
# Run multiple instances of a service
docker-compose up -d --scale mcp-web=3
```

## Troubleshooting

### Service Won't Start
```bash
# Check logs
docker-compose logs service-name

# Check if port is already in use
netstat -tulpn | grep :8070
```

### Database Connection Issues
- Verify `DATABASE_HOSTNAME=postgres` in .env
- Verify `MONGODB_URI=mongodb://mongodb:27017` in .env
- Services use container names for DNS resolution

### Reset Everything
```bash
# Stop and remove all containers, networks, volumes
docker-compose down -v

# Remove images
docker-compose down --rmi all

# Start fresh
docker-compose up -d --build
```

## Production Considerations

1. **Security**:
   - Change all default passwords
   - Use secrets management instead of .env for sensitive data
   - Enable SSL/TLS for databases

2. **Performance**:
   - Increase database resources in docker-compose.yml
   - Add resource limits to prevent containers from consuming too much

3. **Monitoring**:
   - Add health checks
   - Integrate with monitoring tools (Prometheus, Grafana)

4. **Backup**:
   - Regularly backup volumes:
     ```bash
     docker run --rm -v synapse-postgres-data:/data -v $(pwd):/backup alpine tar czf /backup/postgres-backup.tar.gz /data
     ```

## Network Architecture

All services communicate through the `synapse-network` bridge network:
- Containers can reach each other by service name
- Main API connects to `postgres:5432` and `mongodb:27017`
- MCP servers are accessible from host via mapped ports
