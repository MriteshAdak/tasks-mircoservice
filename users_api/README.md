# Users API (`users_api`)

The **Users API** is a FastAPI microservice responsible for user identity management, credential storage, and local authentication via JSON Web Tokens (JWT).

---

## Architectural Design & Working

The service follows a layered, domain-driven structure to maintain separation of concerns:

```
src/users_api/
├── auth/               # Password hashing (Argon2) & JWT creation/decoding
├── exceptions/         # Domain exceptions (NotFound, Conflict, InvalidCredentials, etc.)
├── infrastructure/     # Settings loader & SQLAlchemy database session provider
├── models/             # SQLAlchemy ORM entities (User, UserCredentials)
├── repositories/       # Data persistence and query abstraction layer
├── routers/            # HTTP endpoints (/users, /auth, /health)
├── schemas/            # Pydantic validation models (UserCreate, TokenResponse, etc.)
├── services/           # Core business logic (UserService)
├── dependencies.py     # FastAPI dependency injection definitions
└── main.py             # FastAPI app factory and centralized exception handling
```

### Key Technical Decisions

- **Password Security**: Passwords are never stored in plain text. They are hashed using **Argon2** via `pwdlib[argon2]`.
- **Credential Separation**: User profiles (`users` table) and security credentials (`user_credentials` table) are kept separate in the database, with a cascading foreign key delete.
- **JWT Issuance**: Upon successful login, the service issues an HMAC-SHA256 (`HS256`) signed JWT containing:
  - `sub`: User ID (UUID)
  - `username`: User's login handle
  - `exp`: Expiration timestamp based on `JWT_ACCESS_TOKEN_EXPIRE_MINUTES`
- **Schema Isolation**: The service operates inside the `users_api` PostgreSQL schema. It maintains its own `alembic_version` table within that schema.

---

## Database Models

All tables are defined within the `users_api` schema.

### `users`
| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | Primary Key, Default UUID4 | Unique user ID |
| `username` | String | Unique, Indexed, Not Null | Unique login username |
| `display_name` | String | Not Null | Publicly visible display name |
| `created_at` | DateTime(UTC) | Not Null | Timestamp of registration |
| `updated_at` | DateTime(UTC) | Not Null | Timestamp of last update |

### `user_credentials`
| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | Primary Key, Default UUID4 | Credential record ID |
| `user_id` | UUID | Unique, Indexed, FK -> `users.id` (ON DELETE CASCADE) | Owning user |
| `password_hash` | String | Not Null | Argon2 password hash |
| `created_at` | DateTime(UTC) | Not Null | Timestamp created |
| `updated_at` | DateTime(UTC) | Not Null | Timestamp updated |

---

## API Endpoints

### User Management (`/users`)

| Method | Endpoint | Description | Request Body | Response | Status |
|---|---|---|---|---|---|
| `POST` | `/users` | Register a new user | `UserCreate` | `UserResponse` | 201 Created |
| `GET` | `/users/{username}` | Look up user by username | None | `UserResponse` | 200 OK |
| `DELETE` | `/users/{username}` | Delete user & credentials | None | Empty | 204 No Content |

#### Registration Payload Example (`POST /users`)
```json
{
  "username": "johndoe",
  "display_name": "John Doe",
  "password": "StrongPassword123!"
}
```

### Authentication (`/auth`)

| Method | Endpoint | Description | Headers | Response | Status |
|---|---|---|---|---|---|
| `POST` | `/auth/login` | Verify credentials & issue JWT | None | `TokenResponse` | 200 OK |
| `GET` | `/auth/me` | Fetch authenticated user profile | `Authorization: Bearer <token>` | `UserResponse` | 200 OK |

#### Login Payload Example (`POST /auth/login`)
```json
{
  "username": "johndoe",
  "password": "StrongPassword123!"
}
```

#### Token Response
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsIn...",
  "token_type": "bearer",
  "expires_in": 900
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
USER_API_DB_SCHEMA=users_api
USER_API_PORT=8081
JWT_SECRET=dev-secret-key-change-in-prod
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
LOG_LEVEL=INFO
```

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
Alembic automatically ensures the `users_api` schema exists before applying migrations:

```bash
uv run alembic upgrade head
```

### 5. Start the Development Server
```bash
uv run uvicorn src.users_api.main:app --host 0.0.0.0 --port 8081 --reload
```

The API will be available at `http://localhost:8081` with interactive documentation at `http://localhost:8081/docs`.

---

## Database Migrations (Alembic)

When modifying SQLAlchemy models in `src/users_api/models/`:

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

### 1. Asymmetric Token Issuance (RS256 / JWKS Endpoint)
* **Current State**: Generates access tokens signed using symmetric HMAC-SHA256 (`HS256`) and a shared `JWT_SECRET`. To verify user identities, downstream microservices (such as `tasks_api`) must possess the exact same secret key, creating a risk where consuming services can forge arbitrary user tokens.
* **Next Phase Improvement**: Transition to asymmetric cryptography (`RS256` or `ES256`). `users_api` will sign tokens using a private RSA key and expose a public JSON Web Key Set (`GET /.well-known/jwks.json`). Downstream consumers will verify token signatures using the public key alone, establishing zero-trust service boundaries.

### 2. Event-Driven User Lifecycle Notifications (Publishing `UserDeleted`)
* **Current State**: The `DELETE /users/{username}` endpoint deletes user credentials and the profile record within `users_api` in isolation. There is no notification sent to dependent services, resulting in orphaned records in services like `tasks_api`.
* **Next Phase Improvement**: Integrate an event publisher (using RabbitMQ, Redis Streams, or AWS SNS/SQS) that broadcasts a `UserDeleted` event when an account is removed, allowing downstream services to purge or soft-delete user-owned resources asynchronously.

### 3. Deep Health & Readiness Probes (`/health/live` vs. `/health/ready`)
* **Current State**: The `/health` endpoint returns a static `{"status": "ok"}` response without checking if PostgreSQL is reachable or able to process queries.
* **Next Phase Improvement**: Separate health checks into:
  * `GET /health/live`: Fast process liveness probe.
  * `GET /health/ready`: Deep readiness probe executing a lightweight SQL query (`SELECT 1`) to ensure database connectivity before orchestrators route traffic to the container.

### 4. Asynchronous Database Driver & Native Async Sessions
* **Current State**: The application uses synchronous SQLAlchemy with `psycopg2-binary` (`engine = create_engine(...)`) and synchronous route functions (`def register_user(...)`). FastAPI executes these functions in a threadpool worker, increasing memory and context-switching overhead under heavy traffic.
* **Next Phase Improvement**: Upgrade database connectivity to `asyncpg` (`postgresql+asyncpg://`) with SQLAlchemy's `AsyncSession` and native `async def` route handlers for non-blocking I/O and improved request throughput.

### 5. Distributed Tracing & Request Correlation
* **Current State**: `asgi-correlation-id` and `structlog` are defined in `pyproject.toml`, but neither is activated in `users_api.main:create_app`. Distributed requests cannot be correlated across service boundaries.
* **Next Phase Improvement**: Register `CorrelationIdMiddleware` to automatically extract or generate `X-Request-ID` headers, and format application logs as structured JSON containing the active `request_id`.

### 6. Refresh Token Rotation & Token Revocation
* **Current State**: Only short-lived access tokens (15-minute default) are issued upon login. There is no refresh token mechanism, nor is there a token blocklist/revocation store when a user account is deleted or credentials are changed.
* **Next Phase Improvement**: Implement secure HTTP-only refresh token rotation and a Redis-backed token revocation/invalidation list to immediately revoke active sessions upon password reset or account deletion.

### 7. Automated Test Suite
* **Current State**: No automated test cases exist under `tests/`.
* **Next Phase Improvement**: Implement automated testing with `pytest` and `httpx`:
  * Unit tests for password validation rules, display name constraints, and username formatting.
  * Integration tests for `/auth/login`, `/auth/me`, and `/users` CRUD operations with an isolated test database.


