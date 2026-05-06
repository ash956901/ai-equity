import json
from langchain_core.messages import HumanMessage

def get_synthesis_llm():
    from src.config import get_settings
    s = get_settings()
    model = s.get_llm_model()

    if s.llm_provider == "ollama":
        from langchain_ollama import ChatOllama
        return ChatOllama(model=model, base_url=s.ollama_base_url, temperature=s.llm_temperature)
    elif s.llm_provider == "groq":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model=model, api_key=s.groq_api_key, base_url=s.groq_base_url, temperature=s.llm_temperature)
    elif s.llm_provider == "deepseek":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model=model, api_key=s.deepseek_api_key, base_url=s.deepseek_base_url, temperature=s.llm_temperature)
    elif s.llm_provider == "cerebras":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model=model, api_key=s.cerebras_api_key, base_url=s.cerebras_base_url, temperature=s.llm_temperature)
    elif s.llm_provider == "nvidia":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model=model, api_key=s.deepseek_api_key, base_url=s.deepseek_base_url, temperature=s.llm_temperature)
    else:
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model=model, api_key=s.openai_api_key, temperature=s.llm_temperature)

def synthesize_response(raw_data: str, user_query: str, context: str = "") -> str:
    """Use LLM to format the JSON data into a clean text response."""
    llm = get_synthesis_llm()
    prompt = f"""You are Iris, an Indian equity research assistant. Be concise.
Rules:
- You are providing the final answer directly to the user based on the raw data.
- If the Raw Data is empty or contains no results, perform the analysis directly based on the information provided in the User Query and your financial knowledge.
- Keep the tone professional, like a financial analyst.
- Keep responses under 200 words for simple queries, 500 words max for complex.
- Use markdown formatting with bullet points and bold text where appropriate.

User Query: {user_query}
Context: {context}

Raw Data from API:
{raw_data}

Synthesize this data into a helpful response for the user."""
    
    response = llm.invoke([HumanMessage(content=prompt)])
    return getattr(response, "content", str(response))

def extract_companies_from_query(query: str) -> list[str]:
    """Simple extraction of company names to compare using heuristic."""
    words = query.replace(",", "").replace(".", "").split()
    candidates = []
    skip = {"compare", "and", "vs", "versus", "between", "the", "companies", "stock", "price", "of", "what", "is", "difference"}
    for word in words:
        if word.lower() not in skip and len(word) > 2:
            candidates.append(word)
    return candidates[:2]
