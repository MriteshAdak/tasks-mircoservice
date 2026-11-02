# Tasks Microservice Platform

A decoupled microservices platform built with **FastAPI**, **SQLAlchemy 2.0**, and **PostgreSQL**. The platform separates domain concerns into dedicated services that share a single PostgreSQL database instance using schema-level isolation and stateless **JWT authentication**.

---

## Architecture Overview

```
                        ┌─────────────────────────────────────────┐
                        │              Client / Web UI            │
                        └──────────────┬──────────────────┬───────┘
                                       │                  │
                1. Register / Login    │                  │  2. Bearer <JWT>
                   (Get JWT Token)     │                  │     Task Operations
                                       ▼                  ▼
                    ┌──────────────────────┐  ┌──────────────────────┐
                    │      Users API       │  │      Tasks API       │
                    │   (Port: 8081)       │  │   (Port: 8082)       │
                    └──────────┬───────────┘  └──────────┬───────────┘
                               │                         │
             Shared JWT Secret │ (stateless verification)│ Shared JWT Secret
             `JWT_SECRET`      └─────────────┬───────────┘ `JWT_SECRET`
                                             │
                                             ▼
                               ┌───────────────────────────┐
                               │   PostgreSQL (Port 5435)  │
                               │   DB: task_microservices  │
                               ├─────────────┬─────────────┤
                               │ Schema:     │ Schema:     │
                               │ `users_api` │ `tasks_api` │
                               └─────────────┴─────────────┘
```

### Microservices

| Service | Port | Description | Documentation |
|---|---|---|---|
| **Users API** | `8081` | Manages user registrations, profiles, credentials, and issues JWT access tokens. | [Users API README](./users_api/README.md) |
| **Tasks API** | `8082` | Manages user tasks (CRUD, filtering, sorting, pagination) with stateless JWT authorization. | [Tasks API README](./tasks_api/README.md) |
| **Shared DB** | `5435` | PostgreSQL 16 instance with schema-isolated namespaces (`users_api` and `tasks_api`). | See `shared_db/docker-compose.yaml` |

---

## Repository Structure

```
tasks-mircoservice/
├── shared_db/
│   └── docker-compose.yaml     # Orchestrates PostgreSQL, migrations, and both APIs
├── users_api/                  # User identity & authentication service
│   ├── alembic/                # Database migrations for 'users_api' schema
│   ├── src/users_api/          # Application source code
│   ├── Dockerfile
│   ├── pyproject.toml
│   └── README.md               # Detailed Users API design & working
├── tasks_api/                  # Task management service
│   ├── alembic/                # Database migrations for 'tasks_api' schema
│   ├── src/tasks_api/          # Application source code
│   ├── Dockerfile
│   ├── pyproject.toml
│   └── README.md               # Detailed Tasks API design & working
└── README.md                   # Project overview & running instructions
```

---

## Running the Entire Platform

The simplest way to run all services together is using Docker Compose. It provisions PostgreSQL, automatically executes schema migrations for each service, and spins up both API servers with live reload.

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) & [Docker Compose](https://docs.docker.com/compose/)

### 1. Start Services

From the root directory:

```bash
docker compose -f shared_db/docker-compose.yaml up --build
```

*(Alternatively, `cd shared_db && docker compose up --build`)*

### 2. Service Startup Flow

1. **`postgres`** starts on port `5435` with database `task_microservices`.
2. **`user_api_migrate`** waits for Postgres health check, ensures the `users_api` schema exists, and applies Alembic migrations.
3. **`task_api_migrate`** waits for Postgres health check, ensures the `tasks_api` schema exists, and applies Alembic migrations.
4. **`user_api`** (port `8081`) and **`task_api`** (port `8082`) launch once their migrations succeed.

### 3. Verify Health

```bash
curl http://localhost:8081/health
curl http://localhost:8082/health
```

Both endpoints will return:
```json
{"status": "ok"}
```

Interactive API documentation (Swagger UI) is available at:
- **Users API:** [http://localhost:8081/docs](http://localhost:8081/docs)
- **Tasks API:** [http://localhost:8082/docs](http://localhost:8082/docs)

### 4. Stopping Services

```bash
# Stop containers
docker compose -f shared_db/docker-compose.yaml down

# Stop containers and wipe PostgreSQL volume
docker compose -f shared_db/docker-compose.yaml down -v
```

---

## Configuration

Top-level configuration defaults configured in `shared_db/docker-compose.yaml`:

| Variable | Default Value | Description |
|---|---|---|
| `POSTGRES_DB` | `task_microservices` | PostgreSQL database name |
| `POSTGRES_USER` | `postgres` | Database superuser |
| `POSTGRES_PASSWORD` | `allowing123` | Database password |
| `POSTGRES_PORT` | `5435` | Host port for PostgreSQL |
| `USER_API_PORT` | `8081` | Host port for Users API |
| `TASK_API_PORT` | `8082` | Host port for Tasks API |
| `USER_API_DB_SCHEMA` | `users_api` | Schema namespace for user tables |
| `TASK_API_DB_SCHEMA` | `tasks_api` | Schema namespace for task tables |
| `JWT_SECRET` | `dev-secret-key-change-in-prod` | Shared secret for signing & verifying JWTs |
| `JWT_ALGORITHM` | `HS256` | JWT signing algorithm |

---

## Improvements in Next Phase (Platform-Wide)

This section outlines platform-wide architectural, infrastructural, and cross-cutting improvements planned for upcoming phases, comparing current baselines against target industry standards.

### 1. Cross-Cutting Improvements

#### A. Asymmetric Authentication & Zero-Trust Token Verification
* **Current State**: Services share a single symmetric HMAC-SHA256 secret (`JWT_SECRET`). Any downstream service that validates tokens (`tasks_api`) also holds the secret key capable of forging valid authentication tokens for any identity across the platform.
* **Next Phase Improvement**: Migrate to asymmetric cryptography (`RS256` or `ES256`). `users_api` signs tokens with a private key, and consuming services verify tokens using a public key or dynamically via a `/.well-known/jwks.json` endpoint.

#### B. Asynchronous Database Drivers & Native Async I/O
* **Current State**: Both services use synchronous SQLAlchemy engines with `psycopg2-binary`. Synchronous route handlers execute within FastAPI's internal `anyio` threadpool worker, introducing thread context-switching overhead and limiting throughput under high concurrency.
* **Next Phase Improvement**: Standardize on `asyncpg` (`postgresql+asyncpg://`) with SQLAlchemy's `AsyncSession` and native `async def` route handlers across all services for non-blocking database I/O.

#### C. Database-per-Service Physical Decoupling
* **Current State**: Both microservices share a single PostgreSQL database container (`task_microservices`) isolated only by schema (`users_api`, `tasks_api`). A database outage, connection saturation, or CPU spike in one service directly degrades the other.
* **Next Phase Improvement**: Separate the schemas into distinct database instances (or dedicated managed database clusters in production) to achieve true operational fault-isolation and independent horizontal scaling.

#### D. Event-Driven Inter-Service Messaging
* **Current State**: There is no message broker or inter-service communication bus. When a user is deleted in `users_api`, `tasks_api` is unaware, leaving orphaned task records.
* **Next Phase Improvement**: Deploy a message broker (RabbitMQ, Redis Streams, or AWS SQS/SNS) with transactional outbox publishing. `users_api` will publish domain events (`UserRegistered`, `UserDeleted`), and `tasks_api` will consume them to orchestrate cascading actions asynchronously.

#### E. Distributed Tracing & Observability
* **Current State**: `asgi-correlation-id` and `structlog` exist in dependencies but are not wired into the application pipelines. Requests across service boundaries cannot be traced or correlated in log aggregators.
* **Next Phase Improvement**: Wire `CorrelationIdMiddleware` into all services, propagate `X-Request-ID` across HTTP and event boundaries, and format all logs as structured JSON containing `request_id`, `service`, and `user_id`.

#### F. Standardized Health & Readiness Probes
* **Current State**: Both services expose a static `/health` endpoint returning `{"status": "ok"}` without testing database connectivity. Broken instances continue receiving traffic.
* **Next Phase Improvement**: Implement standard dual-probe health checks:
  * `/health/live`: Fast process liveness check.
  * `/health/ready`: Deep dependency readiness check performing a `SELECT 1` database query before accepting traffic.

#### G. Automated Testing & Quality Gates
* **Current State**: Zero automated tests exist in the repository despite `pytest` being configured in `pyproject.toml`.
* **Next Phase Improvement**: Implement unit test suites (with mock repositories) and integration test suites (using `httpx.AsyncClient` with ephemeral PostgreSQL containers via `testcontainers-python`), integrated into automated CI/CD quality gates.

---

### 2. Authorization & Access Control Architecture

The current architecture provides **authentication** (verifying *who* the caller is) but lacks an extensible **authorization and access control framework** (governing *what* the caller is permitted to do). The following additions will be introduced in the next phase:

```
┌────────────────────────────────────────────────────────────────────────┐
│                          Access Control Flow                           │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
                ┌───────────────────────────────────────┐
                │        Client Request with JWT        │
                │ Claims: sub, username, roles, scopes  │
                └───────────────────┬───────────────────┘
                                    │
                                    ▼
                ┌───────────────────────────────────────┐
                │          FastAPI Dependencies         │
                │  1. Token Signature Verification      │
                │  2. Scope Enforcement (e.g. tasks:write)
                │  3. Role Verification (e.g. admin)    │
                └───────────────────┬───────────────────┘
                                    │
                                    ▼
                ┌───────────────────────────────────────┐
                │      Domain Policy Enforcement        │
                │  ABAC: Resource Owner vs Delegate     │
                │  Tenant / Organization Scoping        │
                └───────────────────────────────────────┘
```

#### A. Role-Based Access Control (RBAC)
* **Current State**: Binary authorization (authenticated caller vs. anonymous caller). Every authenticated user has the exact same permissions, and there is no concept of administrative roles, managers, or auditors.
* **Next Phase Improvement**:
  * Introduce formal user roles (`user`, `admin`, `auditor`, `system`).
  * Persist roles in `users_api` and embed an active `roles: list[str]` claim into the JWT access token.
  * Implement reusable FastAPI dependencies (e.g., `Depends(require_role("admin"))`) to guard administrative and sensitive endpoints.

#### B. Fine-Grained Permission Scopes (OAuth2-style Scopes)
* **Current State**: Access tokens grant unrestricted access to all endpoints belonging to the caller's ID without granular permission boundaries.
* **Next Phase Improvement**:
  * Implement permission scopes within tokens (e.g., `scopes: ["tasks:read", "tasks:write", "users:profile"]`).
  * Enforce scopes per route using FastAPI's `Security(get_current_user, scopes=["tasks:write"])`.
  * Support third-party API clients and service-to-service accounts with restricted least-privilege scopes.

#### C. Attribute-Based & Policy-Based Access Control (ABAC / PBAC)
* **Current State**: Resource authorization is hardcoded directly into repository SQL filters (`WHERE id = :id AND user_id = :user_id`). This cannot accommodate collaborative features, shared tasks, or hierarchical access.
* **Next Phase Improvement**:
  * Introduce an explicit Policy Evaluation layer (e.g., Casbin or domain policy handlers).
  * Support attribute-based rules:
    * **Task Collaboration**: Allow access if `user_id == task.owner_id` OR `user_id IN task.collaborator_ids`.
    * **Tenant/Team Scoping**: Support organizational or team isolation (`team_id = :team_id`).
    * **State-Based Restrictions**: Disallow edits or deletions on tasks marked with `status = "archived"` or `status = "locked"`.

#### D. Admin Elevation & Cross-User Auditing
* **Current State**: `tasks_api` returns a strict `404 Not Found` for any task where `task.user_id != token.sub`. Administrators cannot view, reassign, or troubleshoot user tasks.
* **Next Phase Improvement**:
  * Allow callers with the `admin` role or `tasks:admin` scope to bypass user-level filtering while automatically producing structured security audit logs for compliance tracking.

---

## Individual Service Documentation

For in-depth details on architecture, internal layers, schemas, endpoints, and running each service independently:

- [Users API Documentation](./users_api/README.md)
- [Tasks API Documentation](./tasks_api/README.md)
