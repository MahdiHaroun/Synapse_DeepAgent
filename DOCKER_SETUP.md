# Docker Commands for Synapse DeepAgent

## Setup
1. Copy the example env file and fill in your actual values:
   ```bash
   cp .env.example .env
   # Edit .env with your actual credentials
   ```

2. Build the Docker image:
   ```bash
   docker build -t synapse-deepagent -f DockerFile .
   ```

3. Run the container with environment file:
   ```bash
   docker run -d \
     --name synapse-app \
     --env-file .env \
     -p 8070:8070 \
     -p 3000:3000 \
     -p 3010:3010 \
     -p 3020:3020 \
     -p 3030:3030 \
     -p 3040:3040 \
     -p 3050:3050 \
     -p 3060:3060 \
     synapse-deepagent
   ```

## Services Running Inside Container

The Docker container automatically starts:
- **Main API**: http://localhost:8070
- **MCP Servers**:
  - Gmail MCP: http://localhost:3050
  - AWS S3 MCP: http://localhost:3000
  - Calendar MCP: http://localhost:3030
  - Analysis MCP: http://localhost:3040
  - Auth MCP: http://localhost:3060
  - Web Search MCP: http://localhost:3020
  - RAG Service MCP: http://localhost:3010

## Useful Commands

### View logs
```bash
docker logs synapse-app
docker logs -f synapse-app  # Follow logs
```

### Stop container
```bash
docker stop synapse-app
```

### Start container
```bash
docker start synapse-app
```

### Remove container
```bash
docker rm synapse-app
```

### Rebuild and restart
```bash
docker stop synapse-app
docker rm synapse-app
docker build -t synapse-deepagent -f DockerFile .
docker run -d \
  --name synapse-app \
  --env-file .env \
  -p 8070:8070 \
  -p 3000-3060:3000-3060 \
  synapse-deepagent
```

### Access container shell
```bash
docker exec -it synapse-app /bin/bash
```

### Check MCP servers status
```bash
# Check if all processes are running
docker exec synapse-app ps aux | grep python
```
