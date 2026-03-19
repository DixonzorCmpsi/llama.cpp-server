# On-Prem AI Server

A self-hosted, OpenAI-compatible inference API built on [llama.cpp](https://github.com/ggml-org/llama.cpp), secured behind an Nginx API-key gateway, running GGUF models on GPU (CPU fallback automatic).

---

## Project Structure

```
onPrem/
├── Dockerfile               # AI server image (CUDA + CPU fallback)
├── docker-compose.yml       # Stack definition
├── nginx.conf               # Gateway auth and proxying
├── .env                     # Stack secrets (CF tunnel token) — gitignored
├── .env.example             # Template for .env
├── auth_keys.conf           # Bearer tokens — gitignored, never committed
├── auth_keys.conf.example   # Template for auth_keys.conf
│
├── docs/
│   ├── API.md               # Full API reference + integration examples
│   └── STARTUP_GUIDE.md     # First-run checklist and troubleshooting
│
├── scripts/
│   ├── download_model.py    # Download GGUF models from Hugging Face
│   └── warmup.py            # Pre-warm all models into VRAM
│
├── chat_cli/
│   ├── chat.py              # Interactive terminal chat client
│   ├── requirements.txt     # Python dependencies
│   └── .env                 # CLI connection config — gitignored
│
└── model_cache/
    ├── *.gguf               # Model weight files — gitignored
    └── *.yml                # Model preset files
```

---

## Architecture

```
Internet → https://ai.deetalk.win → [Cloudflare Edge] → [cloudflared tunnel]
                                                               ↓
Client (local) → http://localhost → [Nginx gateway:80] → [llama-server:8080]
                                     (API key auth)        (GPU/CPU inference)
```

| Container | Image | Port | Purpose |
|-----------|-------|------|---------|
| `local-ai-gateway` | `nginx:alpine` | `80` (host) | Auth + reverse proxy |
| `local-ai-api` | Built from `Dockerfile` | internal `8080` | llama.cpp inference |
| `local-ai-tunnel` | `cloudflare/cloudflared` | none | Outbound tunnel to Cloudflare |

---

## Quick Start

### 1. Set up auth keys

```powershell
copy auth_keys.conf.example auth_keys.conf
# Edit auth_keys.conf and add a real key — generate one with:
python -c "import secrets; print('sk-' + secrets.token_hex(24))"
```

### 2. Set up the Cloudflare tunnel (optional, for public access)

```powershell
copy .env.example .env
# Edit .env and add your tunnel token from the Cloudflare Zero Trust dashboard
```

### 3. Download a model

```powershell
pip install huggingface_hub
python scripts/download_model.py "bartowski/Meta-Llama-3.1-8B-Instruct-GGUF"
```

### 4. Start the stack

```powershell
docker compose up -d --build
```

### 5. Verify

```powershell
# Local
curl.exe http://localhost/v1/models -H "Authorization: Bearer <your-key>"

# Public (if tunnel is configured)
curl.exe https://ai.deetalk.win/v1/models -H "Authorization: Bearer <your-key>"
```

### 6. Chat

```powershell
curl.exe http://localhost/v1/chat/completions `
  -H "Authorization: Bearer <your-key>" `
  -H "Content-Type: application/json" `
  -d "{\"model\":\"cognitivecomputations_Dolphin3.0-R1-Mistral-24B-Q3_K_M\",\"messages\":[{\"role\":\"user\",\"content\":\"Hello\"}]}"
```

### 7. Interactive CLI Chat

For a permanent client setup, use the included interactive CLI chat. You can specify the model in a `.env` file so you don't have to keep typing it.

```powershell
cd chat_cli
copy .env.example .env
```

Edit the `chat_cli/.env` file to add your key and this model:

```ini
API_BASE_URL=http://localhost/v1
API_KEY=sk-your-real-key-here
MODEL=cognitivecomputations_Dolphin3.0-R1-Mistral-24B-Q3_K_M
```

Then run the chat application:

```powershell
pip install -r requirements.txt
python chat.py
```

---

## How Models Work

`llama-server` runs in **router mode** (`--models-dir`). Each model needs two files in `./model_cache`:

```
model_cache/
  your-model.gguf    ← weights
  your-model.yml     ← preset (auto-created by download_model.py)
```

Preset file format:

```yaml
model: /models/your-model.gguf
n_ctx: 8192
```

The model `id` for API calls is the preset filename **without** `.yml`.

---

## Model Catalog

Download any model with:

```powershell
python scripts/download_model.py "<HuggingFace Repo ID>"
```

Defaults to Q4_K_M. To pick a specific quantization pass the filename as a second argument.

### Currently Installed (RTX 3060, 12 GB VRAM)

| Model ID | Size | Best For |
|----------|------|----------|
| `mistral-7b-instruct-v0.2.Q2_K` | 2.9 GB | Fast general chat, low VRAM |
| `Qwen2.5-Coder-7B-Instruct-Q4_K_M` | 4.4 GB | Code generation, debugging |
| `DeepSeek-R1-Distill-Llama-8B-Q4_K_M` | 4.6 GB | Reasoning, step-by-step thinking |
| `cognitivecomputations_Dolphin3.0-R1-Mistral-24B-Q3_K_M` | ~10.7 GB | General purpose, agentic, uncensored |

> **VRAM note:** Dolphin 24B uses ~10.7 GB — load it alone. The 7–8B models can coexist (up to `--models-max 3` active simultaneously).

---

### General Purpose / Chat

| Model | Repo ID | Size (Q4_K_M) | VRAM (Q4_K_M) |
|-------|---------|--------------|---------------|
| Llama 3.1 8B Instruct | `bartowski/Meta-Llama-3.1-8B-Instruct-GGUF` | ~4.9 GB | ~6 GB |
| Llama 3.2 3B Instruct | `bartowski/Llama-3.2-3B-Instruct-GGUF` | ~2.0 GB | ~3 GB |
| Llama 3.2 1B Instruct | `bartowski/Llama-3.2-1B-Instruct-GGUF` | ~0.8 GB | ~2 GB |
| Llama 3.3 70B Instruct | `bartowski/Llama-3.3-70B-Instruct-GGUF` | ~43 GB | ~48 GB |
| Mistral 7B Instruct v0.3 | `bartowski/Mistral-7B-Instruct-v0.3-GGUF` | ~4.4 GB | ~6 GB |
| Mistral Nemo 12B Instruct | `bartowski/Mistral-Nemo-Instruct-2407-GGUF` | ~7.7 GB | ~10 GB |
| Mixtral 8x7B Instruct | `TheBloke/Mixtral-8x7B-Instruct-v0.1-GGUF` | ~26 GB | ~30 GB |
| Qwen 2.5 7B Instruct | `bartowski/Qwen2.5-7B-Instruct-GGUF` | ~4.7 GB | ~6 GB |
| Qwen 2.5 14B Instruct | `bartowski/Qwen2.5-14B-Instruct-GGUF` | ~9.0 GB | ~11 GB |
| Qwen 2.5 32B Instruct | `bartowski/Qwen2.5-32B-Instruct-GGUF` | ~20 GB | ~24 GB |
| Gemma 2 2B Instruct | `bartowski/gemma-2-2b-it-GGUF` | ~1.6 GB | ~3 GB |
| Gemma 2 9B Instruct | `bartowski/gemma-2-9b-it-GGUF` | ~5.4 GB | ~7 GB |
| Phi-3.5 Mini Instruct | `bartowski/Phi-3.5-mini-instruct-GGUF` | ~2.2 GB | ~4 GB |
| Phi-4 14B | `bartowski/phi-4-GGUF` | ~8.5 GB | ~11 GB |
| Neural Chat 7B | `TheBloke/neural-chat-7B-v3-3-GGUF` | ~4.4 GB | ~6 GB |

### Reasoning / Thinking

| Model | Repo ID | Size (Q4_K_M) | VRAM (Q4_K_M) |
|-------|---------|--------------|---------------|
| DeepSeek R1 Distill Llama 8B | `bartowski/DeepSeek-R1-Distill-Llama-8B-GGUF` | ~4.9 GB | ~6 GB |
| DeepSeek R1 Distill Qwen 7B | `bartowski/DeepSeek-R1-Distill-Qwen-7B-GGUF` | ~4.7 GB | ~6 GB |
| DeepSeek R1 Distill Qwen 14B | `bartowski/DeepSeek-R1-Distill-Qwen-14B-GGUF` | ~9.0 GB | ~11 GB |
| DeepSeek R1 Distill Qwen 32B | `bartowski/DeepSeek-R1-Distill-Qwen-32B-GGUF` | ~20 GB | ~24 GB |
| QwQ 32B | `bartowski/QwQ-32B-GGUF` | ~20 GB | ~24 GB |

### Code

| Model | Repo ID | Size (Q4_K_M) | VRAM (Q4_K_M) |
|-------|---------|--------------|---------------|
| Qwen 2.5 Coder 7B Instruct | `bartowski/Qwen2.5-Coder-7B-Instruct-GGUF` | ~4.7 GB | ~6 GB |
| Qwen 2.5 Coder 14B Instruct | `bartowski/Qwen2.5-Coder-14B-Instruct-GGUF` | ~9.0 GB | ~11 GB |
| Qwen 2.5 Coder 32B Instruct | `bartowski/Qwen2.5-Coder-32B-Instruct-GGUF` | ~20 GB | ~24 GB |
| DeepSeek Coder V2 Lite | `bartowski/DeepSeek-Coder-V2-Lite-Instruct-GGUF` | ~10 GB | ~12 GB |
| CodeLlama 7B Instruct | `TheBloke/CodeLlama-7B-Instruct-GGUF` | ~4.4 GB | ~6 GB |
| CodeLlama 13B Instruct | `TheBloke/CodeLlama-13B-Instruct-GGUF` | ~8.1 GB | ~10 GB |

---

## Choosing a Quantization

| Quant | Quality | Size | Best For |
|-------|---------|------|----------|
| `Q2_K` | lowest | ~35% | Tight VRAM, acceptable quality |
| `Q4_K_M` | good | ~55% | Best balance — recommended |
| `Q5_K_M` | better | ~65% | More VRAM, better output |
| `Q8_0` | near-lossless | ~100% | Maximum quality, large VRAM |

```powershell
python scripts/download_model.py "bartowski/Meta-Llama-3.1-8B-Instruct-GGUF" "Meta-Llama-3.1-8B-Instruct-Q5_K_M.gguf"
```

---

## Auth

API keys live in `auth_keys.conf` — **gitignored, never committed**.

```powershell
copy auth_keys.conf.example auth_keys.conf
```

Generate a key:

```powershell
python -c "import secrets; print('sk-' + secrets.token_hex(24))"
```

Add one line per key in `auth_keys.conf`:

```nginx
"Bearer sk-your-real-key-here" 1;
```

After editing, reload the gateway:

```powershell
docker compose up -d api-gateway
```

---

## Common Commands

| Action | Command |
|--------|---------|
| First start / rebuild | `docker compose up -d --build` |
| Restart AI server (new model) | `docker compose restart ai-server` |
| Reload gateway (auth key change) | `docker compose up -d api-gateway` |
| Pre-warm all models into VRAM | `python scripts/warmup.py` |
| Stop everything | `docker compose down` |
| Check status | `docker compose ps` |
| AI server logs | `docker compose logs -f ai-server` |
| Gateway logs | `docker compose logs -f api-gateway` |
| Tunnel logs | `docker compose logs -f cloudflared` |

---

## Docs

- [docs/API.md](./docs/API.md) — Full API reference, integration examples (Python, JS, TS, C#, Go, curl, LangChain)
- [docs/STARTUP_GUIDE.md](./docs/STARTUP_GUIDE.md) — First-run checklist, troubleshooting
