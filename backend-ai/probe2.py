import sys, os, time
sys.path.insert(0, os.path.abspath("."))
from src.config import get_settings
s = get_settings()
from openai import OpenAI
k = s.get_deepseek_api_keys()[0]
c = OpenAI(api_key=k, base_url=s.deepseek_base_url, timeout=30)
for model in ["meta/llama-3.1-8b-instruct", "openai/gpt-oss-120b", "deepseek-ai/deepseek-v4-pro"]:
    t0=time.time()
    try:
        r = c.chat.completions.create(model=model, messages=[{"role":"user","content":"OK"}], max_tokens=5, temperature=0)
        print(f"{model}: OK ({time.time()-t0:.1f}s)")
    except Exception as e:
        print(f"{model}: {type(e).__name__} {getattr(e,'status_code','')} ({time.time()-t0:.1f}s)")
