# Cloud Deployment & Asynchronicity Strategy – AI Equity Research Platform

## Overview

This document defines the **cloud infrastructure, deployment architecture, and asynchronous processing strategy** for the AI equity research platform, including cloud provider selection, storage, compute, background workers, and near-time query handling.

---

## Cloud Provider Decision: AWS

### Comparison: AWS vs Azure

| Criterion | AWS | Azure |
|-----------|-----|-------|
| **Postgres (managed)** | RDS PostgreSQL | Azure Database for PostgreSQL |
| **Object storage** | S3 (industry standard) | Blob Storage |
| **Container orchestration** | ECS/EKS | AKS |
| **Serverless functions** | Lambda | Azure Functions |
| **Message queue** | SQS | Service Bus |
| **Redis (managed)** | ElastiCache | Azure Cache for Redis |
| **Monitoring** | CloudWatch | Azure Monitor |
| **Cost (typical)** | Lower for storage, compute | Competitive, better for MS stack |
| **Ecosystem maturity** | More mature, larger community | Growing rapidly |
| **Student credits** | AWS Educate | Azure for Students |

### Recommendation: **AWS**

**Reasoning:**

1. **Ecosystem maturity**: Larger community, more third-party integrations, extensive documentation.
2. **S3 dominance**: Industry-standard object storage; better tooling and SDKs.
3. **Cost efficiency**: S3 storage costs are lower; EC2 spot instances for batch jobs.
4. **Flexibility**: ECS/EKS for containers, Lambda for serverless, SQS for queues – all well-integrated.
5. **Student-friendly**: AWS Educate provides credits and learning resources.

**Trade-off accepted**: Slightly steeper learning curve initially, but better long-term scalability.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         AWS Cloud                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    API Layer (FastAPI)                    │   │
│  │  - EC2 / ECS (Fargate) / App Runner                       │   │
│  │  - Application Load Balancer (ALB)                        │   │
│  │  - Auto-scaling based on CPU/memory                       │   │
│  └────────────────────┬─────────────────────────────────────┘   │
│                       │                                           │
│  ┌────────────────────┼──────────────────────────────────────┐  │
│  │                    ▼                                       │  │
│  │  ┌──────────────────────────────────────────────────┐     │  │
│  │  │         Data Layer                                │     │  │
│  │  │  - RDS PostgreSQL (Multi-AZ)                      │     │  │
│  │  │  - ElastiCache Redis (for sessions/cache)         │     │  │
│  │  │  - S3 (raw docs, parsed JSON, charts)             │     │  │
│  │  │  - Qdrant (self-hosted on EC2 or cloud-managed)   │     │  │
│  │  └──────────────────────────────────────────────────┘     │  │
│  │                                                             │  │
│  │  ┌──────────────────────────────────────────────────┐     │  │
│  │  │      Background Workers (Celery/Arq)             │     │  │
│  │  │  - ECS Tasks / EC2 Spot Instances                 │     │  │
│  │  │  - SQS as message broker                          │     │  │
│  │  │  - Auto-scaling based on queue depth              │     │  │
│  │  └──────────────────────────────────────────────────┘     │  │
│  │                                                             │  │
│  │  ┌──────────────────────────────────────────────────┐     │  │
│  │  │      Scheduled Jobs (Cron)                        │     │  │
│  │  │  - EventBridge (CloudWatch Events)                │     │  │
│  │  │  - Lambda for lightweight triggers                │     │  │
│  │  └──────────────────────────────────────────────────┘     │  │
│  └─────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │              Monitoring & Logging                         │ │
│  │  - CloudWatch Logs & Metrics                              │ │
│  │  - X-Ray (distributed tracing)                            │ │
│  │  - CloudWatch Alarms                                      │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Component Specifications

### 1. Compute (FastAPI Backend)

#### Option A: ECS Fargate (Recommended for MVP)

**Pros:**
- Serverless containers (no EC2 management)
- Auto-scaling built-in
- Pay only for what you use
- Easy CI/CD with ECR

**Cons:**
- Slightly more expensive than EC2
- Cold start latency (minimal for long-running services)

**Configuration:**
```yaml
# ECS Task Definition
Task:
  CPU: 1024 (1 vCPU)
  Memory: 2048 MB
  Container:
    Image: {account}.dkr.ecr.{region}.amazonaws.com/equity-research-api:latest
    Port: 8000
    Environment:
      - DATABASE_URL
      - REDIS_URL
      - S3_BUCKET
      - QDRANT_URL
      - OPENAI_API_KEY
    HealthCheck:
      Command: ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"]
      Interval: 30s
      Timeout: 5s
      Retries: 3

Service:
  DesiredCount: 2  # Start with 2 tasks
  LoadBalancer: ALB
  AutoScaling:
    MinTasks: 2
    MaxTasks: 10
    TargetCPUUtilization: 70%
    TargetMemoryUtilization: 80%
```

#### Option B: EC2 with Docker (For cost optimization later)

**Setup:**
- t3.medium instances (2 vCPU, 4 GB RAM)
- Auto Scaling Group (ASG) with target tracking
- Application Load Balancer (ALB)
- Docker Compose or Kubernetes (EKS)

### 2. Database (PostgreSQL)

#### RDS PostgreSQL Configuration

```yaml
Instance:
  Class: db.t3.medium  # Start small, scale up
  Engine: PostgreSQL 15
  Storage: 100 GB gp3 (General Purpose SSD)
  StorageAutoscaling: true (up to 500 GB)
  MultiAZ: true  # High availability
  BackupRetention: 7 days
  EncryptionAtRest: true

Performance:
  MaxConnections: 200
  SharedBuffers: 1 GB
  EffectiveCacheSize: 3 GB
  WorkMem: 16 MB

Monitoring:
  EnhancedMonitoring: true (60s granularity)
  PerformanceInsights: true
```

**Cost optimization:**
- Use read replicas for analytics queries (later)
- Enable query performance insights to optimize slow queries
- Consider Aurora Serverless for variable workloads (later)

### 3. Object Storage (S3)

#### Bucket Structure

```
equity-research-platform/
├── raw/
│   ├── nse/
│   │   └── {company_id}/{filing_id}.pdf
│   ├── bse/
│   │   └── {company_id}/{filing_id}.pdf
│   ├── ir/
│   │   └── {company_id}/{document_hash}.{ext}
│   └── uploads/
│       └── {user_id}/{upload_id}.{ext}
├── parsed/
│   └── {company_id}/{filing_id}.json
├── charts/
│   └── {company_id}/{filing_id}/{chart_id}.png
└── exports/
    └── {user_id}/{export_id}.{ext}
```

#### S3 Configuration

```yaml
Bucket: equity-research-platform
Region: ap-south-1  # Mumbai (for India focus)
Versioning: Enabled
Encryption: AES-256 (SSE-S3)
LifecycleRules:
  - Id: archive-old-raw-docs
    Prefix: raw/
    Transitions:
      - Days: 90
        StorageClass: INTELLIGENT_TIERING
      - Days: 365
        StorageClass: GLACIER
  - Id: delete-old-parsed
    Prefix: parsed/
    Expiration:
      Days: 730  # Keep parsed JSON for 2 years
  - Id: delete-old-uploads
    Prefix: raw/uploads/
    Expiration:
      Days: 90  # User uploads expire after 90 days

PublicAccessBlock: Enabled (all blocked)
CORS: Enabled (for pre-signed URLs)
```

**Access pattern:**
- Use **pre-signed URLs** for secure temporary access
- Use **S3 Transfer Acceleration** for faster uploads (if needed)
- Use **CloudFront CDN** for frequently accessed charts (later)

### 4. Cache (Redis)

#### ElastiCache Redis Configuration

```yaml
NodeType: cache.t3.medium  # 3.09 GB memory
Engine: Redis 7.0
ClusterMode: Disabled (single shard for simplicity)
Replicas: 1 (for high availability)
AutomaticFailover: Enabled
EncryptionInTransit: true
EncryptionAtRest: true

Use Cases:
  - Session storage (TTL: 1 hour)
  - Chat memory cache (TTL: 1 hour)
  - Frequent query results cache (TTL: 5 minutes)
  - Rate limiting counters
  - Celery broker (if using Celery)
```

**Alternative:** Use Redis on EC2 with persistence if cost is a concern.

### 5. Vector Database (Qdrant)

#### Option A: Self-Hosted on EC2 (Recommended for control)

```yaml
Instance: t3.large (2 vCPU, 8 GB RAM)
Storage: 500 GB gp3 SSD (for 1M+ vectors)
Docker: qdrant/qdrant:latest

Volumes:
  - /data/qdrant:/qdrant/storage

Configuration:
  service:
    http_port: 6333
    grpc_port: 6334
  storage:
    storage_path: /qdrant/storage
    snapshots_path: /qdrant/snapshots
  optimizers:
    indexing_threshold: 20000
    max_segment_size: 200000
```

**Backup strategy:**
- Daily snapshots to S3 via cron job
- Use Qdrant's built-in snapshot API

#### Option B: Qdrant Cloud (Managed)

**Pros:**
- Fully managed, no ops overhead
- Automatic backups and scaling
- Built-in monitoring

**Cons:**
- Higher cost (~$50-200/month depending on size)
- Less control over configuration

**Recommendation:** Start with self-hosted EC2 for cost control; migrate to Qdrant Cloud if ops burden becomes high.

---

## Background Worker Architecture

### Technology Choice: Celery with SQS

**Why Celery:**
- Mature, battle-tested
- Rich ecosystem (flower for monitoring, celery-beat for scheduling)
- Supports multiple brokers (Redis, SQS, RabbitMQ)
- Retry logic, task chaining, rate limiting built-in

**Why SQS as broker:**
- Fully managed, no infrastructure to maintain
- Scales automatically
- Pay-per-request pricing (very cheap)
- Integrates well with Celery via `kombu`

### Worker Configuration

```python
# celery_config.py
from celery import Celery
from kombu import Queue

app = Celery('equity_research')

app.conf.update(
    broker_url='sqs://',  # Uses boto3 credentials
    broker_transport_options={
        'region': 'ap-south-1',
        'queue_name_prefix': 'equity-research-'
    },
    result_backend='redis://elasticache-endpoint:6379/0',
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Asia/Kolkata',
    enable_utc=True,
    
    # Task routing
    task_routes={
        'app.etl.crawlers.*': {'queue': 'crawlers'},
        'app.etl.parsers.*': {'queue': 'parsers'},
        'app.etl.embeddings.*': {'queue': 'embeddings'},
        'app.etl.news.*': {'queue': 'news'},
    },
    
    # Task settings
    task_acks_late=True,  # Acknowledge after task completion
    task_reject_on_worker_lost=True,
    task_time_limit=3600,  # 1 hour max per task
    task_soft_time_limit=3300,  # 55 minutes soft limit
    
    # Retry settings
    task_autoretry_for=(Exception,),
    task_retry_kwargs={'max_retries': 3, 'countdown': 60},
    
    # Concurrency
    worker_prefetch_multiplier=4,
    worker_max_tasks_per_child=1000,  # Restart worker after 1000 tasks
)

# Define queues
app.conf.task_queues = (
    Queue('crawlers', routing_key='crawlers'),
    Queue('parsers', routing_key='parsers'),
    Queue('embeddings', routing_key='embeddings'),
    Queue('news', routing_key='news'),
    Queue('default', routing_key='default'),
)
```

### Worker Deployment (ECS Tasks)

```yaml
# ECS Task Definition for Workers
WorkerTask:
  CPU: 2048 (2 vCPU)
  Memory: 4096 MB
  Container:
    Image: {account}.dkr.ecr.{region}.amazonaws.com/equity-research-worker:latest
    Command: ["celery", "-A", "app.celery_app", "worker", "-Q", "crawlers,parsers", "-c", "4"]
    Environment:
      - DATABASE_URL
      - REDIS_URL
      - S3_BUCKET
      - QDRANT_URL
      - AWS_REGION
    LogConfiguration:
      LogDriver: awslogs
      Options:
        awslogs-group: /ecs/equity-research-workers
        awslogs-region: ap-south-1
        awslogs-stream-prefix: worker

Service:
  DesiredCount: 2  # Start with 2 workers
  AutoScaling:
    MinTasks: 1
    MaxTasks: 10
    ScaleOnQueueDepth:
      TargetValue: 100  # Scale up if queue depth > 100 messages
      ScaleInCooldown: 300
      ScaleOutCooldown: 60
```

**Cost optimization:**
- Use **EC2 Spot Instances** for workers (up to 90% cost savings)
- Configure spot instance interruption handling (graceful shutdown)

### Separate Worker Pools

```bash
# Crawler workers (I/O heavy)
celery -A app.celery_app worker -Q crawlers -c 8 --max-tasks-per-child=100

# Parser workers (CPU heavy)
celery -A app.celery_app worker -Q parsers -c 4 --max-tasks-per-child=50

# Embedding workers (API call heavy)
celery -A app.celery_app worker -Q embeddings -c 10 --max-tasks-per-child=200

# News workers (mixed)
celery -A app.celery_app worker -Q news -c 6 --max-tasks-per-child=100
```

---

## Scheduled Jobs (Cron)

### EventBridge (CloudWatch Events)

```yaml
Rules:
  - Name: daily-nse-filings-crawl
    Schedule: cron(0 18 * * ? *)  # 6 PM IST daily (after market close)
    Target:
      ECSTask:
        TaskDefinition: equity-research-worker
        Command: ["python", "-m", "app.etl.crawlers.nse_crawler", "--full"]
  
  - Name: daily-bse-filings-crawl
    Schedule: cron(30 18 * * ? *)  # 6:30 PM IST daily
    Target:
      ECSTask:
        TaskDefinition: equity-research-worker
        Command: ["python", "-m", "app.etl.crawlers.bse_crawler", "--full"]
  
  - Name: hourly-news-fetch
    Schedule: rate(1 hour)
    Target:
      Lambda:
        FunctionName: trigger-news-fetch
        Payload: {"portfolio_companies": true}
  
  - Name: weekly-ir-crawl
    Schedule: cron(0 2 ? * SUN *)  # 2 AM IST every Sunday
    Target:
      ECSTask:
        TaskDefinition: equity-research-worker
        Command: ["python", "-m", "app.etl.crawlers.ir_crawler", "--all"]
  
  - Name: weekly-theme-tagging
    Schedule: cron(0 3 ? * SUN *)  # 3 AM IST every Sunday
    Target:
      ECSTask:
        TaskDefinition: equity-research-worker
        Command: ["python", "-m", "app.etl.theme_tagger", "--incremental"]
```

### Celery Beat (Alternative)

```python
# celerybeat_schedule.py
from celery.schedules import crontab

app.conf.beat_schedule = {
    'daily-nse-crawl': {
        'task': 'app.etl.crawlers.crawl_nse_filings',
        'schedule': crontab(hour=18, minute=0),  # 6 PM IST
    },
    'hourly-news-fetch': {
        'task': 'app.etl.news.fetch_all_news',
        'schedule': crontab(minute=0),  # Every hour
    },
    'weekly-ir-crawl': {
        'task': 'app.etl.crawlers.crawl_all_ir_pages',
        'schedule': crontab(day_of_week='sunday', hour=2, minute=0),
    },
}
```

---

## Near-Time Query Handling

### Challenge

User queries need **near-real-time responses** (~1-3 seconds), but heavy ingestion work (crawling, parsing, embedding) runs **asynchronously** in the background.

### Solution: Hybrid Architecture

#### 1. Pre-Computed Data Layer

```python
# Most queries read from pre-computed tables
@app.get("/api/company/{company_id}/analysis")
async def get_company_analysis(company_id: UUID):
    """
    Fast path: Read from pre-computed tables.
    """
    # Read from financial_ratios (pre-computed)
    ratios = db.query(FinancialRatios).filter_by(
        company_id=company_id
    ).order_by(FinancialRatios.period_end.desc()).first()
    
    # Read from company_themes (pre-computed)
    themes = db.query(CompanyTheme).filter_by(
        company_id=company_id,
        is_active=True
    ).all()
    
    # Read from cached metrics (Redis)
    cached_metrics = redis_client.get(f"company:{company_id}:metrics")
    if cached_metrics:
        return json.loads(cached_metrics)
    
    # If not cached, compute and cache
    metrics = compute_company_metrics(company_id, ratios, themes)
    redis_client.setex(
        f"company:{company_id}:metrics",
        300,  # 5 minutes TTL
        json.dumps(metrics)
    )
    
    return metrics
```

#### 2. On-Demand Refresh API

```python
@app.post("/api/company/{company_id}/refresh")
async def trigger_company_refresh(company_id: UUID, background_tasks: BackgroundTasks):
    """
    Trigger on-demand refresh for a company.
    Returns immediately with task ID; client polls for status.
    """
    # Queue refresh task
    task = refresh_company_data.delay(company_id)
    
    # Store task ID in Redis for status tracking
    redis_client.setex(
        f"refresh:{company_id}:task_id",
        3600,  # 1 hour TTL
        task.id
    )
    
    return {
        "task_id": task.id,
        "status": "queued",
        "status_url": f"/api/tasks/{task.id}/status"
    }

@app.get("/api/tasks/{task_id}/status")
async def get_task_status(task_id: str):
    """
    Poll task status.
    """
    from celery.result import AsyncResult
    
    result = AsyncResult(task_id, app=celery_app)
    
    return {
        "task_id": task_id,
        "status": result.state,  # PENDING, STARTED, SUCCESS, FAILURE
        "progress": result.info.get('progress') if result.info else None,
        "result": result.result if result.successful() else None,
        "error": str(result.info) if result.failed() else None
    }
```

#### 3. Streaming Responses (WebSocket)

```python
from fastapi import WebSocket

@app.websocket("/ws/query")
async def websocket_query(websocket: WebSocket):
    """
    Stream agent graph execution in real-time.
    """
    await websocket.accept()
    
    try:
        # Receive query
        data = await websocket.receive_json()
        query = data['query']
        user_id = data['user_id']
        
        # Initialize state
        state = ResearchState(
            user_id=user_id,
            session_id=uuid.uuid4(),
            user_query=query,
            expertise_level='intermediate'
        )
        
        # Stream graph execution
        async for event in research_graph.astream(state):
            await websocket.send_json({
                "type": "node_complete",
                "node": event['node'],
                "data": event['data']
            })
        
        # Send final response
        await websocket.send_json({
            "type": "final_response",
            "response": state['final_response']
        })
    
    except Exception as e:
        await websocket.send_json({"type": "error", "message": str(e)})
    finally:
        await websocket.close()
```

#### 4. Caching Strategy

```python
# Multi-layer caching
class CacheService:
    def get_company_data(self, company_id: UUID, data_type: str):
        """
        L1: Redis (fast, 5-minute TTL)
        L2: Postgres (pre-computed tables)
        L3: Compute on-demand (fallback)
        """
        cache_key = f"company:{company_id}:{data_type}"
        
        # L1: Redis
        cached = redis_client.get(cache_key)
        if cached:
            return json.loads(cached)
        
        # L2: Postgres
        if data_type == 'ratios':
            data = db.query(FinancialRatios).filter_by(
                company_id=company_id
            ).order_by(FinancialRatios.period_end.desc()).first()
            
            if data:
                result = data.to_dict()
                redis_client.setex(cache_key, 300, json.dumps(result))
                return result
        
        # L3: Compute
        result = self._compute_data(company_id, data_type)
        redis_client.setex(cache_key, 300, json.dumps(result))
        return result
```

---

## Monitoring & Observability

### CloudWatch Setup

```yaml
LogGroups:
  - /ecs/equity-research-api
  - /ecs/equity-research-workers
  - /lambda/trigger-news-fetch

Metrics:
  - Namespace: EquityResearch/API
    Metrics:
      - QueryLatency (p50, p95, p99)
      - RequestCount
      - ErrorRate
      - ActiveSessions
  
  - Namespace: EquityResearch/Workers
    Metrics:
      - TaskDuration
      - TaskSuccessRate
      - TaskFailureRate
      - QueueDepth
  
  - Namespace: EquityResearch/Database
    Metrics:
      - ConnectionCount
      - QueryDuration
      - DeadlockCount

Alarms:
  - Name: HighAPILatency
    Metric: QueryLatency (p95)
    Threshold: > 3000ms
    Actions: SNS notification
  
  - Name: HighErrorRate
    Metric: ErrorRate
    Threshold: > 5%
    Actions: SNS notification, auto-scale API
  
  - Name: HighQueueDepth
    Metric: QueueDepth
    Threshold: > 500
    Actions: Auto-scale workers
  
  - Name: DatabaseCPUHigh
    Metric: RDS CPU Utilization
    Threshold: > 80%
    Actions: SNS notification
```

### Distributed Tracing (X-Ray)

```python
from aws_xray_sdk.core import xray_recorder
from aws_xray_sdk.ext.flask.middleware import XRayMiddleware

# Instrument FastAPI
xray_recorder.configure(service='equity-research-api')
app.add_middleware(XRayMiddleware, recorder=xray_recorder)

# Trace database queries
from aws_xray_sdk.core import patch_all
patch_all()

# Custom segments
@xray_recorder.capture('vector_search')
def search_filings(company_id, query):
    # X-Ray will automatically trace this
    return qdrant_client.search(...)
```

---

## Cost Estimation (Monthly, MVP Scale)

| Service | Configuration | Cost (USD) |
|---------|--------------|------------|
| **ECS Fargate (API)** | 2 tasks, 1 vCPU, 2 GB RAM | ~$30 |
| **ECS Fargate (Workers)** | 2 tasks, 2 vCPU, 4 GB RAM | ~$60 |
| **RDS PostgreSQL** | db.t3.medium, 100 GB, Multi-AZ | ~$80 |
| **ElastiCache Redis** | cache.t3.medium, 1 replica | ~$50 |
| **S3 Storage** | 500 GB storage, 100 GB transfer | ~$15 |
| **Qdrant (EC2)** | t3.large, 500 GB SSD | ~$70 |
| **SQS** | 10M requests/month | ~$5 |
| **CloudWatch** | Logs, metrics, alarms | ~$20 |
| **Data Transfer** | 100 GB out | ~$10 |
| **OpenAI API** | Embeddings + LLM calls | ~$50-150 |
| **Total** | | **~$390-490/month** |

**Optimization strategies:**
- Use EC2 spot instances for workers (-70% cost)
- Use S3 Intelligent Tiering (-40% storage cost)
- Optimize LLM calls (cache, smaller models)
- Use RDS reserved instances after 6 months (-40% cost)

---

## Deployment Pipeline (CI/CD)

### GitHub Actions Workflow

```yaml
name: Deploy to AWS

on:
  push:
    branches: [main]

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v2
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ap-south-1
      
      - name: Login to Amazon ECR
        id: login-ecr
        uses: aws-actions/amazon-ecr-login@v1
      
      - name: Build and push API image
        env:
          ECR_REGISTRY: ${{ steps.login-ecr.outputs.registry }}
          ECR_REPOSITORY: equity-research-api
          IMAGE_TAG: ${{ github.sha }}
        run: |
          docker build -t $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG .
          docker push $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG
      
      - name: Deploy to ECS
        run: |
          aws ecs update-service \
            --cluster equity-research-cluster \
            --service equity-research-api \
            --force-new-deployment
      
      - name: Run database migrations
        run: |
          aws ecs run-task \
            --cluster equity-research-cluster \
            --task-definition equity-research-migration \
            --launch-type FARGATE \
            --network-configuration "awsvpcConfiguration={subnets=[subnet-xxx],securityGroups=[sg-xxx],assignPublicIp=ENABLED}"
```

---

## Summary

This cloud deployment strategy provides:

1. **AWS as primary cloud** for mature ecosystem and cost efficiency
2. **ECS Fargate** for serverless container orchestration
3. **RDS PostgreSQL** with Multi-AZ for high availability
4. **S3** for scalable object storage with lifecycle policies
5. **ElastiCache Redis** for caching and session management
6. **Qdrant on EC2** for cost-effective vector search
7. **Celery + SQS** for asynchronous background processing
8. **EventBridge** for scheduled jobs
9. **Hybrid query architecture** balancing pre-computed data, caching, and on-demand refresh
10. **Comprehensive monitoring** with CloudWatch and X-Ray
11. **CI/CD pipeline** with GitHub Actions
12. **Cost-optimized** architecture starting at ~$400/month

This architecture scales from MVP (100s of users) to production (10k+ users) with minimal changes, primarily through auto-scaling and managed service tier upgrades.
