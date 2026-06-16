# SupplySync Inventory and Order Management Platform

SupplySync is a production-grade logistics and inventory backend built using **Django**, **Django REST Framework (DRF)**, **Celery**, and **Redis**. It handles inventory management across multiple warehouses, processes orders, and tracks purchase and sales lifecycles under high concurrency.

## Core Features & Architecture

1. **Service Layer Architecture**: Strictly decouples business logic from the HTTP representation layer. All mutations and database operations reside in dedicated `services.py` modules inside each app.
2. **Concurrency Control & Row-Level Locking**: Implements PostgreSQL's row-level locking via Django ORM's `select_for_update()` during critical operations like stock transfers and sales order placements to prevent double-spending or overselling.
3. **Event-Driven Asynchronous Processing**: Triggers background Celery workers for event logging, low stock alerting, and downstream actions when inventory modifications occur.
4. **Periodic Cron Jobs**: Integrated with **Celery Beat** for automated cache invalidation (low-stock reports) and daily operational summary logging.
5. **Redis Caching Strategy**: Caches read-heavy endpoints (product details, categories tree, warehouse summaries, dashboard analytics, low stock reports) with cache invalidation on mutations.
6. **Role-Based Access Control (RBAC)**: Enforces access restrictions for roles (`ADMIN`, `WAREHOUSE_MANAGER`, `PROCUREMENT_MANAGER`, and `STAFF`) via custom DRF permission classes.
7. **Rate Limiting**: Custom Redis-backed throttle (`LoginRateLimitThrottle`) restricting failed login attempts to 5 per IP address per 15-minute window.
8. **Unified Custom Exception Handler**: Catches all validation, business, and framework exceptions to return them in a standardized JSON error response schema.

---

## Technology Stack

- **Backend Framework**: Python (3.11/3.12/3.13) & Django 5.x
- **API Engine**: Django REST Framework (DRF) 3.15.x
- **Authentication**: Stateless Simple JWT (JSON Web Tokens)
- **Database**: PostgreSQL 15
- **Task Queue & Message Broker**: Celery & Redis
- **OpenAPI documentation**: drf-spectacular (Swagger UI / Redoc)
- **Testing**: pytest & pytest-django

---

## Local Development Setup

### 1. Prerequisite Infrastructure
Ensure Docker and Docker Compose are installed. Spin up the infrastructure services (PostgreSQL & Redis):

```bash
docker-compose up -d
```

### 2. Virtual Environment Setup
Initialize a Python virtual environment and install dependencies:

```bash
python -m venv venv
# On Windows
venv\Scripts\activate
# On macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
```

### 3. Running Database Migrations
Create schema migrations and apply them to the PostgreSQL database container:

```bash
python manage.py makemigrations
python manage.py migrate
```

### 4. Running the Development Server
Start the Django API application locally:

```bash
python manage.py runserver
```
The API will be available at `http://127.0.0.1:8000/`.

---

## API Documentation

The project auto-generates OpenAPI 3 schemas. Once the server is running, access the interactive docs:
- **Swagger UI**: [http://127.0.0.1:8000/api/schema/swagger-ui/](http://127.0.0.1:8000/api/schema/swagger-ui/)
- **Redoc**: [http://127.0.0.1:8000/api/schema/redoc/](http://127.0.0.1:8000/api/schema/redoc/)

---

## Running Automated Tests

Run the test suite using `pytest`:

```bash
pytest
```
Testing is configured via `pytest.ini` and runs against a clean SQLite database to keep executions fast and isolated.
