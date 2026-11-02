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

## Individual Service Documentation

For in-depth details on architecture, internal layers, schemas, endpoints, and running each service independently:

- [Users API Documentation](./users_api/README.md)
- [Tasks API Documentation](./tasks_api/README.md)
