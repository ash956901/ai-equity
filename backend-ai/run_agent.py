import sys
import os
import uuid
import argparse

# Ensure src module is discoverable
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.agents.graph_builder import build_research_graph
from src.agents.state import ResearchState, QueryMode
from unittest.mock import patch


DEFAULT_PDF_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "data", "RIL-Integrated-Annual-Report-2024-25.pdf")
)
DEFAULT_QUERY = "What are the key financial highlights and revenue figures from the uploaded document?"

def extract_pdf_chunks(pdf_path, max_pages=10):
    try:
        import fitz  # PyMuPDF is much faster
        print("Using PyMuPDF for extraction...")
        doc = fitz.open(pdf_path)
        return [page.get_text() for idx, page in enumerate(doc) if idx < max_pages]
    except ImportError:
        try:
            print("PyMuPDF not found, falling back to PyPDFLoader...")
            from langchain_community.document_loaders import PyPDFLoader
            loader = PyPDFLoader(pdf_path)
            # This loads the entire document which is slow, but we can't easily lazily load
            # so we'll just slice it after. Ideally user has PyMuPDF.
            docs = loader.load_and_split()
            return [doc.page_content for doc in docs[:max_pages]]
        except ImportError:
            print("Please install PyMuPDF (fitz) or langchain-community")
            return []


def parse_args():
    parser = argparse.ArgumentParser(description="Run local PDF analysis through the research agent graph.")
    parser.add_argument(
        "--pdf",
        default=DEFAULT_PDF_PATH,
        help="Absolute or relative path to input PDF (defaults to Reliance annual report).",
    )
    parser.add_argument(
        "--query",
        default=DEFAULT_QUERY,
        help="User query to analyze against PDF content.",
    )
    parser.add_argument(
        "--expertise-level",
        default="intermediate",
        choices=["beginner", "intermediate", "advanced"],
        help="Controls explanation depth in synthesis output.",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=10,
        help="Maximum pages to extract from the PDF.",
    )
    return parser.parse_args()


def run():
    args = parse_args()
    pdf_path = os.path.abspath(args.pdf)
    if not os.path.exists(pdf_path):
        print(f"Error: PDF not found at {pdf_path}")
        return

    print("Extracting text from PDF...")
    chunks = extract_pdf_chunks(pdf_path, max_pages=max(1, args.max_pages))
    if not chunks:
        print("Failed to extract chunks")
        return
        
    print(f"Extracted {len(chunks)} pages/chunks from PDF.")

    # We will mock VectorService.search_user_upload to return the PDF chunks
    def mock_search_user_upload(*args, **kwargs):
        # We search the query over the chunks naively, or just return first 10 for simplicity
        query = kwargs.get("query", "").lower()
        scored_chunks = []
        for i, chunk in enumerate(chunks):
            # very naive matching: count query word occurrences
            score = sum(chunk.lower().count(word) for word in query.split())
            if score > 0:
                scored_chunks.append({"text": chunk, "score": float(score), "page_number": i+1})
        
        # Sort by score descending
        scored_chunks.sort(key=lambda x: x["score"], reverse=True)
        # Fallback to top chunks if no match
        if not scored_chunks:
            scored_chunks = [{"text": chunk, "score": 1.0, "page_number": p+1} for p, chunk in enumerate(chunks[:10])]
            
        return scored_chunks[:10]

    print("Building agent graph...")
    graph = build_research_graph()
    
    initial_state: ResearchState = {
        "user_id": uuid.uuid4(),
        "session_id": uuid.uuid4(),
        "upload_id": uuid.uuid4(),
        "user_query": args.query,
        "expertise_level": args.expertise_level,
        "query_mode": QueryMode.DOC_UPLOAD,
    }

    print(f"Running agent with query: '{args.query}'...")
    with patch("src.agents.doc_insight_agent.VectorService.search_user_upload", side_effect=mock_search_user_upload):
        final_state = graph.invoke(initial_state)

    print("\n" + "="*50)
    print("AGENT RESPONSE:")
    print("="*50)
    print(final_state.get("final_response", "No response generated."))
    print("\nSources used:")
    for source in final_state.get("sources", []):
        print(f" - {source}")

    print("\nExecution plan:")
    print(final_state.get("agent_execution_plan", []))

    print("\nAgent call log:")
    for row in final_state.get("agent_call_log", []):
        print(f" - {row}")

    print("\nTool call log:")
    for row in final_state.get("tool_call_log", []):
        print(f" - {row}")

if __name__ == "__main__":
    run()
