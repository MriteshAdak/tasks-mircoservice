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

## Improvements in Next Phase

> [!NOTE]
> For platform-wide improvements (such as the migration to asynchronous `asyncpg` drivers, dual-probe health checks, distributed correlation IDs, and unified containerized testing), refer to the [Root README](../README.md#improvements-in-next-phase-platform-wide).

This section details improvements and architectural refinements specific to the **Users API**, comparing the current baseline against target industry standards.

### 1. Service-Specific Improvements

#### A. Asymmetric Key Lifecycle & JWKS Provider (`/.well-known/jwks.json`)
* **Current State**: Generates access tokens using a symmetric HMAC-SHA256 (`HS256`) secret key shared with downstream microservices. Consuming services that verify tokens hold the secret necessary to forge tokens.
* **Next Phase Improvement**: Act as an OpenID Connect (OIDC)-style Identity Provider:
  * Sign tokens using an asymmetric private RSA/ECDSA key (`RS256` or `ES256`).
  * Expose a public JSON Web Key Set endpoint (`GET /.well-known/jwks.json`) supporting automated key rotation, allowing downstream consumers to verify tokens securely without access to private signing keys.

#### B. Event-Driven User Lifecycle Publishing
* **Current State**: `DELETE /users/{username}` removes credentials and user records in isolation. No event is emitted to inform dependent services of the deletion.
* **Next Phase Improvement**: Implement a transactional outbox pattern to broadcast lifecycle events (`UserRegistered`, `UserUpdated`, `UserDeleted`) to a platform event broker (RabbitMQ, Redis Streams, or AWS SNS). This enables decoupled microservices to clean up dependent resources automatically.

#### C. Refresh Token Rotation & Session Invalidation
* **Current State**: Issues only short-lived access tokens (15-minute default). There is no refresh token flow, session store, or mechanism to invalidate compromised tokens prior to expiration.
* **Next Phase Improvement**:
  * Implement an OAuth2 refresh token flow issuing single-use, rotating refresh tokens stored with cryptographically secure family tracking.
  * Maintain a Redis-backed session revocation list to immediately invalidate all active tokens when a user logs out, resets credentials, or has their account suspended.

#### D. Brute-Force Protection, Rate Limiting & Account Lockout
* **Current State**: Authentication and registration endpoints (`/auth/login`, `/users`) have no rate limiting or failed attempt tracking.
* **Next Phase Improvement**: Add IP-based and username-based rate limiting (via `slowapi` or Redis sliding-window limiters). Lock accounts temporarily after successive failed authentication attempts to protect against credential stuffing and brute-force attacks.

---

### 2. Authorization & Access Control Elements

As the identity provider for the platform, `users_api` is responsible for defining user privileges, assigning roles, and minting authorization claims into tokens.

#### A. Role Management & Claims Issuance (RBAC Core)
* **Current State**: The `users` model only stores identity attributes (`username`, `display_name`). Tokens contain only `sub` and `username`.
* **Next Phase Improvement**:
  * Add a `roles` table or schema enum (`user`, `admin`, `auditor`, `service_account`) and a user-role mapping in the database.
  * Embed active user roles directly into access token claims:
    ```json
    {
      "sub": "8c46002f-2c70-43be-8e01-1ad6b8408ec2",
      "username": "johndoe",
      "roles": ["user"],
      "permissions": ["tasks:read", "tasks:write"]
    }
    ```
  * Downstream services can immediately enforce role-based decisions without querying `users_api` on every request.

#### B. Permission Scopes Generation
* **Current State**: No concept of scopes or permissions exists in the authentication payload.
* **Next Phase Improvement**:
  * Map roles to granular permissions (e.g., `admin` -> `["tasks:*", "users:*"]`; `user` -> `["tasks:read", "tasks:write", "users:me"]`).
  * Add scope request negotiation to the `/auth/login` endpoint so clients can request minimal required privileges for specific sessions.

#### C. Account Lifecycle States & Access Invalidation
* **Current State**: Users are either present or deleted. There are no intermediate account states.
* **Next Phase Improvement**:
  * Add an `account_status` column to the `users` table (`active`, `suspended`, `pending_verification`, `locked`).
  * Reject login and refresh attempts for any user whose status is not `active`.
  * Broadcast `UserSuspended` events immediately to purge active sessions across the platform.

#### D. Administrative User Management Endpoints
* **Current State**: Any user can delete their username via `DELETE /users/{username}` without role verification. There is no administrative endpoint to list all users, view status, or reassign privileges.
* **Next Phase Improvement**:
  * Restrict user deletion and role assignment endpoints to callers with the `admin` role (`Depends(require_role("admin"))`).
  * Standardize user self-service actions under `/users/me` rather than arbitrary username path parameters.



