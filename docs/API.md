# API Reference

This server exposes an **OpenAI-compatible REST API**, meaning any library or tool built for the OpenAI API works here by changing the `base_url` and `api_key`.

---

## Connection

| Setting | Value |
|---------|-------|
| Local URL | `http://localhost/v1` |
| Public URL | `https://ai.deetalk.win/v1` |
| Auth | `Authorization: Bearer <your-key>` |
| Keys | Defined in `auth_keys.conf` |

---

## Endpoints

### `GET /v1/models` — List models

Returns all registered models.

```bash
curl http://localhost/v1/models \
  -H "Authorization: Bearer <your-key>"
```

**Response:**
```json
{
  "object": "list",
  "data": [
    { "id": "mistral-7b-instruct-v0.2.Q2_K", "object": "model" },
    { "id": "DeepSeek-R1-Distill-Llama-8B-Q4_K_M", "object": "model" },
    { "id": "Qwen2.5-Coder-7B-Instruct-Q4_K_M", "object": "model" }
  ]
}
```

---

### `POST /v1/chat/completions` — Chat

**Request body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `model` | string | yes | Model ID from `/v1/models` |
| `messages` | array | yes | Conversation history |
| `stream` | boolean | no | Stream tokens as SSE (default: false) |
| `max_tokens` | integer | no | Max tokens to generate |
| `temperature` | float | no | 0.0–2.0, default 1.0 |
| `top_p` | float | no | Nucleus sampling, default 1.0 |
| `system` | string | no | Shorthand system prompt |

---

## Available Models

| Model ID | Size | Best For |
|----------|------|----------|
| `mistral-7b-instruct-v0.2.Q2_K` | 2.9 GB | Fast general chat, low VRAM |
| `Qwen2.5-Coder-7B-Instruct-Q4_K_M` | 4.4 GB | Code generation, debugging, technical tasks |
| `DeepSeek-R1-Distill-Llama-8B-Q4_K_M` | 4.6 GB | Reasoning, analysis, step-by-step thinking |
| `cognitivecomputations_Dolphin3.0-R1-Mistral-24B-Q3_K_M` | 10.7 GB | General purpose, agentic, uncensored (best quality) |

> **Tip:** Use Dolphin for agentic/general tasks. Use DeepSeek for anything requiring structured reasoning. Use Qwen for code.

---

## Integration Examples

### Python — OpenAI SDK

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost/v1",
    api_key="sk-your-key-here",
)

# Basic chat
response = client.chat.completions.create(
    model="mistral-7b-instruct-v0.2.Q2_K",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What is the capital of France?"},
    ],
)
print(response.choices[0].message.content)
```

```python
# Streaming
stream = client.chat.completions.create(
    model="DeepSeek-R1-Distill-Llama-8B-Q4_K_M",
    messages=[{"role": "user", "content": "Explain recursion step by step."}],
    stream=True,
)
for chunk in stream:
    print(chunk.choices[0].delta.content or "", end="", flush=True)
```

```python
# Code generation
response = client.chat.completions.create(
    model="Qwen2.5-Coder-7B-Instruct-Q4_K_M",
    messages=[
        {"role": "system", "content": "You are an expert software engineer."},
        {"role": "user", "content": "Write a Python function to parse a JWT without a library."},
    ],
    temperature=0.2,
)
print(response.choices[0].message.content)
```

---

### JavaScript / Node.js — OpenAI SDK

```javascript
import OpenAI from "openai";

const client = new OpenAI({
  baseURL: "http://localhost/v1",
  apiKey: "sk-your-key-here",
});

// Basic chat
const response = await client.chat.completions.create({
  model: "mistral-7b-instruct-v0.2.Q2_K",
  messages: [
    { role: "system", content: "You are a helpful assistant." },
    { role: "user", content: "What is the capital of France?" },
  ],
});
console.log(response.choices[0].message.content);
```

```javascript
// Streaming
const stream = await client.chat.completions.create({
  model: "DeepSeek-R1-Distill-Llama-8B-Q4_K_M",
  messages: [{ role: "user", content: "Explain recursion step by step." }],
  stream: true,
});
for await (const chunk of stream) {
  process.stdout.write(chunk.choices[0]?.delta?.content ?? "");
}
```

---

### TypeScript

```typescript
import OpenAI from "openai";

const client = new OpenAI({
  baseURL: "http://localhost/v1",
  apiKey: process.env.LOCAL_AI_KEY ?? "",
});

async function chat(prompt: string, model = "mistral-7b-instruct-v0.2.Q2_K"): Promise<string> {
  const response = await client.chat.completions.create({
    model,
    messages: [{ role: "user", content: prompt }],
  });
  return response.choices[0].message.content ?? "";
}
```

---

### curl (bash)

```bash
# Set once in your shell
export AI_KEY="sk-your-key-here"
export AI_URL="http://localhost/v1"

# List models
curl $AI_URL/models -H "Authorization: Bearer $AI_KEY"

# Chat
curl $AI_URL/chat/completions \
  -H "Authorization: Bearer $AI_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "mistral-7b-instruct-v0.2.Q2_K",
    "messages": [{"role": "user", "content": "Hello"}]
  }'

# Streaming
curl $AI_URL/chat/completions \
  -H "Authorization: Bearer $AI_KEY" \
  -H "Content-Type: application/json" \
  --no-buffer \
  -d '{
    "model": "DeepSeek-R1-Distill-Llama-8B-Q4_K_M",
    "messages": [{"role": "user", "content": "Think through this step by step: what is 17 * 23?"}],
    "stream": true
  }'
```

---

### PowerShell

```powershell
$key = "sk-your-key-here"
$url = "http://localhost/v1"

# List models
curl.exe $url/models -H "Authorization: Bearer $key"

# Chat
$body = @{
    model    = "mistral-7b-instruct-v0.2.Q2_K"
    messages = @(@{ role = "user"; content = "Hello" })
} | ConvertTo-Json

Invoke-RestMethod "$url/chat/completions" `
  -Method POST `
  -Headers @{ Authorization = "Bearer $key"; "Content-Type" = "application/json" } `
  -Body $body |
  Select-Object -ExpandProperty choices |
  ForEach-Object { $_.message.content }
```

---

### C# — OpenAI NuGet package

```csharp
using OpenAI;
using OpenAI.Chat;

var client = new OpenAIClient(
    new ApiKeyCredential("sk-your-key-here"),
    new OpenAIClientOptions { Endpoint = new Uri("http://localhost/v1") }
);

var chat = client.GetChatClient("mistral-7b-instruct-v0.2.Q2_K");

var response = await chat.CompleteChatAsync(new[]
{
    new UserChatMessage("What is the capital of France?")
});

Console.WriteLine(response.Value.Content[0].Text);
```

---

### Go — `sashabaranov/go-openai`

```go
package main

import (
    "context"
    "fmt"
    openai "github.com/sashabaranov/go-openai"
)

func main() {
    cfg := openai.DefaultConfig("sk-your-key-here")
    cfg.BaseURL = "http://localhost/v1"
    client := openai.NewClientWithConfig(cfg)

    resp, err := client.CreateChatCompletion(context.Background(),
        openai.ChatCompletionRequest{
            Model: "mistral-7b-instruct-v0.2.Q2_K",
            Messages: []openai.ChatCompletionMessage{
                {Role: openai.ChatMessageRoleUser, Content: "Hello"},
            },
        },
    )
    if err != nil {
        panic(err)
    }
    fmt.Println(resp.Choices[0].Message.Content)
}
```

---

### LangChain (Python)

```python
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    base_url="http://localhost/v1",
    api_key="sk-your-key-here",
    model="mistral-7b-instruct-v0.2.Q2_K",
    temperature=0.7,
)

response = llm.invoke("What is the capital of France?")
print(response.content)
```

---

### LangChain (JavaScript)

```javascript
import { ChatOpenAI } from "@langchain/openai";

const llm = new ChatOpenAI({
  configuration: {
    baseURL: "http://localhost/v1",
    apiKey: "sk-your-key-here",
  },
  model: "mistral-7b-instruct-v0.2.Q2_K",
});

const response = await llm.invoke("What is the capital of France?");
console.log(response.content);
```

---

## Environment Variable Pattern

Store your key in a `.env` file and load it — never hardcode keys in source:

**.env**
```
LOCAL_AI_URL=http://localhost/v1
LOCAL_AI_KEY=sk-your-key-here
```

**Python**
```python
from dotenv import load_dotenv
import os
load_dotenv()

client = OpenAI(
    base_url=os.getenv("LOCAL_AI_URL"),
    api_key=os.getenv("LOCAL_AI_KEY"),
)
```

**Node.js**
```javascript
import "dotenv/config";
const client = new OpenAI({
  baseURL: process.env.LOCAL_AI_URL,
  apiKey: process.env.LOCAL_AI_KEY,
});
```

---

## Error Reference

| HTTP | Meaning | Fix |
|------|---------|-----|
| `401` | Invalid or missing API key | Check `Authorization: Bearer <key>` matches `auth_keys.conf` |
| `404` | Unknown model ID | Run `GET /v1/models` to see valid IDs |
| `500` | Server error | Check `docker compose logs ai-server` |
| Connection refused | Stack not running | Run `docker compose up -d` |

---

## Loading All Models at Startup

By default, llama.cpp loads models on the first request (lazy). To pre-warm all models so the first real request is fast:

```powershell
python scripts/warmup.py
```

This sends a minimal request to each model, triggering loading into VRAM. Run it after `docker compose restart ai-server`.

> **VRAM note (RTX 3060, 12 GB):** Dolphin 24B uses ~10.7 GB alone. The 7–8B models (~5–6 GB each) can coexist.
> The server loads up to `--models-max 3` models simultaneously and evicts the least-recently-used when the limit is hit.
