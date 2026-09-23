#!/bin/bash
mkdir -p /opt/n8n
cd /opt/n8n

cat << 'EOF' > docker-compose.yml
version: "3.8"
services:
  n8n:
    image: docker.n8n.io/n8nio/n8n:latest
    container_name: n8n
    restart: always
    ports:
      - "127.0.0.1:5678:5678"
    environment:
      - N8N_HOST=localhost
      - N8N_PORT=5678
      - N8N_PROTOCOL=http
      - NODE_ENV=production
      - WEBHOOK_URL=http://localhost:5678/
      - GENERIC_TIMEZONE=Asia/Jakarta
    volumes:
      - n8n_data:/home/node/.n8n

volumes:
  n8n_data:
EOF

docker compose up -d
