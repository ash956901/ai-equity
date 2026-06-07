import sys, os, time, logging
logging.basicConfig(level=logging.WARNING)
for _s in (sys.stdout, sys.stderr):
    try: _s.reconfigure(encoding='utf-8', errors='replace')
    except Exception: pass
sys.path.insert(0, os.path.abspath('.'))
from src.config import get_settings
get_settings.cache_clear()
s = get_settings()
print(f'MODEL={s.get_llm_model()} KEYS={len(s.get_deepseek_api_keys())}', flush=True)

from src.agents.middleware_openai_compat import _nim_extra_body, build_nim_chat
print(f'extra_body(gpt-oss)={_nim_extra_body("openai/gpt-oss-120b")}')
print(f'extra_body(deepseek)={_nim_extra_body("deepseek-ai/deepseek-v4-pro")}')

from src.llm import get_llm
llm = get_llm(temperature=0.2)
print(f'get_llm type={type(llm).__name__} has_rotation={hasattr(llm,"_key_pool")}', flush=True)

from langchain_core.messages import HumanMessage
t0=time.time()
try:
    r = llm.invoke([HumanMessage(content='Reply with exactly: COMPARE_OK')])
    print(f'COMPARE_PATH_OK|{time.time()-t0:.1f}s|{r.content[:40]!r}', flush=True)
except Exception as e:
    print(f'COMPARE_PATH_FAIL|{time.time()-t0:.1f}s|{type(e).__name__}: {str(e)[:120]}', flush=True)

from src.agents.orchestrator import build_research_agent
agent = build_research_agent()
t0=time.time()
try:
    res = agent.invoke({'messages':[{'role':'user','content':'Explain why defense theme is heating up this week\n\n[Context: expertise_level=intermediate]'}]},
        config={'configurable':{'thread_id':'verify-final-gptoss'}})
    txt = res['messages'][-1].content
    print(f'CHAT_PATH_OK|{time.time()-t0:.1f}s|{len(txt)}chars', flush=True)
    print('=== ANSWER ===\n' + txt[:600])
except Exception as e:
    print(f'CHAT_PATH_FAIL|{time.time()-t0:.1f}s|{type(e).__name__}: {str(e)[:140]}', flush=True)
