Simple commands to help me if i forget:

To build docker image:
```bash
docker build -f docker/Dockerfile -t neuber-correction-server:latest .
``` 



To run container:
```bash
docker run -d --name neuber-correction-server -p 8000:8000 neuber-correction-server:latest
```

To run with docker-compose:
```bash
cd docker && docker-compose up -d --build
```
or simple:
```bash
docker run -p 80:80 neuber-correction-server:latest
```

# View logs
```bash
docker logs -f neuber-correction-server
```

# Stop container
```bash
docker stop neuber-correction-server
```

# Restart container
```bash
docker restart neuber-correction-server
```

# Remove container
```bash
docker rm neuber-correction-server
```

# Check if container is running
```bash
docker ps | grep neuber-correction-server
```

# Access the application
# Web Interface: http://localhost:80
# API Docs: http://localhost:80/docs