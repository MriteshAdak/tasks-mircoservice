# Tasks API (`tasks_api`)

The **Tasks API** is a FastAPI microservice that manages the task lifecycle (creation, pagination, filtering, updates, and deletion). It enforces strict user data isolation using stateless JWT token verification.

---

## Architectural Design & Working

The service follows a layered, domain-driven architecture:

```
src/tasks_api/
├── auth/               # Stateless JWT token validation & TokenClaims extraction
├── enums/              # TaskStatus enum (todo, in_progress, done)
├── exceptions/         # Domain exceptions (NotFound, Validation, Authentication)
├── infrastructure/     # Settings loader & SQLAlchemy database session provider
├── models/             # SQLAlchemy ORM entities (Task)
├── repositories/       # Query abstraction layer (TaskRepository)
├── routers/            # HTTP endpoints (/tasks, /health)
├── schemas/            # Pydantic schemas (TaskCreateRequest, TaskResponse, etc.)
├── services/           # Task domain business logic (TaskService)
├── dependencies.py     # FastAPI dependency injection definitions
├── handler.py          # AWS Lambda Mangum ASGI adapter
└── main.py             # FastAPI app factory and centralized exception handling
```

### Key Technical Decisions

- **Stateless Authorization**: Does not make network requests to `users_api` to authenticate requests. Instead, it symmetrically verifies incoming bearer tokens against the shared `JWT_SECRET` and extracts the user's UUID from the `sub` claim.
- **Zero Cross-Schema Foreign Keys**: To preserve microservice autonomy and avoid cross-schema database locks, the `tasks` table stores `user_id` as an indexed UUID column without a direct foreign key constraint to `users_api.users`.
- **Query Ownership Scoping**: Every database lookup, update, and deletion is scoped to the authenticated user's ID (`WHERE id = :task_id AND user_id = :user_id`). Attempting to access another user's task returns a `404 Not Found` to prevent information enumeration.
- **Serverless & Container Dual-Mode**: Can be run locally or in containers via `uvicorn src.tasks_api.main:app`, or deployed directly to AWS Lambda via `src/tasks_api/handler.py` (`Mangum(app)`).
- **Schema Isolation**: Operates inside the `tasks_api` PostgreSQL schema, including its native enum type `TaskStatus` and `alembic_version` tracking table.

---

## Database Models

All tables and enums are defined within the `tasks_api` schema.

### `tasks`
| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | Primary Key, Default UUID4 | Unique task ID |
| `user_id` | UUID | Indexed, Not Null | Owner's user ID (from JWT `sub`) |
| `title` | String | Not Null | Task title (1–200 characters) |
| `description` | String | Nullable | Optional detailed task description |
| `status` | Enum (`TaskStatus`) | Not Null, Default `todo` | `todo`, `in_progress`, or `done` |
| `due_date` | DateTime(UTC) | Nullable | Optional task due timestamp |
| `created_at` | DateTime(UTC) | Not Null | Timestamp created |
| `updated_at` | DateTime(UTC) | Not Null | Timestamp updated |

---

## API Endpoints

All task endpoints require an `Authorization: Bearer <token>` header obtained from `users_api`.

### Tasks (`/tasks`)

| Method | Endpoint | Description | Query / Body | Response | Status |
|---|---|---|---|---|---|
| `POST` | `/tasks` | Create a new task | `TaskCreateRequest` | `TaskResponse` | 201 Created |
| `GET` | `/tasks` | List tasks owned by authenticated user | `limit`, `offset`, `status`, `sort_by` | `TaskListResponse` | 200 OK |
| `GET` | `/tasks/{task_id}` | Retrieve specific task by ID | None | `TaskResponse` | 200 OK |
| `PATCH` | `/tasks/{task_id}` | Partially update an existing task | `TaskUpdateRequest` | `TaskResponse` | 200 OK |
| `DELETE` | `/tasks/{task_id}` | Delete a task by ID | None | Empty | 204 No Content |

#### Task Creation Example (`POST /tasks`)
```json
{
  "title": "Build integration pipeline",
  "description": "Configure GitHub actions and test runner",
  "status": "todo",
  "due_date": "2026-12-15T18:00:00Z"
}
```

#### Task List Response Example (`GET /tasks?status=todo&limit=20`)
```json
{
  "items": [
    {
      "id": "c1f76d91-4cf1-4560-bf86-53d9e48698bc",
      "user_id": "8c46002f-2c70-43be-8e01-1ad6b8408ec2",
      "title": "Build integration pipeline",
      "description": "Configure GitHub actions and test runner",
      "status": "todo",
      "due_date": "2026-12-15T18:00:00Z",
      "created_at": "2026-11-02T01:00:00Z",
      "updated_at": "2026-11-02T01:00:00Z"
    }
  ],
  "pagination": {
    "total": 1,
    "limit": 20,
    "offset": 0
  }
}
```

### System (`/`)
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Liveness health check (`{"status": "ok"}`) |
| `GET` | `/docs` | OpenAPI Swagger documentation |

---

## Running Locally

### 1. Prerequisites
- Python 3.14+ (or Python 3.11+)
- [uv](https://github.com/astral-sh/uv) or `pip`
- A PostgreSQL instance running (e.g., via `docker compose -f ../shared_db/docker-compose.yaml up postgres -d`)

### 2. Configure Environment
Copy `.env.example` to `.env` or `.env.local`:

```bash
cp .env.example .env.local
```

Edit the file to match your environment:
```ini
DATABASE_URL=postgresql+psycopg2://postgres:allowing123@localhost:5435/task_microservices
TASK_API_DB_SCHEMA=tasks_api
TASK_API_PORT=8082
JWT_SECRET=dev-secret-key-change-in-prod
JWT_ALGORITHM=HS256
LOG_LEVEL=INFO
```

> [!IMPORTANT]
> The `JWT_SECRET` must be identical to the one used by `users_api` so that JWT tokens can be properly validated.

### 3. Install Dependencies
```bash
# Using uv:
uv sync --all-groups

# Or using pip:
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -e .
```

### 4. Run Database Migrations
Alembic automatically ensures the `tasks_api` schema exists before applying migrations:

```bash
uv run alembic upgrade head
```

### 5. Start the Development Server
```bash
uv run uvicorn src.tasks_api.main:app --host 0.0.0.0 --port 8082 --reload
```

The API will be available at `http://localhost:8082` with interactive documentation at `http://localhost:8082/docs`.

---

## Database Migrations (Alembic)

When modifying SQLAlchemy models in `src/tasks_api/models/`:

```bash
# Generate a new migration revision
uv run alembic revision --autogenerate -m "describe changes"

# Apply the migration
uv run alembic upgrade head

# Rollback one migration revision
uv run alembic downgrade -1
```

---

## Testing & Linting

```bash
# Run tests
uv run pytest

# Check code formatting & style
uv run ruff check .
uv run black --check .
```

---

## Improvements in Next Phases

This section highlights architectural, security, and operational improvements planned for future phases, comparing the current baseline against target industry standards.

### 1. Asymmetric Token Verification (RS256 / JWKS)
* **Current State**: Validates incoming JWT bearer tokens using a symmetric secret (`JWT_SECRET`) and algorithm `HS256`. This means `tasks_api` possesses the shared secret key capable of forging valid authentication tokens for any user or identity across the entire system.
* **Next Phase Improvement**: Migrate to asymmetric verification (`RS256` or `ES256`). `tasks_api` will only maintain the public key (or retrieve key sets dynamically from `users_api` via a `/.well-known/jwks.json` endpoint). This eliminates shared secret leakage and enforces strict zero-trust boundaries between services.

### 2. Distributed Tracing & Request Correlation
* **Current State**: `asgi-correlation-id` and `structlog` are included as dependencies in `pyproject.toml`, but neither is wired into `tasks_api.main:create_app`. As a result, incoming requests lack an `X-Request-ID` correlation header, and log records cannot be traced back across service boundaries.
* **Next Phase Improvement**: Register `CorrelationIdMiddleware` in FastAPI and configure structured JSON logging (`structlog` or custom log formatters) to bind and emit `request_id` across all application log statements.

### 3. Deep Health & Readiness Probes (`/health/live` vs. `/health/ready`)
* **Current State**: The `/health` endpoint returns a hardcoded `{"status": "ok"}` without testing database connectivity or query execution. If the PostgreSQL connection pool is saturated or the database goes offline, orchestrators continue routing traffic to broken instances.
* **Next Phase Improvement**: Split into two distinct endpoints:
  * `GET /health/live`: Fast, shallow process liveness probe.
  * `GET /health/ready`: Deep readiness probe that issues a lightweight query (`SELECT 1`) against PostgreSQL to verify database connectivity before receiving traffic.

### 4. Asynchronous Database Driver & Native Async Sessions
* **Current State**: The service uses synchronous SQLAlchemy with `psycopg2-binary` (`engine = create_engine(...)`) and synchronous route handlers (`def create_task(...)`). FastAPI executes these synchronous handlers in a background worker threadpool, adding thread context-switching overhead under high concurrency.
* **Next Phase Improvement**: Adopt `asyncpg` (`postgresql+asyncpg://`) and SQLAlchemy's `AsyncSession` alongside native `async def` route handlers to enable fully non-blocking I/O across all database queries.

### 5. Event-Driven Lifecycle Consumption (Orphan Task Cleanup)
* **Current State**: There is no inter-service communication or message broker between `users_api` and `tasks_api`. When a user account is deleted in `users_api`, their associated task records remain permanently orphaned in the `tasks_api` database schema.
* **Next Phase Improvement**: Introduce an event subscriber (using RabbitMQ, Redis Streams, or AWS SQS) that listens for a `UserDeleted` domain event and executes automated task cleanup or cascading soft-deletes.

### 6. Dependency Pruning & Environment Hygiene
* **Current State**: `pyproject.toml` contains dependencies that are not utilized in `tasks_api`, including `pwdlib[argon2]` (password hashing is only required by `users_api`) and `boto3` / `mangum` without an active AWS Lambda CI/CD pipeline.
* **Next Phase Improvement**: Prune unused dependencies from `pyproject.toml` and re-export `requirements.txt` to minimize container image attack surface and installation times.

### 7. Automated Test Suite
* **Current State**: No automated unit or integration tests exist in the repository despite `pytest` being configured in `pyproject.toml`.
* **Next Phase Improvement**: Implement comprehensive test suites:
  * Unit tests for `TaskService` business rules and validation logic (due date validation, title length, status transitions).
  * Integration tests for `/tasks` HTTP endpoints using `httpx.AsyncClient` with a test database container.


