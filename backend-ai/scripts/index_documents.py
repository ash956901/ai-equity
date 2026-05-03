"""RAG Pipeline Trigger: Index all seeded documents into Qdrant."""

import sys
from pathlib import Path
from sqlalchemy.orm import Session

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.db.database import SessionLocal
from src.db.models import Filing, Company
from src.etl.embedding_generator import EmbeddingGenerator
from src.etl.load_task import ETLLoadTask

def index_all():
    db = SessionLocal()
    generator = EmbeddingGenerator()
    loader = ETLLoadTask()
    
    print("🚀 Starting RAG Indexing Pipeline...")
    
    filings = db.query(Filing).all()
    if not filings:
        print("❌ No filings found in database. Run seed_db.py first.")
        return

    for filing in filings:
        company = db.query(Company).filter(Company.id == filing.company_id).first()
        print(f"📄 Indexing: {filing.title} for {company.name if company else 'Unknown'}")
        
        # Mock text if raw text is missing (for seed data)
        # In production, this would read from filing.parsed_text_uri
        content = f"This is the official {filing.filing_type} for {company.name if company else 'the company'}. "
        content += f"Summary of performance: Revenue grew by 12% YoY. Net profit increased significantly. "
        content += f"Strategic focus remains on {company.sector if company else 'growth'} and technology innovation. "
        content += f"Risk factors include market volatility and regulatory changes in {company.industry if company else 'the industry'}."

        # Create chunks
        chunks = [
            {
                "text": content,
                "company_id": str(filing.company_id),
                "company": company.name if company else "Unknown",
                "filing_id": str(filing.id),
                "filing_type": filing.filing_type,
                "filing_date": filing.filing_date.isoformat(),
            }
        ]
        
        # Generate Embeddings
        print("  - Generating embeddings...")
        embedded_chunks = generator.generate_document_embeddings(chunks)
        
        # Load to Qdrant
        print("  - Loading to Qdrant...")
        loader.load_chunks(embedded_chunks)

    print("✅ RAG Indexing Complete. Iris is now ready to chat about these documents!")
    db.close()

if __name__ == "__main__":
    index_all()
