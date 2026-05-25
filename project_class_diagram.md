# EquityAI Class Diagrams (PlantUML & Mermaid)

This document contains full class definitions and relationship diagrams for **EquityAI**. The codes are designed to be copied directly into online rendering tools.

*   **PlantUML Renderers**: [PlantText](https://www.planttext.com/) or [PlantUML Online Server](https://www.plantuml.com/plantuml/).
*   **Mermaid Renderers**: [Mermaid Live Editor](https://mermaid.live/).

---

## 1. PlantUML Class Diagram Code

Copy the code block below and paste it into [PlantText](https://www.planttext.com/) to generate the diagrams.

```plantuml
@startuml
skinparam style strictuml
skinparam BoxPadding 10
skinparam ParticipantPadding 10
skinparam NoteBackgroundColor #FEFECE
skinparam NoteBorderColor #A2A2A2

package "Domain Layer (SQLAlchemy Models)" {
    class User {
        +UUID id
        +String email
        +String username
        +String password_hash
        +String full_name
        +String risk_tolerance
        +String investment_horizon
        +Boolean is_active
        +DateTime created_at
    }

    class Portfolio {
        +UUID id
        +UUID user_id
        +String name
        +String description
        +String broker
        +Boolean is_primary
        +DateTime created_at
        +calculate_metrics()
    }

    class Holding {
        +UUID id
        +UUID portfolio_id
        +UUID company_id
        +Decimal quantity
        +Decimal average_price
        +Decimal current_price
        +String currency
        +DateTime last_updated
    }

    class Company {
        +UUID id
        +String ticker_nse
        +String ticker_bse
        +String name
        +String sector
        +String industry
        +Text description
        +Boolean is_active
    }

    class Filing {
        +UUID id
        +UUID company_id
        +String filing_type
        +String fiscal_year
        +String document_path
        +DateTime published_date
    }

    class DocumentChunk {
        +UUID id
        +UUID filing_id
        +Text text
        +String section
        +Integer start_position
        +Integer end_position
    }

    class CommodityPrice {
        +UUID id
        +String symbol
        +String name
        +Decimal price
        +DateTime timestamp
    }

    class GeopoliticalEvent {
        +UUID id
        +String title
        +String category
        +String country
        +Float confidence
        +DateTime event_date
    }

    class SectorExposure {
        +UUID id
        +String sector
        +String commodity
        +String impact_direction
        +Boolean is_active
    }

    class CausalInsight {
        +UUID id
        +UUID portfolio_id
        +UUID company_id
        +String title
        +String trigger_event
        +String commodity
        +String impact_direction
        +Text explanation
        +Text recommendation
        +Float confidence
        +DateTime generated_at
    }
}

package "Application Services" {
    class PortfolioService {
        -Session db
        +__init__(Session db)
        +get_primary_portfolio(UUID user_id) : UUID
        +get_holdings(UUID portfolio_id) : List[Dict]
        +calculate_metrics(UUID portfolio_id) : Dict
    }

    class CausalService {
        -Session db
        +__init__(Session db)
        +get_commodity_changes(Integer days) : Dict
        +get_recent_volatile_commodities(Float threshold) : List[Dict]
        +analyze_portfolio(UUID portfolio_id) : List[Dict]
        +save_insights(UUID portfolio_id, List[Dict] insights) : List[CausalInsight]
    }
}

package "ETL & Ingestion Pipeline" {
    class DocumentProcessor {
        +process_document(String file_path) : Dict
    }

    class TextCleaner {
        +clean_text(String text) : String
        +normalize_text(String text) : String
    }

    class SemanticChunker {
        -Integer chunk_size
        -Integer overlap
        +__init__(Integer chunk_size, Integer overlap)
        +chunk_text(String text, Dict metadata) : List[Dict]
        -_create_chunks(String text, String section) : List[Dict]
    }

    class EmbeddingGenerator {
        -String model_name
        +__init__(String model_name)
        +generate_embeddings(List[String] texts) : List[List[Float]]
        +generate_document_embeddings(List[Dict] chunks) : List[Dict]
    }

    class ETLTransformTask {
        -DocumentProcessor doc_proc
        -TextCleaner cleaner
        -SemanticChunker chunker
        -EmbeddingGenerator embedder
        +process_filing(String file_path, Dict metadata) : Dict
    }
}

package "Agentic Intelligence (Iris Orchestration)" {
    class Orchestrator {
        +build_research_agent() : DeepAgent
        -_get_model_string() : String
        -_get_model_kwargs() : Dict
    }

    interface DeepAgent {
        +tools: List[Function]
        +system_prompt: String
        +subagents: Dict[String, SubAgent]
        +memory: Dict
        +run(String prompt) : Object
    }
}

' Relationships & Associations
User "1" *-- "0..*" Portfolio : owns
Portfolio "1" *-- "0..*" Holding : contains
Company "1" *-- "0..*" Holding : referenced_by
Company "1" *-- "0..*" Filing : reports
Filing "1" *-- "0..*" DocumentChunk : segmented_into

PortfolioService ..> Portfolio : reads & calculates
PortfolioService ..> Holding : reads

CausalService ..> CommodityPrice : queries
CausalService ..> SectorExposure : evaluates
CausalService ..> CausalInsight : generates
CausalService ..> Holding : inspects

ETLTransformTask *-- DocumentProcessor
ETLTransformTask *-- TextCleaner
ETLTransformTask *-- SemanticChunker
ETLTransformTask *-- EmbeddingGenerator

Orchestrator ..> DeepAgent : compiles
Orchestrator ..> PortfolioService : consumes
Orchestrator ..> CausalService : consumes

@endum
```

---

## 2. Mermaid Class Diagram Code

Copy the code block below and paste it into the [Mermaid Live Editor](https://mermaid.live/) to render or compile dynamically.

```mermaid
classDiagram
    %% Relationship Definitions
    User "1" --* "0..*" Portfolio : owns
    Portfolio "1" --* "0..*" Holding : contains
    Company "1" --* "0..*" Holding : referenced_by
    Company "1" --* "0..*" Filing : reports
    Filing "1" --* "0..*" DocumentChunk : segmented_into
    
    PortfolioService ..> Portfolio : inspects
    CausalService ..> CommodityPrice : queries
    CausalService ..> SectorExposure : evaluates
    CausalService ..> CausalInsight : generates
    
    ETLTransformTask *-- DocumentProcessor : uses
    ETLTransformTask *-- TextCleaner : uses
    ETLTransformTask *-- SemanticChunker : uses
    ETLTransformTask *-- EmbeddingGenerator : uses
    
    Orchestrator ..> DeepAgent : compiles

    class User {
        +UUID id
        +String email
        +String username
        +String password_hash
        +String full_name
        +String risk_tolerance
        +Boolean is_active
        +DateTime created_at
    }

    class Portfolio {
        +UUID id
        +UUID user_id
        +String name
        +String broker
        +Boolean is_primary
        +DateTime created_at
    }

    class Holding {
        +UUID id
        +UUID portfolio_id
        +UUID company_id
        +Decimal quantity
        +Decimal average_price
        +Decimal current_price
        +DateTime last_updated
    }

    class Company {
        +UUID id
        +String ticker_nse
        +String name
        +String sector
        +String industry
    }

    class Filing {
        +UUID id
        +UUID company_id
        +String filing_type
        +String document_path
        +DateTime published_date
    }

    class DocumentChunk {
        +UUID id
        +UUID filing_id
        +Text text
        +String section
        +Integer start_position
        +Integer end_position
    }

    class CommodityPrice {
        +UUID id
        +String symbol
        +String name
        +Decimal price
        +DateTime timestamp
    }

    class SectorExposure {
        +UUID id
        +String sector
        +String commodity
        +String impact_direction
        +Boolean is_active
    }

    class CausalInsight {
        +UUID id
        +UUID portfolio_id
        +UUID company_id
        +String title
        +String trigger_event
        +String commodity
        +String impact_direction
        +Text explanation
        +Float confidence
    }

    class PortfolioService {
        -Session db
        +get_primary_portfolio(user_id) UUID
        +get_holdings(portfolio_id) List
        +calculate_metrics(portfolio_id) Dict
    }

    class CausalService {
        -Session db
        +get_commodity_changes(days) Dict
        +analyze_portfolio(portfolio_id) List
        +save_insights(portfolio_id, insights) List
    }

    class ETLTransformTask {
        -DocumentProcessor doc_proc
        -TextCleaner cleaner
        -SemanticChunker chunker
        -EmbeddingGenerator embedder
        +process_filing(file_path, metadata) Dict
    }

    class Orchestrator {
        +build_research_agent() DeepAgent
    }

    class DeepAgent {
        <<interface>>
        +tools: List
        +system_prompt: String
        +subagents: Dict
        +memory: Dict
    }
```

---

## 3. Structural Design Patterns Employed

For the technical writing portion of your report, here are the architectural patterns demonstrated by the class design above:

1.  **Repository/Active Record - Domain Layer Separation**: SQLAlchemy models (`User`, `Portfolio`, `Holding`, `Company`) represent pure data mappings. Services (`PortfolioService`, `CausalService`) encapsulate the operations performed on these entities. This keeps logic testable and prevents database operations from cluttering the models.
2.  **Factory Pattern (Orchestrator and LLM models)**: `Orchestrator` uses settings-driven logic to dynamically instantiate model configurations (Ollama vs. OpenAI vs. Groq vs. DeepSeek) and build `DeepAgent` graph instances without locking the application to a single LLM vendor.
3.  **Pipeline Processing Pattern (ETL Transformation)**: `ETLTransformTask` orchestrates a sequential processing chain:
    $$\text{Raw Document} \xrightarrow{\text{DocumentProcessor}} \text{Raw Text} \xrightarrow{\text{TextCleaner}} \text{Normalized Text} \xrightarrow{\text{SemanticChunker}} \text{Chunks} \xrightarrow{\text{EmbeddingGenerator}} \text{Vectors}$$
4.  **Facade/Service Layer**: Direct database queries are restricted behind service wrappers (`CausalService`, `PortfolioService`) which expose simple Python dictionary interfaces to the agent tools and API controllers, preventing deep coupling between SQLAlchemy sessions and the LangGraph orchestrator.
