# Railway Deployment Quick Start

## 5-Minute Setup

### 1. Create Railway Project (2 min)

```bash
# Install Railway CLI
npm i -g @railway/cli

# Login
railway login

# Create new project
railway init --name dual-lobe-clinical

# Link to your repo (optional - Railway can auto-detect)
railway link <PROJECT_ID>
```

### 2. Set Environment Variables (2 min)

In Railway Dashboard → Project → Variables:

```
DUAL_LOBE_A_MODEL=groq/mixtral-8x7b-32768
DUAL_LOBE_B_MODEL=groq/llama2-70b-4096
GROQ_API_KEY=<your-groq-api-key>

# Or if using OpenRouter (free):
DUAL_LOBE_A_MODEL=openrouter/nvidia/nemotron-3-super-120b-a12b:free
DUAL_LOBE_B_MODEL=openrouter/nvidia/nemotron-3-super-120b-a12b:free

# Memory path (use /tmp for ephemeral Railway)
DUAL_LOBE_MEMORY_PATH=/tmp/.dual_lobe_memory.jsonl
```

### 3. Deploy (1 min)

**Option A: Via Railway Dashboard**
1. Connect GitHub repo
2. Railway auto-detects `railway.toml`
3. Set variables above
4. Deploy

**Option B: Via CLI**
```bash
railway up --build-command "pip install -e ." --start-command "python -m dual_lobe_clinical.main --query 'test' --patient-context '{}'"
```

---

## Test Your Deployment

### Via Railway Shell
```bash
# Connect to remote container
railway shell

# Run a test query
python -m dual_lobe_clinical.main \
  --query "Summarize treatment options" \
  --patient-context "Age: 65, Condition: Hypertension"
```

### View Logs
```bash
railway logs
```

---

## Common Deployment Scenarios

### Scenario 1: Run One-Off Queries
```bash
# In Railway Shell or via scheduled job
python -m dual_lobe_clinical.main \
  --query "$YOUR_QUERY" \
  --patient-context "$YOUR_CONTEXT"
```

### Scenario 2: Run Benchmark Study
```bash
# Set environment for study run
export STUDY_DIR=/tmp/results

# Run study with limited repeats (for testing)
python evaluation/run_study.py \
  --arms a_only \
  --repeats 1 \
  --output-dir $STUDY_DIR

# Download results
railway download $STUDY_DIR
```

### Scenario 3: Keep Service Warm (Worker)
```bash
# In railway.toml, use:
startCommand = "while true; do python -c 'print(\"ping\")'; sleep 60; done"
```

---

## Troubleshooting

### "No module named dual_lobe_clinical"
- **Cause**: Dependencies not installed
- **Fix**: Ensure pyproject.toml is in root, `pip install -e .` runs

### "API Rate Limit Exceeded"
- **Cause**: Free tier limits exceeded
- **Fix**: 
  1. Switch to paid API tier
  2. Use different model provider
  3. Increase `DUAL_LOBE_RETRY_MAX_SECONDS`

### "HTTP 127.0.0.1:11434 refused connection"
- **Cause**: Clinical Guardian B trying local Ollama (not available on Railway)
- **Fix**: Use different model provider for both A and B, or deploy Ollama separately

### "Permission denied: /tmp/.dual_lobe_memory.jsonl"
- **Cause**: /tmp may have restrictions
- **Fix**: Use `/home/dyno/.dual_lobe_memory.jsonl` instead

---

## Monitoring

### Real-time Logs
```bash
railway logs --follow
```

### CPU & Memory Usage
Railway Dashboard → Deployments → Resource Metrics

### Error Tracking
- Check Railway logs for `ERROR:` prefixes
- CrewAI/LiteLLM errors logged with context

---

## Cost Estimation

| Provider | Free Tier | Limitations |
|----------|-----------|------------|
| Groq | ✅ Yes | 30 reqs/min (fast models) |
| OpenRouter | ✅ Yes | Limited free credits |
| Google Gemini | ✅ Yes | Rate limited |
| OpenAI | ❌ No | Pay-per-token |

**Estimated Cost** (if using paid):
- Small study (1 case): ~$0.10-0.30
- Benchmark (100 cases × 3 repeats): ~$15-50
- Continuous service: ~$50-500/month (depends on usage)

---

## Next Steps After Deployment

1. **Test the deployment**: Run a test query via shell
2. **Set up logging**: Railway logs to external service (optional)
3. **Configure auto-redeploy**: Railway auto-redeployes on GitHub push
4. **Set up alerts**: Notify if deployment fails
5. **Monitor costs**: Set spending alerts in Railway

---

## Advanced: Custom Deployment

### Using Docker Registry
```bash
# Build locally
docker build -t myregistry/dual-lobe:latest .

# Push to Railway
railway service create --using-dockerfile
```

### Using Railway Volumes (for persistent storage)
```bash
# In railway.toml
[[volumes]]
mount_path = "/data"
size = "1GB"
```

### Multi-service Setup (with Ollama)
```toml
[[services]]
name = "dual-lobe"
type = "python"
startCommand = "python -m dual_lobe_clinical.main"

[[services]]
name = "ollama"
type = "docker"
# ... custom Ollama config
```

---

## Support

- **Railway Docs**: https://docs.railway.app
- **GitHub Issues**: https://github.com/anasalsawy/dual-lobe-clinical-safety/issues
- **Slack/Discord**: See README.md for community links

---

**Version**: 1.0
**Last Updated**: 2026-09-29
