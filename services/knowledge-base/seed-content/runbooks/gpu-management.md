# Runbook: GPU Management

## Overview
Procedures for managing GPU resources for AI/ML workloads in the Omni Quantum Elite platform.

**Audience**: Platform engineers, ML engineers
**Estimated time**: Varies
**Risk level**: Medium

---

## GPU-Dependent Services

| Service | Container | GPU Usage | Priority |
|---------|-----------|-----------|----------|
| Ollama | omni-ollama | Model inference (CodeLlama, DeepSeek, etc.) | High |
| AI Coder Alpha (OpenHands) | omni-openhands | Optional (for local model inference) | Medium |
| AI Coder Beta (SWE-Agent) | omni-swe-agent | Optional (for local model inference) | Medium |

---

## GPU Detection and Verification

### Check Available GPUs

```bash
# Host-level GPU detection
nvidia-smi

# Check Docker GPU access
docker run --rm --gpus all nvidia/cuda:12.2.0-base-ubuntu22.04 nvidia-smi

# Check GPU allocation to containers
docker inspect omni-ollama | jq '.[0].HostConfig.DeviceRequests'
```

### Expected Output
```
+-----------------------------------------------------------------------------+
| NVIDIA-SMI 535.xx    Driver Version: 535.xx    CUDA Version: 12.2          |
|-------------------------------+----------------------+----------------------+
| GPU  Name        Persistence-M| Bus-Id        Disp.A | Volatile Uncorr. ECC |
| Fan  Temp  Perf  Pwr:Usage/Cap|         Memory-Usage | GPU-Util  Compute M. |
|===============================+======================+======================|
|   0  NVIDIA RTX ...      On   | 00000000:01:00.0 Off |                  N/A |
| 30%   45C    P8    15W / 350W |   2048MiB / 24576MiB |      5%      Default |
+-------------------------------+----------------------+----------------------+
```

---

## Docker Compose GPU Configuration

### Allocating GPU to Ollama

```yaml
services:
  omni-ollama:
    image: ollama/ollama:latest
    container_name: omni-ollama
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
        limits:
          memory: 32g
    environment:
      - NVIDIA_VISIBLE_DEVICES=all
      - OLLAMA_NUM_PARALLEL=2
      - OLLAMA_MAX_LOADED_MODELS=3
    volumes:
      - ollama-data:/root/.ollama
```

### Sharing GPU Between Services

If multiple services need GPU access, configure time-sharing via NVIDIA MPS or sequential access:

```yaml
# Option 1: All services share all GPUs
deploy:
  resources:
    reservations:
      devices:
        - driver: nvidia
          count: all
          capabilities: [gpu]

# Option 2: Specific GPU assignment (multi-GPU hosts)
deploy:
  resources:
    reservations:
      devices:
        - driver: nvidia
          device_ids: ["0"]
          capabilities: [gpu]
```

---

## Model Management (Ollama)

### List Loaded Models

```bash
curl http://omni-ollama:11434/api/tags
```

### Pull a New Model

```bash
curl -X POST http://omni-ollama:11434/api/pull \
  -d '{"name": "codellama:13b"}'
```

### Check Running Models

```bash
curl http://omni-ollama:11434/api/ps
```

### Unload a Model (Free VRAM)

```bash
curl -X POST http://omni-ollama:11434/api/generate \
  -d '{"model": "codellama:13b", "keep_alive": 0}'
```

### Model VRAM Requirements

| Model | Parameters | VRAM (fp16) | VRAM (q4_0) |
|-------|-----------|-------------|-------------|
| codellama:7b | 7B | 14 GB | 4.2 GB |
| codellama:13b | 13B | 26 GB | 7.4 GB |
| deepseek-coder:6.7b | 6.7B | 13 GB | 3.8 GB |
| starcoder2:7b | 7B | 14 GB | 4.0 GB |
| llama3.1:8b | 8B | 16 GB | 4.7 GB |
| nomic-embed-text | 137M | 0.5 GB | 0.3 GB |

### Recommended Configuration (24GB GPU)

Load simultaneously (within VRAM budget):
- `codellama:13b` (q4_0) — 7.4 GB
- `nomic-embed-text` — 0.3 GB
- Reserve ~4 GB for inference workspace
- Total: ~12 GB used, ~12 GB headroom

```bash
# Set Ollama to keep max 2 models loaded
# docker-compose.yml environment:
OLLAMA_MAX_LOADED_MODELS=2
OLLAMA_NUM_PARALLEL=2
```

---

## Monitoring GPU Usage

### Real-Time GPU Monitoring

```bash
# Watch GPU utilization (updates every 1 second)
watch -n 1 nvidia-smi

# Detailed process list
nvidia-smi pmon -i 0 -s um -d 1
```

### Prometheus GPU Metrics

If `nvidia-dcgm-exporter` is configured:

```promql
# GPU utilization percentage
DCGM_FI_DEV_GPU_UTIL{gpu="0"}

# GPU memory used (bytes)
DCGM_FI_DEV_FB_USED{gpu="0"}

# GPU temperature
DCGM_FI_DEV_GPU_TEMP{gpu="0"}

# GPU power usage
DCGM_FI_DEV_POWER_USAGE{gpu="0"}
```

### Grafana Dashboard Queries

```promql
# GPU Memory Utilization %
(DCGM_FI_DEV_FB_USED / DCGM_FI_DEV_FB_FREE) * 100

# Model Inference Latency (from Ollama metrics)
rate(ollama_request_duration_seconds_sum[5m]) / rate(ollama_request_duration_seconds_count[5m])
```

---

## Troubleshooting

### GPU Not Detected by Docker

```bash
# 1. Check NVIDIA driver is installed
nvidia-smi

# 2. Check nvidia-container-toolkit is installed
dpkg -l | grep nvidia-container-toolkit

# 3. If not installed:
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
sudo apt-get update && sudo apt-get install -y nvidia-container-toolkit
sudo systemctl restart docker

# 4. Verify Docker GPU access
docker run --rm --gpus all nvidia/cuda:12.2.0-base-ubuntu22.04 nvidia-smi
```

### Out of VRAM

```bash
# 1. Check what's using VRAM
nvidia-smi

# 2. Unload unused models from Ollama
curl -X POST http://omni-ollama:11434/api/generate \
  -d '{"model": "unused-model", "keep_alive": 0}'

# 3. Use quantized models (q4_0 uses ~4x less VRAM than fp16)
curl -X POST http://omni-ollama:11434/api/pull \
  -d '{"name": "codellama:13b-instruct-q4_0"}'

# 4. Reduce parallel inference
# Set OLLAMA_NUM_PARALLEL=1 in docker-compose.yml and restart
```

### Slow Inference

```bash
# 1. Check GPU utilization — if low, model might be running on CPU
nvidia-smi

# 2. Verify model is loaded in GPU memory
curl http://omni-ollama:11434/api/ps

# 3. Check for thermal throttling
nvidia-smi -q -d PERFORMANCE

# 4. Ensure no other process is using the GPU
nvidia-smi pmon -i 0

# 5. Consider switching to a smaller/quantized model
```

### Container Fails to Start with GPU

```bash
# Check Docker runtime configuration
cat /etc/docker/daemon.json
# Should contain:
# { "runtimes": { "nvidia": { "path": "nvidia-container-runtime" } } }

# Check container GPU request
docker inspect omni-ollama | jq '.[0].HostConfig.DeviceRequests'

# Check NVIDIA container runtime logs
journalctl -u docker | grep nvidia | tail -20
```

---

## GPU Maintenance

### Driver Updates

```bash
# 1. Stop all GPU-dependent containers
docker compose stop omni-ollama omni-openhands omni-swe-agent

# 2. Update driver (Ubuntu)
sudo apt-get update
sudo apt-get install nvidia-driver-535  # or latest stable

# 3. Reboot
sudo reboot

# 4. Verify
nvidia-smi

# 5. Restart containers
docker compose start omni-ollama omni-openhands omni-swe-agent
```

### Periodic Health Check

Run weekly:
```bash
#!/usr/bin/env bash
echo "=== GPU Health Check $(date) ==="
nvidia-smi --query-gpu=name,temperature.gpu,utilization.gpu,memory.used,memory.total,power.draw --format=csv
echo ""
echo "=== Ollama Models ==="
curl -s http://omni-ollama:11434/api/tags | jq '.models[] | {name, size, modified_at}'
echo ""
echo "=== Running Models ==="
curl -s http://omni-ollama:11434/api/ps | jq '.models[] | {name, size, expires_at}'
```
