# Multi-Tier Architecture

## High-Level Architecture

```mermaid
graph TD
  U["User Browser"] -->|"HTTPS / WebSocket"| FE["Frontend SPA #40;React#41;"]
  FE -->|"GraphQL / REST"| CDN["CDN / WAF #40;e.g., Cloudflare#41;"]
  CDN --> LB["API Load Balancer #40;e.g., AWS ALB#41;"]
  LB --> API["Application Service #40;Python FastAPI / Flask#41;"]
  API -->|"gRPC / REST"| LG["LangGraph Orchestrator #40;Python, stateless, autoscaled#41;"]
  LG <--> |"WebSocket #40;CDP#41;"| BB["Browserbase Cluster #40;Remote Headless Browsers#41;"]
  LG --> |"JSON Form Metadata / Job Metadata"| PG[("Postgres DB #40;with JSONB support#41;")]
  LG --> |"Publish / Consume Jobs"| Q["Job Queue #40;SQS / Kafka / RabbitMQ#41;"]
  API <--> |"WebSocket #40;for real-time updates#41;"| U
  API --> RS["Redis #40;ephemeral state / sockets / caching#41;"]

  subgraph Observability
    OT["OpenTelemetry Collector"] --> GF["Grafana / Prometheus / Loki"]
  end
  API --> OT
  LG --> OT
  BB --> OT

  subgraph Security
    SEC["TLS 1.3 / mTLS, WAF Rules, API Keys, VPC Private Subnets, SGs"]
  end
  SEC -.-> API
  SEC -.-> LG
  SEC -.-> BB
  SEC -.-> PG
  SEC -.-> Q
  SEC -.-> RS
```

### Description
1. **Frontend SPA (React)** – A single-page application served via CDN/WAF for security and performance. It handles user input (e.g., URL entry, "Start" button), displays real-time agent progress via WebSocket, and manages HITL prompts/interventions. Uses libraries like Socket.io for WebSocket handling and Material-UI for UI components.
2. **API Load Balancer & Service (Python FastAPI/Flask)** – Stateless layer handling authentication (e.g., JWT/OAuth), scrape request validation, and proxying WebSocket traffic for agent updates. Exposes GraphQL/REST endpoints for initiating jobs and querying status. Integrates with LangGraph for job orchestration.
3. **LangGraph Orchestrator (Python)** – Core component using `create_react_agent` from LangGraph to manage ReAct-style agents. Stateless instances are autoscaled (e.g., via Kubernetes or AWS ECS) based on queue load. Handles tool calls, state persistence via checkpointers (e.g., Redis or Postgres-based), and integration with Stagehand for browser actions. Publishes long-running scrapes to the job queue for async processing.
4. **Browserbase Cluster** – Remote, headless browser service (e.g., via Browserbase.com) providing scalable, secure sessions. Connected via WebSocket (Chrome DevTools Protocol - CDP) for low-latency control. Executes actions in isolated environments to avoid IP blocks and ensure compliance. Monitored for session health and timeouts.
5. **Postgres DB** – Persistent storage for scraped form-field metadata (as JSONB columns for flexible schema), website keys (e.g., unique by domain), user accounts, job history, and audit logs. Schema includes tables like `websites` (id, domain, requires_login bool), `form_fields` (website_id fk, field_json jsonb), and `scrape_jobs` (id, status, results_json jsonb). Supports indexing on JSONB for efficient queries.
6. **Redis** – Used for ephemeral data like active WebSocket connections, agent session states (e.g., partial form JSON during scraping), caching DB lookups (e.g., login requirements), and rate limiting. Configured with eviction policies for memory management.
7. **Job Queue (SQS/Kafka/RabbitMQ)** – Buffers scrape requests for asynchronous, fault-tolerant processing. Allows decoupling of API from LangGraph, enabling retries on failures (e.g., browser crashes) and prioritization of jobs.
8. **Observability** – Implements distributed tracing (OpenTelemetry), metrics (Prometheus), and logging (Loki/ELK) for end-to-end visibility. Dashboards track agent loops, tool call latencies, error rates, and resource usage. Alerts for anomalies like high failure rates or session timeouts.
9. **Security Controls** – Enforce TLS/mTLS everywhere; WAF for DDoS/XSS protection; API keys/secrets management (e.g., AWS Secrets Manager) for LLM/Browserbase credentials; network isolation via VPC private subnets and security groups; encrypted storage (e.g., Postgres at-rest encryption); role-based access control (RBAC) for users; compliance with GDPR/CCPA for data handling. Avoid storing sensitive form data (e.g., passwords) in DB.

### Additional Considerations
- **Scalability**: Horizontal scaling for API and LangGraph via containers. Browserbase handles browser scaling natively. Use auto-scaling groups based on queue depth or CPU metrics.
- **Deployment**: Containerized (Docker) on Kubernetes/AWS ECS for orchestration. CI/CD with GitHub Actions or Jenkins.
- **Cost Optimization**: Use spot instances for non-critical LangGraph workers; monitor Browserbase usage to avoid over-provisioning.
- **Error Handling**: Global try-catch in LangGraph for tool failures, with retries (e.g., max 3) and fallbacks to HITL. Queue dead-letter for failed jobs.

---

## Low-Level Architecture (Agent–Run Flow)

```mermaid
graph TD
    U[User] -->|"Enter URL / Start"| FE[Frontend SPA React]
    FE -->|"WebSocket / REST"| FA[FastAPI Backend - Endpoints/Handlers]
    FA -->|"Queue Job URL/Task"| JQ[Job Queue RabbitMQ]
    JQ --> WP[Worker Process - Pulls & Processes Jobs]
    WP --> SM[Session Manager - Init Browser Session WebSocket CDP]
    SM --> BB[Browserbase Session]
    WP --> AG[LangGraph Orchestrator - Configures/Runs create_react_agent]
    subgraph "Scrape Loop ReAct Cycle"
        AG --> AGENT["agent - Reason/Act/Observe Loop"]
        AGENT -->|"Tool Calls Custom: Navigate, Fill, Analyze, HITL"| TOOLS[Custom Tools]
        TOOLS --> SH[Stagehand Framework Python SDK]
        SH --> BB
        SH -->|"act / extract / observe / goto / navigate"| AX[Chrome Accessibility Tree / DOM Snapshot]
        AX --> SH
        TOOLS -->|"Form JSON Updates"| AGENT
        AG -->|"Real-Time Progress actions, partial JSON via WebSocket"| FA
        FA --> FE
    end
    subgraph "HITL Flow"
        TOOLS -->|"HITL Tool - Interrupt via LangGraph interrupt_before"| HITL["HITL Node"]
        HITL -->|"Prompt User Enter CAPTCHA or Verify Email via WebSocket"| FA
        FA -->|"Display Prompt"| FE
        FE -->|"Display Prompt"| U
        U -->|"Human Input text, confirmation"| FE
        FE -->|"Feedback / Resume via WebSocket"| FA
        FA -->|"Resume"| HITL
        HITL --> AGENT
    end
    subgraph "Agent Decision Making"
        AGENT --> LLM[LLM OpenAI GPT-4o / Anthropic Claude]
        LLM -->|"Structured Output tool invocation"| AGENT
        AGENT -->|"State Update via Checkpointer"| RS[(Redis / MemorySaver)]
    end
    AG -->|"DB Lookup login check during Loop if Needed via Tool/Hook"| PG[(Postgres DB)]
    AG -->|"Completed / Results Full Form JSON"| PH[Post-Agent Hook - Save to DB & Notify]
    PH -->|"Save Form JSON/Job History"| PG
    PH -->|"Results via WebSocket/REST"| FA
    FA -->|"Completed / Results"| FE
    FE -->|"Display Results / Store Locally"| U
    WP -->|"Cleanup Session on Job End"| SM
    SM -->|"Close Session"| BB
```
