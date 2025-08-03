# Routes Documentation

This document outlines the API routes for the backend of the web form scraping application. The backend uses FastAPI for RESTful endpoints and WebSocket support. Routes are organized by category (e.g., Scrape Jobs, WebSocket). All endpoints are prefixed with `/api/v1` for versioning.

Security notes:
- No authentication is required as this is an internal tool.
- Input validation uses Pydantic models.
- Rate limiting applied via middleware (e.g., SlowAPI) if needed for abuse prevention.
- Errors return standard HTTP codes (e.g., 400 for bad request).

## Scrape Job Routes
These manage scrape requests, status queries, and results.

| Method | Endpoint                | Description                                  | Request Body/Params/Example          | Response                              |
|--------|-------------------------|----------------------------------------------|--------------------------------------|---------------------------------------|
| POST   | /scrape/start           | Initiate a new scrape job for a URL. Returns job ID for tracking. | {"url": "https://example.com"}      | 202: {"job_id": "uuid", "status": "queued"} |
| GET    | /scrape/jobs            | List all scrape jobs. Supports pagination. | Query params: ?page=1&limit=10       | 200: [{"job_id": "uuid", "url": "string", "status": "running", "started_at": "timestamp"}] |
| GET    | /scrape/jobs/{job_id}   | Get details of a specific job, including status, partial results, and final form JSON. | Path: {job_id}                       | 200: {"job_id": "uuid", "status": "complete", "results": {"form_json": {...}}} |
| DELETE | /scrape/jobs/{job_id}   | Cancel or delete a scrape job (if pending/running). | Path: {job_id}                       | 204: No content                       |

## Website Metadata Routes
These provide access to stored form metadata from the DB.

| Method | Endpoint                  | Description                                  | Request Body/Params/Example          | Response                              |
|--------|---------------------------|----------------------------------------------|--------------------------------------|---------------------------------------|
| GET    | /websites                 | List websites with scraped metadata. | Query params: ?domain=example.com    | 200: [{"domain": "string", "requires_login": true, "last_scraped": "timestamp"}] |
| GET    | /websites/{domain}        | Get form fields metadata for a specific website. | Path: {domain} (e.g., example.com)   | 200: {"domain": "string", "form_fields": [{"field_name": "string", "metadata": {...}}]} |

## WebSocket Endpoint
For real-time interactions, including progress updates, HITL prompts, and responses.

- **Endpoint**: ws://<host>/ws/{job_id}
- **Description**: Establishes a WebSocket connection for a specific job. The frontend connects after starting a scrape.
- **Events** (Server → Client):
  - `progress_update`: {"action": "Navigating to page", "partial_form": {...}}
  - `hitl_prompt`: {"prompt": "Enter CAPTCHA code", "type": "text"}
  - `scrape_complete`: {"job_id": "uuid", "results": {"form_json": {...}}}
  - `error`: {"message": "Browser session failed"}
- **Events** (Client → Server):
  - `hitl_response`: {"response": "user_input"}
  - `cancel_job`: {} (to interrupt and cancel)
- **Connection Flow**: Client connects with job_id → Server validates → Streams updates from LangGraph agent → Closes on completion or error.
