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

## Improvements in Next Phase

> [!NOTE]
> For platform-wide improvements (such as the migration to asynchronous `asyncpg` drivers, dual-probe health checks, distributed correlation IDs, and unified containerized testing), refer to the [Root README](../README.md#improvements-in-next-phase-platform-wide).

This section details improvements and architectural refinements specific to the **Tasks API**, comparing the current baseline against target industry standards.

### 1. Service-Specific Improvements

#### A. Event-Driven Lifecycle Consumption (Handling `UserDeleted` Events)
* **Current State**: There is no inter-service communication or message subscription. When a user is deleted in `users_api`, their associated task records remain permanently orphaned in the `tasks_api` schema.
* **Next Phase Improvement**: Implement an asynchronous message consumer (e.g., subscribing to a `user.deleted` topic via RabbitMQ, Redis, or AWS SQS). When received, `tasks_api` will execute a cascading soft-delete or purge of all task records belonging to that `user_id`.

#### B. Task Status State Machine & Workflow Transitions
* **Current State**: The `status` field accepts any valid `TaskStatus` enum value (`todo`, `in_progress`, `done`) on updates without transition validation (e.g., a task can jump directly from `todo` to `done` or revert arbitrarily without audit records).
* **Next Phase Improvement**: Introduce a formal state machine inside `TaskService` with explicit transition rules (e.g., `todo` -> `in_progress` -> `done`), automated timestamp capture (`started_at`, `completed_at`), and status change event emission.

#### C. Full-Text Search, Advanced Filtering & Tagging
* **Current State**: Tasks can only be filtered by exact `status` match and sorted across four static columns. Searching tasks by keywords requires full-table client-side inspection.
* **Next Phase Improvement**: Add PostgreSQL full-text search indexing (`to_tsvector`) on `title` and `description`, support tag-based filtering (`tags: list[str]`), priority levels (`low`, `medium`, `high`, `urgent`), and overdue/due-date range queries.

#### D. Dependency Pruning & Container Minimization
* **Current State**: `pyproject.toml` packages dependencies unneeded by `tasks_api`, including `pwdlib[argon2]` (password hashing is only performed in `users_api`) and `boto3` / `mangum` without an active AWS Lambda CI/CD workflow.
* **Next Phase Improvement**: Remove extraneous libraries from `pyproject.toml` and re-export a minimal `requirements.txt` to decrease Docker image size, build duration, and security attack surface.

---

### 2. Authorization & Access Control Elements

The Tasks API currently enforces a single access rule: the token subject (`sub`) must match `task.user_id`. The next phase will introduce a multi-layered access control framework:

#### A. Granular Task Scopes
* **Current State**: Any valid token can perform all operations (read, create, update, delete) on tasks owned by the caller.
* **Next Phase Improvement**: Enforce OAuth2-style permission scopes on endpoints using FastAPI's `Security(get_current_user, scopes=[...])`:
  * `tasks:read`: Read-only access to task lists and details.
  * `tasks:write`: Permission to create and update tasks.
  * `tasks:delete`: Permission to permanently delete tasks.
  * `tasks:admin`: Administrative override to manage tasks across all users.

#### B. Resource Ownership & Collaboration Policies (ABAC)
* **Current State**: Strict 1:1 ownership (`WHERE user_id = :user_id`). Tasks cannot be shared, assigned to team members, or viewed by collaborators.
* **Next Phase Improvement**: Implement Attribute-Based Access Control (ABAC) allowing collaborative task management:
  * **Role Differentiation**: Distinguish between `owner_id` (creator) and `assignee_id` (worker).
  * **Collaborator Access**: Add a `task_members` mapping with permissions (`viewer`, `editor`).
  * **Access Policy**: Allow read access if `user_id IN (owner_id, assignee_id, collaborators)`; allow edit access only if `user_id == owner_id` or user has `editor` role on the task.

#### C. Admin Override & Cross-User Auditing
* **Current State**: Querying a task owned by another user always returns `404 Not Found`, even for administrators or support personnel.
* **Next Phase Improvement**:
  * Check the `roles` claim in the verified token. If `admin` is present, bypass the `user_id` query filter to allow inspecting or reassigning tasks across users.
  * Emit an immutable structured audit log entry whenever an administrative user accesses or modifies another user's task.

#### D. State-Based Immutability & Archival Protection
* **Current State**: Any task, regardless of age or completion status, can be updated or deleted.
* **Next Phase Improvement**: Enforce state-based authorization policies:
  * Lock tasks marked as `archived` or `completed` older than a configurable retention period from routine edits.
  * Require explicit `tasks:reopen` or `tasks:admin` permissions to modify locked or completed tasks.



