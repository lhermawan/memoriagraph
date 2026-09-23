#!/bin/bash
cat << 'EOF' > /etc/systemd/system/ollama.service.d/override.conf
[Service]
Environment="OLLAMA_HOST=0.0.0.0"
EOF
systemctl daemon-reload
systemctl restart ollama
ss -tulnp | grep 11434
