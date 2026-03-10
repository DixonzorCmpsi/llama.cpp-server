# Startup Guide

This guide covers bringing the stack up from scratch and making your first successful chat request.

## 1. Prerequisites

Install and confirm:

- Docker Desktop
- Docker Compose support (`docker compose`)
- Python 3.x with `pip`
- Enough disk space for models (Q2_K ~3 GB, Q4_K_M ~4.5 GB, Q8 ~8 GB)
- Optional: NVIDIA GPU support for Docker if you want GPU inference

Check Docker:

```powershell
docker version
docker compose version
```

## 2. Auth Keys

Copy the example file and add your real keys:

```powershell
copy auth_keys.conf.example auth_keys.conf
```

Generate a key:

```powershell
python -c "import secrets; print('sk-' + secrets.token_hex(24))"
```

Edit `auth_keys.conf` and add one line per key:

```nginx
"Bearer sk-your-generated-key" 1;
```

---

## 3. Download a Model

Install the required Python package once:

```powershell
pip install huggingface_hub
```

Then download a model using the included script:

```powershell
python scripts/download_model.py "bartowski/Meta-Llama-3.1-8B-Instruct-GGUF"
```

The script downloads the Q4_K_M quantization by default into `.\model_cache`.

Other examples:

```powershell
# Pick a specific quantization
python scripts/download_model.py "bartowski/Meta-Llama-3.1-8B-Instruct-GGUF" "Meta-Llama-3.1-8B-Instruct-Q5_K_M.gguf"

# Custom cache directory
python scripts/download_model.py "bartowski/Meta-Llama-3.1-8B-Instruct-GGUF" -c C:\models
```

### Option B: Manual Download

Copy any `.gguf` file directly into `.\model_cache`, then create a preset file manually:

```yaml
model: /models/your-model-name.gguf
n_ctx: 8192
```

Save as `.\model_cache\your-model-name.yml` (same base name as the `.gguf`, container path `/models/`).

---

## 4. Start the Stack

From the repo root:

```powershell
docker compose up -d --build
```

This builds the `ai-server` image from source and starts the Nginx gateway on host port `80`.

---

## 5. Confirm Containers Are Up

```powershell
docker compose ps
```

Expected:

- `local-ai-api` — `Up`
- `local-ai-gateway` — `Up`

---

## 6. Verify the Model Is Registered

```powershell
curl.exe http://localhost/v1/models `
  -H "Authorization: Bearer <your-key>"
```

Expected response includes your model:

```json
{
  "data": [
    {
      "id": "Meta-Llama-3.1-8B-Instruct-Q4_K_M",
      "object": "model",
      "status": { "value": "unloaded" }
    }
  ],
  "object": "list"
}
```

If `data` is an empty array, the preset file is missing or incorrectly named.

---

## 7. Pre-Warm Models (Optional)

Models load lazily on first request. To pre-load all models into VRAM at once:

```powershell
python scripts/warmup.py
```

---

## 8. Send a Chat Request

```powershell
curl.exe http://localhost/v1/chat/completions `
  -H "Authorization: Bearer <your-key>" `
  -H "Content-Type: application/json" `
  -d "{\"model\":\"Meta-Llama-3.1-8B-Instruct-Q4_K_M\",\"messages\":[{\"role\":\"user\",\"content\":\"Hello, what can you do?\"}]}"
```

The first request will be slow (model loads on demand). Subsequent requests are faster.

---

## 9. Adding More Models

1. Download the model (preset is created automatically):
   ```powershell
   python scripts/download_model.py "bartowski/Qwen2.5-7B-Instruct-GGUF"
   ```

2. Restart the AI server (no rebuild needed):
   ```powershell
   docker compose restart ai-server
   ```

3. Verify it appears in `/v1/models`.

---

## 10. Useful Operations

| Action | Command |
|--------|---------|
| First start / rebuild | `docker compose up -d --build` |
| Restart AI server (new model) | `docker compose restart ai-server` |
| Restart gateway (auth key change) | `docker compose up -d api-gateway` |
| Pre-warm all models | `python scripts/warmup.py` |
| Stop everything | `docker compose down` |
| AI server logs | `docker compose logs --tail 100 ai-server` |
| Gateway logs | `docker compose logs --tail 100 api-gateway` |

---

## Troubleshooting

### `curl: (7) Failed to connect to localhost port 80`

The gateway is not listening. Check:

```powershell
docker compose ps
docker compose logs --tail 50 api-gateway
```

### `401 Unauthorized`

Your bearer token does not match `auth_keys.conf`. Check the key in your request matches exactly.

### `200 OK` but empty model list `{"data":[]}`

No `.yml` preset files found in `.\model_cache`. Ensure:

- The `.yml` file exists alongside the `.gguf`
- The `model:` path inside the YAML uses `/models/` (container path), not your Windows path
- After creating the file, run `docker compose restart ai-server`

### Model shows as `unloaded` in `/v1/models`

This is normal. Router mode loads models on first request, not at startup. Send a chat request or run `python scripts/warmup.py`.

### `no backends are loaded` in ai-server logs

The dynamic backend plugins (`libggml-cpu.so`, `libggml-cuda.so`) were not found at runtime. This is already fixed in the current [Dockerfile](../Dockerfile). If you see this after modifying it, ensure this step is present:

```dockerfile
RUN cp /usr/local/lib/libggml-cpu.so /usr/local/bin/ && \
    (cp /usr/local/lib/libggml-cuda.so /usr/local/bin/ 2>/dev/null || true)
```

Then rebuild: `docker compose up -d --build`

### nginx crashes with `could not build map_hash`

Increase `map_hash_bucket_size` in [nginx.conf](../nginx.conf) from `128` to `256`.

### GPU warnings: `no usable GPU found`

Check that:

1. The `deploy.resources.reservations.devices` block is present in [docker-compose.yml](../docker-compose.yml)
2. The NVIDIA Container Toolkit is installed:
   ```powershell
   docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi
   ```
3. The runtime image in [Dockerfile](../Dockerfile) is `nvidia/cuda:12.4.1-runtime-ubuntu22.04`

If GPU is configured correctly, startup logs will show:
```
ggml_cuda_init: found 1 CUDA devices ...
load_tensors: offloaded 33/33 layers to GPU
```

### Port `80` already in use

Change the port mapping in [docker-compose.yml](../docker-compose.yml):

```yaml
ports:
  - "8081:80"
```

Then use `http://localhost:8081`.

### `unable to get image` / Docker not running

Start Docker Desktop:
```powershell
Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"
```
Wait 10 seconds, then retry.

---

## File Reference

| File | Purpose |
|------|---------|
| [docker-compose.yml](../docker-compose.yml) | Stack definition |
| [nginx.conf](../nginx.conf) | Gateway auth and proxying |
| [Dockerfile](../Dockerfile) | AI server image build |
| [scripts/download_model.py](../scripts/download_model.py) | Download GGUF models from Hugging Face |
| [scripts/warmup.py](../scripts/warmup.py) | Pre-warm all models into VRAM |
| `model_cache/*.gguf` | Model weight files |
| `model_cache/*.yml` | Model preset files (required for router mode) |
