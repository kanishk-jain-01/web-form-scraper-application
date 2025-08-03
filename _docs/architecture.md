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
3. **LangGraph Orchestrator (Python)** – Core component using `create_react_agent` from LangGraph to manage ReAct-style agents. Stateless instances are autoscaled (e.g., via Kubernetes or AWS ECS) based on queue load. Handles tool calls, state persistence via checkpointers (e.g., Redis or Postgres-based), and integration with BrowserUse/Stagehand for browser actions. Publishes long-running scrapes to the job queue for async processing.
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
  U[User] -->|"Enter URL / Start"| FE[Frontend SPA #40;React#41;]
  FE -->|"WebSocket / REST"| AG[LangGraph Agent #40;create_react_agent#41;]

  subgraph "Scrape Loop #40;ReAct Cycle#41;"
    AG -->|"Init Browser Session #40;WebSocket CDP#41;"| BB[Browserbase Session]
    BB --> SH[Stagehand Framework #40;Python SDK#41;]
    BB --> BU[BrowserUse Agent #40;High-Level Wrapper#41;]
    SH --> TOOLS["act#40;#41; / extract#40;#41; / observe#40;#41; / navigate#40;#41;"]
    BU --> TOOLS["Agent.run#40;#41; for Multi-Step Tasks"]
    TOOLS --> AX[Chrome Accessibility Tree / DOM Snapshot]
    AX --> TOOLS
    TOOLS -->|"Form JSON Updates"| AG
    AG -->|"DB Lookup/Store #40;e.g., login check#41;"| PG[(Postgres DB)]
    AG -->|"Real-Time Progress #40;e.g., actions, partial JSON#41;"| FE
  end

  subgraph "HITL Flow"
    AG -->|"Interrupt #40;via LangGraph interrupt_before#41;"| HITL["HITL Node"]
    HITL -->|"Prompt User #40;e.g., 'Enter CAPTCHA' or 'Verify Email'#41;"| FE
    FE -->|"Display Prompt"| U
    U -->|"Human Input #40;e.g., text, confirmation#41;"| FE
    FE -->|"Feedback / Resume"| AG
  end

  subgraph "Agent Decision Making"
    AG --> AGENT["agent#40;#41; - Reason/Act/Observe Loop"]
    AGENT -->|"Tool Calls #40;Custom: Navigate, Fill, Analyze, HITL#41;"| LLM[LLM #40;OpenAI GPT-4o / Anthropic Claude#41;]
    LLM -->|"Structured Output #40;e.g., tool invocation#41;"| AGENT
    AGENT -->|"State Update #40;via Checkpointer#41;"| RS[(Redis / MemorySaver)]
  end

  AG -->|"Completed / Results #40;Full Form JSON#41;"| FE
  FE -->|"Display Results / Store Locally"| U
```

### Description
1. **Initiation**: User enters URL in Frontend, which sends a request to start the agent via WebSocket/REST. LangGraph spawns a `create_react_agent` instance with custom tools, LLM, and state schema (e.g., extending `AgentState` with `form_json: dict`, `url: str`, `step_count: int`).
2. **Scrape Loop**:
   - **Browser Integration**: Agent establishes a WebSocket CDP connection to Browserbase for a headless session. Uses Stagehand for granular actions (e.g., `act("Click login button")`, `extract({"schema": form_schema})`) and BrowserUse for high-level tasks (e.g., `Agent(task="Navigate to form and extract fields")`).
   - **Tools Definition** (in LangGraph):
     - `Navigate(url: str)`: Wrapper around Stagehand/BrowserUse `goto()` or navigation actions.
     - `Fill Form Fields(fields: dict)`: Uses Stagehand `act()` to input data, handling metadata like required lengths/options from DB.
     - `Analyze Page(instructions: str)`: Combines Stagehand `observe()`/`extract()` with BrowserUse for page analysis, updating form JSON state.
     - `HITL(prompt: str)`: Custom tool that interrupts the loop, sends prompt to Frontend via WebSocket, awaits user input, and resumes.
     - Tools bound to LLM with schemas for structured calls; support parallel execution in v2.
   - **State Management**: LangGraph checkpointer (e.g., `MemorySaver` backed by Redis) persists messages, form JSON, and progress. DB lookup at start (e.g., check if site requires login via cached Postgres query).
   - **Accessibility/robustness**: Leverages Chrome Accessibility Tree for resilient selectors (anti-fragile to DOM changes).
3. **HITL Flow**: Triggered on errors (e.g., CAPTCHA, email verification) or ambiguities. Uses LangGraph `interrupt_after=["tools"]` to pause after tool calls, routing to HITL node. Frontend displays interactive prompts; user input fed back to agent state.
4. **Decision Making**: ReAct loop in `create_react_agent` (v2 for parallel tools). LLM reasons over state (e.g., "If login required, call Navigate to login page, then Fill Form Fields"). Stops on success (e.g., form scraped) or max steps. Updates visible to user via WebSocket.