"""Business logic for company comparison."""

from typing import Any

from src.agents import build_research_agent


class CompareService:
    """Runs comparison analysis via orchestrator."""

    def compare(
        self,
        user_id: str,
        company_ids: list[str],
        query: str,
        expertise_level: str,
    ) -> dict[str, Any]:
        agent = build_research_agent()
        company_ids_str = ", ".join(company_ids)
        user_message = (
            f"{query}\n\n"
            f"[Context: user_id={user_id}, "
            f"company_ids=[{company_ids_str}], "
            f"expertise_level={expertise_level}]"
        )
        result = agent.invoke(
            {"messages": [{"role": "user", "content": user_message}]},
            config={"configurable": {"thread_id": f"compare-{user_id}"}},
        )
        response_text = result["messages"][-1].content
        return {
            "response": response_text,
            "tokens_used": 0,
        }
