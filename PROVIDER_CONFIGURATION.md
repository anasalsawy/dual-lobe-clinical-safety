# Complete Provider Configuration Guide

## How the System Works 🔄

The dual-lobe system uses **LiteLLM** with automatic provider detection:

1. **Model Identifier** → Auto-detects provider (e.g., `groq/mixtral-8x7b-32768` → Groq provider)
2. **API Key Resolution** → Hierarchical lookup from multiple environment variables
3. **Adaptive Rate Limiting** → Per-provider/model rate limit discovery and enforcement
4. **Fallback Chain** → Automatic failover if primary provider is unavailable

---

## Supported Providers & Credentials

### 1. **OpenRouter** ⭐ (Recommended - Free Tier Available)
```env
# Models
DUAL_LOBE_A_MODEL=openrouter/nvidia/nemotron-3-super-120b-a12b:free
DUAL_LOBE_B_MODEL=openrouter/nvidia/nemotron-3-super-120b-a12b:free

# API Key (one of these)
OPENROUTER_API_KEY=sk-or-...
```
**Free Models Available:**
- `openrouter/nvidia/nemotron-3-super-120b-a12b:free`
- `openrouter/meta-llama/llama-2-70b-chat`
- `openrouter/mistralai/mistral-7b-instruct`

**Links:** https://openrouter.ai/keys

---

### 2. **Groq** ⚡ (Fast, Free Tier)
```env
DUAL_LOBE_A_MODEL=groq/mixtral-8x7b-32768
DUAL_LOBE_B_MODEL=groq/llama2-70b-4096

# API Key
GROQ_API_KEY=gsk_...
```
**Free Models:**
- `groq/mixtral-8x7b-32768` (MoE, very fast)
- `groq/llama2-70b-4096` (Open source)
- `groq/llama-3-70b-8192`

**Links:** https://console.groq.com/keys

**Rate Limits (Free Tier):**
```env
DUAL_LOBE_GROQ_FREE_RPM=30    # Requests per minute
DUAL_LOBE_GROQ_FREE_TPM=6000  # Tokens per minute
```

---

### 3. **OpenAI** (GPT-4, GPT-4o)
```env
DUAL_LOBE_A_MODEL=openai/gpt-4o
DUAL_LOBE_B_MODEL=openai/gpt-4o-mini

# API Key
OPENAI_API_KEY=sk-...
```
**Models:**
- `openai/gpt-4o` (Latest, multimodal)
- `openai/gpt-4o-mini` (Faster, cheaper)
- `openai/gpt-4-turbo`
- `openai/gpt-3.5-turbo`

**Links:** https://platform.openai.com/api-keys

**Cost:** Pay-per-token (~$5-15/1M input tokens depending on model)

---

### 4. **Google Gemini**
```env
DUAL_LOBE_A_MODEL=gemini/gemini-3.5-flash-lite
DUAL_LOBE_B_MODEL=gemini/gemini-3.5-flash

# API Keys (one of these)
GEMINI_API_KEY=AIzaSy...
GOOGLE_API_KEY=AIzaSy...
```
**Models:**
- `gemini/gemini-3.5-flash-lite` (Fastest, free tier)
- `gemini/gemini-3.5-flash` (Very fast)
- `gemini/gemini-2.0-flash`
- `gemini/gemini-pro`

**Links:** https://makersuite.google.com/app/apikey

**Note:** ⚠️ Gemini has aggressive rate limiting on free tier

---

### 5. **Anthropic Claude**
```env
DUAL_LOBE_A_MODEL=anthropic/claude-3-5-sonnet-20241022
DUAL_LOBE_B_MODEL=anthropic/claude-3-5-haiku-20241022

# API Key
ANTHROPIC_API_KEY=sk-ant-...
```
**Models:**
- `anthropic/claude-3-5-sonnet-20241022` (Latest, intelligent)
- `anthropic/claude-3-5-haiku-20241022` (Fast, cheap)
- `anthropic/claude-opus-4-1-20250805`

**Links:** https://console.anthropic.com/keys

---

### 6. **Mistral AI**
```env
DUAL_LOBE_A_MODEL=mistral/mistral-large-2411
DUAL_LOBE_B_MODEL=mistral/mistral-medium

# API Key
MISTRAL_API_KEY=...
```
**Models:**
- `mistral/mistral-large` (Powerful)
- `mistral/mistral-medium` (Balanced)
- `mistral/mistral-small` (Fast)

**Links:** https://console.mistral.ai/

---

### 7. **Cerebras**
```env
DUAL_LOBE_A_MODEL=cerebras/llama-3-70b-instruct
DUAL_LOBE_B_MODEL=cerebras/llama-3-8b

# API Key
CEREBRAS_API_KEY=csk_...
```
**Links:** https://www.cerebras.ai/

---

### 8. **Together AI**
```env
DUAL_LOBE_A_MODEL=together_ai/meta-llama/Llama-3-70b-chat-hf
DUAL_LOBE_B_MODEL=together_ai/meta-llama/Llama-3-8b-chat-hf

# API Key (one of these)
TOGETHER_API_KEY=...
TOGETHERAI_API_KEY=...
```
**Links:** https://www.together.ai/

---

### 9. **DeepInfra**
```env
DUAL_LOBE_A_MODEL=deepinfra/meta-llama/Llama-2-70b-chat-hf
DUAL_LOBE_B_MODEL=deepinfra/meta-llama/Llama-2-7b-chat-hf

# API Key
DEEPINFRA_API_KEY=...
```
**Links:** https://deepinfra.com/

---

### 10. **Fireworks AI**
```env
DUAL_LOBE_A_MODEL=fireworks/accounts/fireworks/models/llama-v2-70b-chat
DUAL_LOBE_B_MODEL=fireworks/accounts/fireworks/models/llama-v2-7b-chat

# API Key
FIREWORKS_API_KEY=...
```
**Links:** https://fireworks.ai/

---

### 11. **SambaNova**
```env
DUAL_LOBE_A_MODEL=sambanova/llama2-70b-chat
DUAL_LOBE_B_MODEL=sambanova/llama2-7b-chat

# API Key
SAMBANOVA_API_KEY=...
```
**Links:** https://cloud.sambanova.ai/

---

### 12. **X.ai / Grok**
```env
DUAL_LOBE_A_MODEL=xai/grok-2-1212
DUAL_LOBE_B_MODEL=xai/grok-vision-beta

# API Key (one of these)
GROK_API_KEY=...
XAI_API_KEY=...
```
**Links:** https://console.x.ai/

---

### 13. **Local / Self-Hosted (Ollama)**
```env
DUAL_LOBE_A_MODEL=ollama/llama2
DUAL_LOBE_B_MODEL=ollama/neural-chat
DUAL_LOBE_A_BASE_URL=http://localhost:11434/v1
DUAL_LOBE_B_BASE_URL=http://localhost:11434/v1
DUAL_LOBE_A_API_KEY=local  # No-op key
DUAL_LOBE_B_API_KEY=local
```
**Links:** https://ollama.ai/

---

## Configuration Hierarchy 📊

The system resolves credentials in this order:

### 1. Per-Role Specific (Highest Priority)
```env
DUAL_LOBE_A_API_KEY=...           # Only for role A
DUAL_LOBE_B_API_KEY=...           # Only for role B
DUAL_LOBE_A_BASE_URL=...          # Only for role A
DUAL_LOBE_B_BASE_URL=...          # Only for role B
DUAL_LOBE_A_TIER=paid             # Only for role A
DUAL_LOBE_B_RPM=30                # Only for role B
```

### 2. Provider-Specific (Mid Priority)
```env
# Auto-detected from model identifier
OPENROUTER_API_KEY=...   # If model starts with "openrouter/"
GROQ_API_KEY=...         # If model starts with "groq/"
ANTHROPIC_API_KEY=...    # If model contains "claude"
GEMINI_API_KEY=...       # If model contains "gemini"
OPENAI_API_KEY=...       # Fallback default
```

### 3. Global Defaults (Lowest Priority)
```env
DUAL_LOBE_PROVIDER_TIER=auto      # Default: auto-detect free vs paid
DUAL_LOBE_RATE_SAFETY=0.92        # Use 92% of discovered limits
DUAL_LOBE_RETRY_ROUNDS=3          # Retry 3 times on rate limit
DUAL_LOBE_RETRY_MAX_SECONDS=30    # Max backoff 30 seconds
```

---

## Fallback Chain Configuration 🔄

Define multiple providers to use in sequence if primary fails:

```env
# As environment variable (JSON array)
DUAL_LOBE_A_FALLBACKS='[
  {
    "model": "anthropic/claude-3-5-haiku-20241022",
    "api_key_env": "ANTHROPIC_API_KEY",
    "max_tokens": 8000,
    "tier": "paid"
  },
  {
    "model": "groq/mixtral-8x7b-32768",
    "api_key_env": "GROQ_API_KEY",
    "max_tokens": 8000,
    "tier": "free"
  }
]'

# Global fallbacks (used by all roles)
DUAL_LOBE_FALLBACKS='[
  {"model": "openrouter/...", "api_key_env": "OPENROUTER_API_KEY"},
  {"model": "groq/...", "api_key_env": "GROQ_API_KEY"}
]'

# Cross-role failover (B can use A's models, etc.)
DUAL_LOBE_CROSS_ROLE_FAILOVER=true
```

---

## Railway Deployment Example 🚀

### Scenario: Groq (Free) with Claude Fallback

In Railway Dashboard → Variables:

```
DUAL_LOBE_A_MODEL=groq/mixtral-8x7b-32768
DUAL_LOBE_B_MODEL=groq/llama2-70b-4096
GROQ_API_KEY=gsk_...

DUAL_LOBE_A_FALLBACKS=[{"model":"anthropic/claude-3-5-haiku-20241022","api_key_env":"ANTHROPIC_API_KEY","tier":"paid"}]
ANTHROPIC_API_KEY=sk-ant-...

DUAL_LOBE_RATE_SAFETY=0.92
DUAL_LOBE_RETRY_ROUNDS=6
```

**Behavior:**
1. First tries Groq (free) - if rate limited or error
2. Falls back to Claude Haiku (paid)
3. System learns actual rate limits and paces accordingly

---

## Rate Limiting & Safety Settings 🎚️

### System Pacing Configuration

```env
# Enable adaptive rate limiting (learns from API responses)
DUAL_LOBE_RATE_SENSOR=true

# Use 92% of discovered limits (safety margin)
DUAL_LOBE_RATE_SAFETY=0.92

# Exponential backoff retry configuration
DUAL_LOBE_RETRY_ROUNDS=6              # Max 6 retry attempts
DUAL_LOBE_RETRY_BASE_SECONDS=1.5      # Start with 1.5s backoff
DUAL_LOBE_RETRY_MAX_SECONDS=60        # Cap at 60s between retries

# Rate limit discovery
DUAL_LOBE_RATE_DISCOVERY_TTL_SECONDS=21600  # Cache limits for 6 hours
DUAL_LOBE_RATE_DISCOVERY_TIMEOUT_SECONDS=3  # Timeout discovery in 3s

# Failover on rate limit
DUAL_LOBE_FAILOVER_ON_RATE_LIMIT=true
```

### Per-Provider Free Tier Hints

```env
# These are auto-detected but can be overridden
DUAL_LOBE_GROQ_FREE_RPM=30
DUAL_LOBE_GROQ_FREE_TPM=6000

DUAL_LOBE_OPENROUTER_FREE_RPM=20
DUAL_LOBE_OPENROUTER_FREE_TPM=...

# Global max limits
DUAL_LOBE_MAX_RPM=100
DUAL_LOBE_MAX_TPM=100000
```

---

## Model Selection Matrix 📋

| Use Case | Primary | Fallback | Config |
|----------|---------|----------|--------|
| **Free/Budget** | Groq Mixtral | OpenRouter free | `GROQ_API_KEY` + fallback |
| **Performance** | Claude 3.5 Sonnet | GPT-4o | `ANTHROPIC_API_KEY` + `OPENAI_API_KEY` |
| **Speed** | Groq Mixtral | Gemini Flash | Groq primary, Gemini fallback |
| **Reliability** | OpenAI GPT-4 | Claude 3.5 | Both paid providers |
| **Local Dev** | Ollama Llama2 | N/A | `OLLAMA_BASE_URL=localhost:11434` |
| **Clinical** | Local Ollama | N/A | Must be localhost by design |

---

## Testing Your Configuration

### Verify Provider Detection
```bash
# Check what provider is detected
python -c "
from dual_lobe_crewai.llm_factory import primary_spec
spec = primary_spec('A')
print(f'Provider: {spec.provider}')
print(f'Model: {spec.model}')
print(f'Has API Key: {bool(spec.api_key)}')
print(f'Tier: {spec.effective_tier}')
"
```

### Test API Connection
```bash
python -m dual_lobe_crewai.main --test-provider A
```

### Check Fallback Chain
```bash
python -c "
from dual_lobe_crewai.llm_factory import resolve_role_specs
specs = resolve_role_specs('A')
for i, s in enumerate(specs):
    print(f'{i}. {s.label}: {s.provider}/{s.model}')
"
```

---

## Cost Estimation

| Provider | Model | Cost | Free Tier | Best For |
|----------|-------|------|-----------|----------|
| **Groq** | Mixtral | Free | ✅ 30 RPM | Development, Testing |
| **OpenRouter** | Nemotron | Free | ✅ Limited | Small runs |
| **Gemini** | Flash | ~$0.075/1M in | ✅ Limited | Cheap production |
| **Claude** | Haiku | ~$0.80/1M in | ❌ | Production, Safety |
| **GPT-4o** | GPT-4o | ~$5/1M in | ❌ | Performance |
| **Ollama** | Self-hosted | $0 | ✅ | Private/Offline |

**Example Study Cost (100 cases × 3 repeats):**
- Groq free: $0
- Gemini: ~$3-5
- Claude Haiku: ~$2-4
- GPT-4o: ~$15-30

---

## Troubleshooting

### "API key not found"
```bash
# Check what variables are being looked for
python -c "
from dual_lobe_crewai.llm_factory import _provider_env_names
keys, bases = _provider_env_names('groq/mixtral-8x7b-32768', None)
print('Looking for:', keys)
"
```

### "Rate limit exceeded"
1. Check current limits: `DUAL_LOBE_RATE_DISCOVERY_TTL_SECONDS` (cache learned limits)
2. Increase safety margin: `DUAL_LOBE_RATE_SAFETY=0.8` (80%)
3. Add fallback: `DUAL_LOBE_A_FALLBACKS=[...]`

### "Provider not recognized"
- Ensure model identifier has provider prefix (e.g., `groq/`, `openai/`)
- Or set explicit `DUAL_LOBE_A_BASE_URL`

---

## Summary

The dual-lobe system:
- ✅ Supports 13+ LLM providers out of the box
- ✅ Auto-detects providers from model identifiers
- ✅ Hierarchical credential resolution (no hardcoding keys)
- ✅ Fallback chains for reliability
- ✅ Adaptive rate limiting that learns from API responses
- ✅ Per-role and global configuration
- ✅ Free tier auto-detection
- ✅ Cross-role failover capability

You can literally swap providers by just changing `DUAL_LOBE_A_MODEL` and adding the appropriate API key!

---

**Created:** 2026-09-29
**Updated:** With complete provider matrix
