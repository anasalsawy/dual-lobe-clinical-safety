# Deployment Configuration Review for Railway

## Project Overview
- **Name**: dual-lobe-clinical-safety
- **Type**: Python CLI/Benchmark System
- **Python**: 3.10+
- **Framework**: CrewAI + Pydantic

---

## ✅ Configuration Status

### 1. **Project Structure** - READY
```
✓ pyproject.toml exists with all dependencies
✓ Entry points configured:
  - dual-lobe: dual_lobe_crewai.main:main
  - dual-lobe-clinical: dual_lobe_clinical.main:main
✓ Optional test dependencies defined
✓ Source code in organized src/ directory
```

### 2. **Dependencies** - READY
```
Core Dependencies:
✓ crewai>=0.80.0 (AI orchestration framework)
✓ pydantic>=2.0 (data validation)
✓ python-dotenv>=1.0 (environment config)
✓ cryptography>=43.0 (privacy/security)

Test Dependencies:
✓ pytest>=8
✓ pytest-asyncio>=0.23
```

### 3. **Environment Variables** - ⚠️ REQUIRES CONFIGURATION

**CRITICAL - Must set in Railway:**

```env
# Model Configuration (Choose provider)
DUAL_LOBE_A_MODEL=openrouter/nvidia/nemotron-3-super-120b-a12b:free
DUAL_LOBE_B_MODEL=openrouter/nvidia/nemotron-3-super-120b-a12b:free

# API Keys (Required - populate before deploy)
OPENAI_API_KEY=sk-...                    # If using OpenAI
DUAL_LOBE_A_API_KEY=...                 # Optional A-specific key
DUAL_LOBE_B_API_KEY=...                 # Optional B-specific key
```

**IMPORTANT - Clinical Guardian B:**

⚠️ **DEPLOYMENT CHALLENGE**: The clinical B component is designed to run **LOCAL ONLY** (http://127.0.0.1:11434/v1). This assumes:
- Local Ollama service running on the same machine
- Port 11434 accessible

**For Railway Deployment, Consider:**
1. **Option A**: Disable clinical B, use regular models for both lobes
2. **Option B**: Deploy Ollama as a sidecar service on Railway
3. **Option C**: Use a remote clinical B if available (requires config change)

---

## 🔧 Deployment Files Created

### 1. **railway.toml** ✓
Railway-native configuration file for CI/CD deployment.
- Defines Python service
- Sets basic start command
- Can be customized for different run modes

### 2. **Dockerfile** ✓
Multi-stage build optimized for production:
- **Builder stage**: Installs dependencies, builds package
- **Runtime stage**: Minimal image with only runtime needs
- **Features**:
  - ~400MB final image size
  - Health checks enabled
  - Proper signal handling
  - Python optimization flags

---

## 📋 Pre-Deployment Checklist

### GitHub → Railway Setup

- [ ] **Railway Account**: Create at https://railway.app
- [ ] **GitHub Connection**: Link your GitHub account in Railway
- [ ] **Environment Variables**: Add to Railway project settings:
  - [ ] DUAL_LOBE_A_MODEL
  - [ ] DUAL_LOBE_B_MODEL
  - [ ] OPENAI_API_KEY (or provider-specific keys)
  - [ ] DUAL_LOBE_CLINICAL_B_MODEL (if using clinical)
  - [ ] DUAL_LOBE_CLINICAL_B_BASE_URL (if overriding)
  - [ ] DUAL_LOBE_CLINICAL_B_API_KEY
  - [ ] DUAL_LOBE_MEMORY_PATH=/tmp/.dual_lobe_memory.jsonl (use /tmp for ephemeral)

### Model Selection

Choose ONE of these approaches:

**Option 1: Free Models (OpenRouter)**
```env
DUAL_LOBE_A_MODEL=openrouter/nvidia/nemotron-3-super-120b-a12b:free
DUAL_LOBE_B_MODEL=openrouter/nvidia/nemotron-3-super-120b-a12b:free
# No API key needed for free tier
```

**Option 2: OpenAI/GPT Models**
```env
DUAL_LOBE_A_MODEL=openai/gpt-4o
DUAL_LOBE_B_MODEL=openai/gpt-4o-mini
OPENAI_API_KEY=sk-...
```

**Option 3: Groq (Fast, Free Tier)**
```env
DUAL_LOBE_A_MODEL=groq/mixtral-8x7b-32768
DUAL_LOBE_B_MODEL=groq/llama2-70b-4096
GROQ_API_KEY=...
```

**Option 4: Google Gemini**
```env
DUAL_LOBE_A_MODEL=gemini/gemini-3.5-flash-lite
DUAL_LOBE_B_MODEL=gemini/gemini-3.5-flash-lite
GOOGLE_API_KEY=...
```

### Rate Limiting & Safety (Optional but Recommended)

```env
DUAL_LOBE_RATE_SAFETY=0.92          # 92% of discovered limits
DUAL_LOBE_RETRY_ROUNDS=3             # Retry failed requests
DUAL_LOBE_RETRY_MAX_SECONDS=30       # Exponential backoff cap
DUAL_LOBE_FAILOVER_ON_RATE_LIMIT=true # Switch models on rate limit
```

---

## 🚀 Deployment Options

### Option 1: CLI Tool (Current Setup)

**Use Case**: Run specific queries via Railway shell or scheduled jobs

```bash
# Run a clinical query
railway run python -m dual_lobe_clinical.main \
  --query "Assess patient risk" \
  --patient-context "Age: 65, BP: 160/90"

# Output: JSON result to stdout
```

**Pros**: Simple, lightweight, any-time execution
**Cons**: One-off runs, not persistent

### Option 2: Benchmark Runner (Evaluation Study)

**Use Case**: Run comprehensive evaluation studies

```bash
# Run evaluation with 3 repeats, all arms
railway run python evaluation/run_study.py \
  --arms a_only answer_verifier dual_lobe \
  --repeats 3
```

**Pros**: Full evaluation pipeline, reproducible
**Cons**: Long-running (~hours), needs persistent storage for results

### Option 3: Web Service (Future Enhancement)

Would require wrapping the CLI in a FastAPI/Flask server:
```python
from fastapi import FastAPI
from dual_lobe_clinical.engine import ClinicalDualLobeEngine

app = FastAPI()

@app.post("/query")
async def query(query: str, patient_context: str = ""):
    engine = ClinicalDualLobeEngine()
    result = await engine.run_clinical(query, patient_context)
    return result
```

---

## ⚠️ Known Limitations & Considerations

### 1. **Clinical Guardian B (Local-Only Design)**
- Current config requires local Ollama on port 11434
- Railway sandboxed environment may not support local services easily
- **Recommendation**: Use Option A - disable for initial deployment

### 2. **Storage & Persistence**
- Railway ephemeral filesystem (survives during dyno but not restarts)
- `.dual_lobe_memory.jsonl` will be lost on redeploy
- **For benchmarks**: Use Railway PostgreSQL add-on or S3-compatible storage

### 3. **API Rate Limits**
- Free tier models have rate limits (documented in .env.example)
- System has adaptive rate limiting (DUAL_LOBE_RATE_SAFETY)
- **Monitor**: Railway logs for rate limit errors

### 4. **Privacy & Encryption**
- Cryptography enabled for patient data tokenization
- Privacy receipts for audit trails
- **Ensure**: API keys not logged (use Railway secrets, not logs)

---

## 📊 Performance Expectations

| Metric | Value |
|--------|-------|
| Cold Start | ~5-10s (Python import + model load) |
| Per-Query Latency | 30-120s (LLM API calls) |
| Memory Usage | ~200-500MB |
| CPU Usage | Variable (depends on model provider) |
| Network | Outbound to API providers |

---

## 🔍 Validation Before Deploy

```bash
# 1. Test locally with Railway CLI
railway link  # Link to your Railway project
railway vars # View environment variables

# 2. Test CLI locally
python -m dual_lobe_clinical.main \
  --query "test" \
  --patient-context "{}"

# 3. Check dependencies
pip check

# 4. Run tests
pytest tests/ -v
```

---

## 📚 Resource Links

- [Railway Docs](https://docs.railway.app)
- [Railway Python Guide](https://docs.railway.app/guides/python)
- [CrewAI Docs](https://docs.crewai.com)
- [Environment Variables Best Practices](https://docs.railway.app/guides/environment-variables)
- [Railway Postgres Add-on](https://docs.railway.app/plugins/postgres)

---

## ✅ Deployment Readiness

| Component | Status | Notes |
|-----------|--------|-------|
| Code | ✅ Ready | In GitHub |
| Dependencies | ✅ Ready | pyproject.toml configured |
| Docker | ✅ Ready | Dockerfile provided |
| Config Files | ✅ Ready | railway.toml provided |
| Environment Vars | ⚠️ Needs setup | Must configure in Railway |
| API Keys | ⚠️ Needs setup | Provide your own |
| Clinical B | ⚠️ Architecture question | Needs decision on deployment approach |

---

## Next Steps

1. **Choose deployment model** (CLI vs Web vs Benchmark)
2. **Select LLM provider** and get API keys
3. **Set environment variables** in Railway project
4. **Decide on clinical B** strategy
5. **Push to GitHub** (configs already included)
6. **Deploy via Railway** UI or CLI
7. **Test** via Railway shell or scheduler

---

**Created**: 2026-09-29
**Project Version**: 0.2.0
