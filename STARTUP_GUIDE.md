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

## 2. Download a Model

Install the required Python package once:

```powershell
pip install huggingface_hub
```

Then download a model using the included script:

```powershell
python download_model.py "TheBloke/Mistral-7B-Instruct-v0.2-GGUF"
```

The script downloads the first available `.gguf` from the repo into `.\model_cache`.

Other examples:

```powershell
# Different repo
python download_model.py "TheBloke/neural-chat-7B-v3-3-GGUF"

# Custom cache directory
python download_model.py "TheBloke/Mistral-7B-Instruct-v0.2-GGUF" -c C:\models
```

### Option B: Manual Download

Copy any `.gguf` file directly into `.\model_cache`.

---

## 3. Preset File (Automatic)

`llama-server` requires a `.yml` preset file alongside each `.gguf`. The download script creates this automatically — no manual steps needed.

After running the download script, `.\model_cache` will contain:

```
model_cache/
  mistral-7b-instruct-v0.2.Q2_K.gguf
  mistral-7b-instruct-v0.2.Q2_K.yml    <- auto-created by download script
```

The model `id` for API calls is the preset filename without `.yml`, e.g. `mistral-7b-instruct-v0.2.Q2_K`.

### Manual download (Option B)

If you copied a `.gguf` manually instead of using the script, create the preset yourself:

```yaml
model: /models/your-model-name.gguf
n_ctx: 8192
```

Save it as `.\model_cache\your-model-name.yml` (same base name as the `.gguf`, container path `/models/`).

---

## 4. Review Auth Keys

Open [nginx.conf](./nginx.conf) and update the allowed bearer tokens if needed.

Current keys:

```nginx
map $http_authorization $is_authorized {
    default 0;
    "Bearer sk-my-super-secret-on-prem-key" 1;
    "Bearer sk-another-client-key"          1;
}
```

---

## 5. Start the Stack

From the repo root:

```powershell
docker compose up -d --build
```

This builds the `ai-server` image from source and starts the Nginx gateway on host port `80`.

---

## 6. Confirm Containers Are Up

```powershell
docker compose ps
```

Expected:

- `local-ai-api` — `Up`
- `local-ai-gateway` — `Up`

---

## 7. Verify the Model Is Registered

```powershell
curl.exe http://localhost/v1/models `
  -H "Authorization: Bearer sk-my-super-secret-on-prem-key"
```

Expected response includes your model:

```json
{
  "data": [
    {
      "id": "mistral-7b-instruct-v0.2.Q2_K",
      "object": "model",
      "status": { "value": "unloaded", ... }
    }
  ],
  "object": "list"
}
```

If `data` is an empty array, the preset file is missing or incorrectly named. See Troubleshooting below.

---

## 8. Send a Chat Request

```powershell
curl.exe http://localhost/v1/chat/completions `
  -H "Authorization: Bearer sk-my-super-secret-on-prem-key" `
  -H "Content-Type: application/json" `
  -d "{\"model\":\"mistral-7b-instruct-v0.2.Q2_K\",\"messages\":[{\"role\":\"user\",\"content\":\"Hello, what can you do?\"}]}"
```

The first request will be slow (model loads on demand). Subsequent requests are faster.

The `model` field must exactly match the preset filename without `.yml`.

---

## 9. Adding More Models

1. Download the model (preset is created automatically):
   ```powershell
   python download_model.py "TheBloke/Mixtral-8x7B-Instruct-v0.1-GGUF"
   ```

2. Restart the AI server (no rebuild needed):
   ```powershell
   docker compose restart ai-server
   ```

3. Verify it appears in `/v1/models`.

---

## 10. Useful Operations

Rebuild after Dockerfile or config changes:

```powershell
docker compose up -d --build
```

Restart only the AI server (after adding/changing model presets):

```powershell
docker compose restart ai-server
```

Restart only the gateway (after changing nginx.conf):

```powershell
docker compose restart api-gateway
```

Stop everything:

```powershell
docker compose down
```

Check logs:

```powershell
docker compose logs --tail 100 ai-server
docker compose logs --tail 100 api-gateway
```

---

## Troubleshooting

### `curl: (7) Failed to connect to localhost port 80`

The gateway is not listening. Check:

```powershell
docker compose ps
docker compose logs --tail 50 api-gateway
```

### `401 Unauthorized`

Your bearer token does not match [nginx.conf](./nginx.conf).

### `200 OK` but empty model list `{"data":[]}`

No `.yml` preset files found in `.\model_cache`. Ensure:

- The `.yml` file exists alongside the `.gguf`
- The `model:` path inside the YAML uses `/models/` (container path), not your Windows path
- After creating the file, run `docker compose restart ai-server`

### Model shows as `unloaded` in `/v1/models`

This is normal. Router mode loads models on first request, not at startup. Send a chat request and it will load automatically.

### `no backends are loaded` in ai-server logs / model fails to load

The dynamic backend plugins (`libggml-cpu.so`, `libggml-cuda.so`) were not found by `llama-server` at runtime. This is already fixed in the current [Dockerfile](./Dockerfile) — the plugins are copied into `/usr/local/bin/` alongside the binary, which is where `llama-server` searches for them.

If you see this after modifying the Dockerfile, ensure this step is present:

```dockerfile
RUN cp /usr/local/lib/libggml-cpu.so /usr/local/bin/ && \
    (cp /usr/local/lib/libggml-cuda.so /usr/local/bin/ 2>/dev/null || true)
```

Then rebuild: `docker compose up -d --build`

### nginx crashes with `could not build map_hash`

Your API key string is too long for the default nginx map hash bucket size. The [nginx.conf](./nginx.conf) already includes `map_hash_bucket_size 128;` to handle this. If you add very long keys in the future and see this error again, increase the value to `256`.

### GPU warnings: `no usable GPU found`

Check that:

1. The `deploy.resources.reservations.devices` block is present in [docker-compose.yml](./docker-compose.yml) — this is what passes `--gpus all` to the container.
2. The NVIDIA Container Toolkit is installed and Docker can see the GPU:
   ```powershell
   docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi
   ```
3. The runtime image in [Dockerfile](./Dockerfile) is `nvidia/cuda:12.4.1-runtime-ubuntu22.04` (not `base`) — the `runtime` tier includes `libcublas.so.12` which the CUDA backend requires.

If the GPU is properly configured, startup logs will show:
```
ggml_cuda_init: found 1 CUDA devices ...
load_backend: loaded CUDA backend from /usr/local/bin/libggml-cuda.so
```
And on first model load:
```
load_tensors: offloaded 33/33 layers to GPU
```

### Port `80` already in use

Change the port mapping in [docker-compose.yml](./docker-compose.yml):

```yaml
ports:
  - "8081:80"
```

Then use `http://localhost:8081`.

### `unable to get image` or `dockerDesktopLinuxEngine: The system cannot find the file specified`

Docker Desktop is not running.

1. Start it:
   ```powershell
   Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"
   ```
2. Wait 5-10 seconds, then verify:
   ```powershell
   docker version
   ```
3. Retry:
   ```powershell
   docker compose up -d --build
   ```

Enable "Start Docker Desktop when you log in" in Docker Desktop settings to avoid this.

---

## File Reference

| File | Purpose |
|------|---------|
| [docker-compose.yml](./docker-compose.yml) | Stack definition |
| [nginx.conf](./nginx.conf) | Gateway auth and proxying |
| [Dockerfile](./Dockerfile) | AI server image build |
| [download_model.py](./download_model.py) | Download GGUF models from Hugging Face |
| `model_cache/*.gguf` | Model weight files |
| `model_cache/*.yml` | Model preset files (required for router mode) |
