import asyncio
import time
import uuid
import sys
import os
from sqlalchemy.orm import Session

# Add backend-ai to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.db.database import SessionLocal
from src.db.models import User, Portfolio
from src.domains.chat.service import ChatService

def setup_test_user(db: Session) -> uuid.UUID:
    # Use a fixed test user ID
    user_id = uuid.UUID('11111111-1111-1111-1111-111111111111')
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        user = User(id=user_id, email="testuser_e2e@example.com", expertise_level="advanced")
        db.add(user)
        db.commit()
    
    # Check for primary portfolio
    portfolio = db.query(Portfolio).filter(Portfolio.user_id == user_id, Portfolio.is_primary == True).first()
    if not portfolio:
        portfolio = Portfolio(id=uuid.uuid4(), user_id=user_id, name="Test Portfolio", is_primary=True)
        db.add(portfolio)
        db.commit()
        
    return user_id

def test_query(db: Session, chat_service: ChatService, user_id: uuid.UUID, query: str, name: str):
    print(f"\n{'='*50}")
    print(f"TESTING ROUTE: {name}")
    print(f"QUERY: '{query}'")
    print(f"{'='*50}")
    
    start_time = time.time()
    try:
        result = chat_service.process_query(
            user_id=user_id,
            query=query,
            expertise_level="advanced",
            session_id=None,
            upload_id=None
        )
        end_time = time.time()
        
        print(f"\nSUCCESS! Time taken: {end_time - start_time:.2f} seconds")
        print(f"Tokens Used: {result.get('tokens_used', 'N/A')}")
        print("\n--- RESPONSE HEAD ---")
        print(result['response'][:500] + ("..." if len(result['response']) > 500 else ""))
        print("---------------------")
        
    except Exception as e:
        end_time = time.time()
        print(f"\nFAILED! Time taken: {end_time - start_time:.2f} seconds")
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()

def run_tests():
    print("Starting E2E Tests for Redesigned Architecture...")
    db = SessionLocal()
    try:
        user_id = setup_test_user(db)
        chat_service = ChatService(db)
        
        # 1. Compare Route
        test_query(db, chat_service, user_id, "Compare TCS and Infosys", "COMPARE")
        
        # 2. Portfolio Route
        test_query(db, chat_service, user_id, "Show my portfolio suggestions", "PORTFOLIO")
        
        # 3. Causal Route
        test_query(db, chat_service, user_id, "What are the hidden patterns in the market?", "CAUSAL")
        
        # 4. General Route
        test_query(db, chat_service, user_id, "Tell me about Reliance Industries", "GENERAL")
        
    finally:
        db.close()

if __name__ == "__main__":
    run_tests()
