# Frontend
- Vite: Build tool for fast development and production bundling.
- React: JavaScript library for building the single-page application (SPA).
- TypeScript: Superset of JavaScript for type safety and better developer experience.
- TailwindCSS: Utility-first CSS framework for styling.
- ShadCn: Component library built on Tailwind for reusable UI elements.
- Socket.io: Library for real-time WebSocket communication (e.g., agent progress updates and HITL prompts).
- Material-UI (optional): For additional UI components if ShadCn needs supplementation.
- Zustand: A minimalistic state management library for React, ideal for handling global app state like scrape job status and real-time updates without the boilerplate of Redux.

# Backend
## API Layer
- Python: Core programming language for backend services.
- FastAPI: High-performance web framework for building APIs with automatic OpenAPI docs and async support. Handles REST/GraphQL endpoints, authentication, and WebSocket proxying.

## Browser Automation
- Browserbase: Headless browser service that spins up cloud-based browser instances. Requires API keys for authentication and provides scalable, secure sessions via WebSocket (CDP protocol). Integrates with Stagehand and BrowserUse for automation.
- Stagehand: Python SDK for AI-powered browser actions (e.g., act(), extract(), observe()) using natural language instructions. Built on Playwright for resilience to DOM changes.
- BrowserUse: Open-source Python library for high-level AI agent browser interactions. Wraps Playwright and LLMs for tasks like navigation and data extraction; complements Stagehand for agentic workflows.

## AI Orchestration
- LangGraph: Open-source framework for building stateful AI agents. Uses `create_react_agent` for ReAct-style loops, tool integration, state management, and interruptions (e.g., HITL).

## Data Storage and Management
- PostgreSQL: Relational database for persistent storage of form metadata (JSONB columns), website details, scrape job history, and user data. Supports efficient querying and indexing on semi-structured data.
- Redis: In-memory data store for caching (e.g., DB lookups, session states), ephemeral agent progress, and WebSocket fan-out. Configured for eviction and rate limiting.

## Asynchronous Processing
- Job Queue: SQS (AWS Simple Queue Service), Kafka, or RabbitMQ for buffering scrape jobs, enabling fault-tolerant async execution, retries, and decoupling of API from LangGraph.

## LLMs
- OpenAI (GPT-4o): Primary LLM for agent reasoning, tool calls, and browser action interpretation.
- Anthropic (Claude): Alternative LLM for high-level decisions in LangGraph, with support for structured outputs.

## Observability and Monitoring
- OpenTelemetry: For distributed tracing, metrics, and logs across services (API, LangGraph, Browserbase).
- Prometheus: Metrics collection and alerting.
- Grafana/Loki: Dashboards for visualization and log aggregation. Used to monitor agent loops, latencies, error rates, and resource usage.

## Security
- JWT/OAuth: For user authentication in FastAPI.
- TLS/mTLS: Encryption for all communications.
- WAF (e.g., Cloudflare): Web Application Firewall for DDoS and XSS protection.
- Secrets Management: AWS Secrets Manager or equivalent for API keys (e.g., Browserbase, OpenAI).

## Deployment and Infrastructure
- Docker: Containerization for consistent environments across API, LangGraph, and other services.
- Kubernetes/AWS ECS: Orchestration for autoscaling stateless components like LangGraph workers.
- CI/CD: GitHub Actions or Jenkins for automated testing, building, and deployment pipelines.
- Cloud Provider (optional): AWS (for SQS, ECS, Secrets Manager) or equivalents like GCP/Azure for hosting.

## Additional Notes
- All components are chosen for compatibility: e.g., FastAPI's async nature pairs well with LangGraph's runnables and Browserbase's WebSocket.
- Environment Management: Use `.env` files or tools like `python-dotenv` for API keys and configs.
- Dependencies: Managed via `pip` for Python (e.g., `fastapi`, `langgraph`, `stagehand-py`, `browser-use`, `psycopg2` for Postgres, `redis-py`).
- Version Control: Git for source code, with branches for features like HITL integration.