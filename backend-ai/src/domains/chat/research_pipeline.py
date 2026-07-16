"""Planner-driven chat research pipeline.

The pipeline breaks a query into task units, executes them in parallel, and
hands the consolidated evidence to the existing LLM layer for final synthesis.
"""

from __future__ import annotations

import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any, Literal, Optional
from uuid import UUID

from src.agents import invoke_research_agent
from src.agents.tools.financial import calculate_ratios, detect_risk_flags, get_latest_financials
from src.agents.tools.news import get_recent_news
from src.agents.tools.portfolio import calculate_portfolio_metrics, get_portfolio_holdings
from src.agents.tools.vector_search import search_filings, search_user_upload, thematic_discovery_search
from src.agents.tools.web_search import internet_search
from src.db.database import get_db
from src.db.models import Company
from src.config import get_settings

logger = logging.getLogger(__name__)

TaskKind = Literal[
    "company_snapshot",
    "news_snapshot",
    "filings_snapshot",
    "portfolio_snapshot",
    "thematic_snapshot",
    "web_snapshot",
]


@dataclass(frozen=True)
class PlannedTask:
    """A unit of work that can run in the worker pool."""

    name: str
    kind: TaskKind
    params: dict[str, Any]


@dataclass(frozen=True)
class TaskResult:
    """Normalized worker output for the aggregator."""

    name: str
    kind: TaskKind
    payload: Any
    source: dict[str, Any]


class ResearchPlanner:
    """Convert a chat request into a bounded task plan."""

    def plan(
        self,
        query: str,
        user_id: UUID,
        company_id: Optional[UUID],
        upload_id: Optional[UUID],
        primary_portfolio_id: Optional[UUID],
    ) -> list[PlannedTask]:
        query_lower = query.lower()
        tasks: list[PlannedTask] = []

        if company_id:
            tasks.append(
                PlannedTask(
                    name="company_snapshot",
                    kind="company_snapshot",
                    params={"company_id": str(company_id)},
                )
            )

        if company_id and any(
            keyword in query_lower
            for keyword in ("news", "sentiment", "headline", "filing", "quarter", "annual report")
        ):
            tasks.append(
                PlannedTask(
                    name="news_snapshot",
                    kind="news_snapshot",
                    params={"company_id": str(company_id)},
                )
            )

        if upload_id:
            tasks.append(
                PlannedTask(
                    name="filings_snapshot",
                    kind="filings_snapshot",
                    params={"upload_id": str(upload_id), "user_id": str(user_id), "query": query},
                )
            )
        elif company_id:
            tasks.append(
                PlannedTask(
                    name="filings_snapshot",
                    kind="filings_snapshot",
                    params={"company_id": str(company_id), "query": query},
                )
            )

        if primary_portfolio_id and any(
            keyword in query_lower for keyword in ("portfolio", "holdings", "exposure", "risk", "allocation")
        ):
            tasks.append(
                PlannedTask(
                    name="portfolio_snapshot",
                    kind="portfolio_snapshot",
                    params={"portfolio_id": str(primary_portfolio_id)},
                )
            )

        if any(
            keyword in query_lower
            for keyword in ("theme", "sector", "industry", "related companies", "similar companies")
        ) and not company_id:
            tasks.append(
                PlannedTask(
                    name="thematic_snapshot",
                    kind="thematic_snapshot",
                    params={"query": query},
                )
            )

        if not tasks:
            tasks.append(
                PlannedTask(
                    name="web_snapshot",
                    kind="web_snapshot",
                    params={"query": query},
                )
            )

        return self._dedupe(tasks)

    @staticmethod
    def _dedupe(tasks: list[PlannedTask]) -> list[PlannedTask]:
        seen: set[TaskKind] = set()
        ordered: list[PlannedTask] = []
        for task in tasks:
            if task.kind in seen:
                continue
            seen.add(task.kind)
            ordered.append(task)
        return ordered


class ResearchWorkerPool:
    """Execute planned tasks with bounded parallelism."""

    def __init__(self, max_workers: int) -> None:
        self.max_workers = max(1, max_workers)

    def run(self, tasks: list[PlannedTask]) -> list[TaskResult]:
        if not tasks:
            return []

        results: list[TaskResult] = []
        with ThreadPoolExecutor(max_workers=min(self.max_workers, len(tasks))) as executor:
            future_map = {executor.submit(self._execute_task, task): task for task in tasks}
            for future in as_completed(future_map):
                task = future_map[future]
                try:
                    results.append(future.result())
                except Exception as exc:  # pragma: no cover - defensive guard
                    logger.exception("Worker task failed: %s", task.name)
                    results.append(
                        TaskResult(
                            name=task.name,
                            kind=task.kind,
                            payload={"error": str(exc)},
                            source={"name": task.name, "kind": task.kind, "status": "error"},
                        )
                    )

        kind_order = {task.kind: index for index, task in enumerate(tasks)}
        return sorted(results, key=lambda item: kind_order.get(item.kind, 0))

    def _execute_task(self, task: PlannedTask) -> TaskResult:
        if task.kind == "company_snapshot":
            return self._run_company_snapshot(task)
        if task.kind == "news_snapshot":
            return self._run_news_snapshot(task)
        if task.kind == "filings_snapshot":
            return self._run_filings_snapshot(task)
        if task.kind == "portfolio_snapshot":
            return self._run_portfolio_snapshot(task)
        if task.kind == "thematic_snapshot":
            return self._run_thematic_snapshot(task)
        return self._run_web_snapshot(task)

    @staticmethod
    def _tool_output(tool: Any, payload: dict[str, Any]) -> Any:
        return tool.invoke(payload)

    def _run_company_snapshot(self, task: PlannedTask) -> TaskResult:
        company_id = task.params["company_id"]
        company = self._load_company(company_id)
        financials = self._tool_output(get_latest_financials, {"company_id": company_id, "periods": 4})
        ratios = self._tool_output(calculate_ratios, {"company_id": company_id})
        risk_flags = self._tool_output(detect_risk_flags, {"company_id": company_id})
        payload = {
            "company": company,
            "financials": financials,
            "ratios": ratios,
            "risk_flags": risk_flags,
        }
        return TaskResult(
            name=task.name,
            kind=task.kind,
            payload=payload,
            source={"name": task.name, "kind": task.kind, "company_id": company_id, "status": "ok"},
        )

    def _run_news_snapshot(self, task: PlannedTask) -> TaskResult:
        company_id = task.params["company_id"]
        payload = self._tool_output(get_recent_news, {"company_id": company_id, "days": 30, "limit": 8})
        return TaskResult(
            name=task.name,
            kind=task.kind,
            payload=payload,
            source={"name": task.name, "kind": task.kind, "company_id": company_id, "status": "ok"},
        )

    def _run_filings_snapshot(self, task: PlannedTask) -> TaskResult:
        if "upload_id" in task.params:
            payload = self._tool_output(
                search_user_upload,
                {
                    "user_id": task.params["user_id"],
                    "upload_id": task.params["upload_id"],
                    "query": task.params["query"],
                    "limit": 8,
                },
            )
            source = {"name": task.name, "kind": task.kind, "upload_id": task.params["upload_id"], "status": "ok"}
        else:
            company_id = task.params["company_id"]
            payload = self._tool_output(
                search_filings,
                {
                    "company_id": company_id,
                    "query": task.params["query"],
                    "limit": 8,
                },
            )
            source = {"name": task.name, "kind": task.kind, "company_id": company_id, "status": "ok"}
        return TaskResult(name=task.name, kind=task.kind, payload=payload, source=source)

    @staticmethod
    def _load_company(company_id: str) -> dict[str, Any]:
        db = next(get_db())
        try:
            company = db.query(Company).filter(Company.id == UUID(company_id)).first()
            if not company:
                return {"error": f"Company not found for id {company_id}"}
            return {
                "company_id": str(company.id),
                "name": company.name,
                "ticker_nse": company.ticker_nse,
                "ticker_bse": company.ticker_bse,
                "sector": company.sector,
                "industry": company.industry,
            }
        finally:
            db.close()

    def _run_portfolio_snapshot(self, task: PlannedTask) -> TaskResult:
        portfolio_id = task.params["portfolio_id"]
        holdings = self._tool_output(get_portfolio_holdings, {"portfolio_id": portfolio_id})
        metrics = self._tool_output(calculate_portfolio_metrics, {"portfolio_id": portfolio_id})
        payload = {"holdings": holdings, "metrics": metrics}
        return TaskResult(
            name=task.name,
            kind=task.kind,
            payload=payload,
            source={"name": task.name, "kind": task.kind, "portfolio_id": portfolio_id, "status": "ok"},
        )

    def _run_thematic_snapshot(self, task: PlannedTask) -> TaskResult:
        payload = self._tool_output(thematic_discovery_search, {"query": task.params["query"], "limit": 10})
        return TaskResult(
            name=task.name,
            kind=task.kind,
            payload=payload,
            source={"name": task.name, "kind": task.kind, "status": "ok"},
        )

    def _run_web_snapshot(self, task: PlannedTask) -> TaskResult:
        payload = self._tool_output(internet_search, {"query": task.params["query"]})
        return TaskResult(
            name=task.name,
            kind=task.kind,
            payload=payload,
            source={"name": task.name, "kind": task.kind, "status": "ok"},
        )


class ResultAggregator:
    """Merge worker results into a bounded synthesis prompt."""

    def build_prompt(self, query: str, tasks: list[PlannedTask], results: list[TaskResult]) -> str:
        return self.build_prompt_with_context(query=query, tasks=tasks, results=results, context_note=None)

    def build_prompt_with_context(
        self,
        query: str,
        tasks: list[PlannedTask],
        results: list[TaskResult],
        context_note: Optional[str],
    ) -> str:
        evidence_sections = []
        for result in results:
            section = self._format_result(result)
            if section:
                evidence_sections.append(section)

        evidence_blob = "\n\n".join(evidence_sections)
        evidence_blob = self._truncate(evidence_blob, 7000)

        task_list = ", ".join(task.name for task in tasks)
        context_block = ""
        if context_note:
            context_block = f"\n\nConversation context:\n{self._truncate(context_note, 2000)}"
        return (
            "You are synthesizing a research answer from pre-collected evidence. "
            "Do not invent facts that are not present in the evidence. "
            "If the evidence is insufficient, say so clearly.\n\n"
            f"User request:\n{query}\n\n"
            f"{context_block}"
            f"Planned tasks: {task_list}\n\n"
            f"Evidence:\n{evidence_blob}\n\n"
            "Write a concise, decision-ready answer."
        )

    def build_sources(self, results: list[TaskResult]) -> list[dict[str, Any]]:
        return [result.source for result in results]

    def _format_result(self, result: TaskResult) -> str:
        payload_text = self._render_payload(result.payload)
        if not payload_text:
            return ""
        return self._truncate(f"## {result.name}\n{payload_text}", 2200)

    def _render_payload(self, payload: Any) -> str:
        try:
            return json.dumps(payload, indent=2, default=str, ensure_ascii=True)
        except TypeError:
            return str(payload)

    @staticmethod
    def _truncate(text: str, limit: int) -> str:
        if len(text) <= limit:
            return text
        return text[: limit - 20] + "\n... [truncated]"


class ResearchPipeline:
    """High-level planner/worker/aggregator pipeline for chat queries."""

    def __init__(self) -> None:
        settings = get_settings()
        self.planner = ResearchPlanner()
        self.worker_pool = ResearchWorkerPool(settings.chat_worker_pool_size)
        self.aggregator = ResultAggregator()

    def run(
        self,
        query: str,
        user_id: UUID,
        company_id: Optional[UUID],
        upload_id: Optional[UUID],
        primary_portfolio_id: Optional[UUID],
        session_id: UUID,
        context_note: Optional[str] = None,
    ) -> dict[str, Any]:
        tasks = self.planner.plan(
            query=query,
            user_id=user_id,
            company_id=company_id,
            upload_id=upload_id,
            primary_portfolio_id=primary_portfolio_id,
        )

        logger.info("Planned %s research tasks for session %s", len(tasks), session_id)
        results = self.worker_pool.run(tasks)
        prompt = self.aggregator.build_prompt_with_context(
            query=query,
            tasks=tasks,
            results=results,
            context_note=context_note,
        )

        result = invoke_research_agent(
            {"messages": [{"role": "user", "content": prompt}]},
            {"configurable": {"thread_id": str(session_id)}},
        )

        response_text = result["messages"][-1].content
        tokens_used = 0
        if hasattr(result["messages"][-1], "response_metadata"):
            tokens_used = (
                result["messages"][-1]
                .response_metadata.get("token_usage", {})
                .get("total_tokens", 0)
            )

        return {
            "response": response_text,
            "tokens_used": tokens_used,
            "sources": self.aggregator.build_sources(results),
            "data_sources": [
                {
                    "name": "Planner-driven research pipeline",
                    "url": f"/chat/sessions/{session_id}",
                    "data_type": "ai_response",
                }
            ],
            "visualizations": [],
        }