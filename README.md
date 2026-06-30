#  SupplySync: Inventory & Order Management Platform

## Overview

**SupplySync** is a production-ready backend application designed for inventory, warehouse, and order management. Built with **Django**, **Django REST Framework**, **PostgreSQL**, **Celery**, and **Redis**, it efficiently manages stock across multiple warehouses while supporting purchase and sales workflows in high-concurrency environments.

The project follows clean architectural principles with a strong focus on scalability, maintainability, and reliability.

---

#  Highlights

### Clean Service Layer Design

Business rules are completely separated from API views. All database updates and core business operations are handled inside dedicated `services.py` files, keeping the presentation layer lightweight and maintainable.

### Safe Concurrent Transactions

Critical inventory operations use PostgreSQL row-level locking through Django's `select_for_update()` to ensure stock consistency during events such as:

* Inventory transfers
* Sales order processing
* Stock deductions

This prevents race conditions, duplicate updates, and inventory overselling.

### Background Task Processing

Celery workers process asynchronous operations so that API requests remain fast. Background jobs include:

* Inventory event logging
* Low-stock notifications
* Post-processing after inventory changes
* Additional downstream business events

### Automated Scheduled Tasks

Celery Beat executes recurring jobs such as:

* Refreshing cached low-stock reports
* Generating daily operational summaries
* Performing routine maintenance tasks

### Intelligent Redis Caching

Frequently requested resources are cached to improve response times, including:

* Product information
* Category hierarchy
* Warehouse summaries
* Dashboard metrics
* Low-stock reports

Caches are automatically refreshed whenever related data changes.

### Role-Based Authorization

Access to APIs is protected using custom Django REST Framework permission classes with the following roles:

* ADMIN
* WAREHOUSE_MANAGER
* PROCUREMENT_MANAGER
* STAFF

Each role is granted only the permissions necessary for its responsibilities.

### Login Rate Limiting

Authentication endpoints implement a Redis-backed custom throttle (`LoginRateLimitThrottle`) that limits failed login attempts to **5 requests per IP address within a 15-minute window**, helping reduce brute-force attacks.

### Unified Error Responses

A centralized exception handler captures framework, validation, and business exceptions and returns them using a consistent JSON response structure across the API.

---

#  Technology Stack

| Category               | Technologies                         |
| ---------------------- | ------------------------------------ |
| Programming Language   | Python 3.11 / 3.12 / 3.13            |
| Backend Framework      | Django 5.x                           |
| REST API               | Django REST Framework 3.15.x         |
| Authentication         | Simple JWT                           |
| Database               | PostgreSQL 15                        |
| Cache & Message Broker | Redis                                |
| Background Processing  | Celery                               |
| API Documentation      | drf-spectacular (Swagger UI & Redoc) |
| Testing                | pytest, pytest-django                |

---

#  Local Development Guide

## Step 1: Start Infrastructure Services

Ensure **Docker** and **Docker Compose** are installed, then launch PostgreSQL and Redis containers.

```bash
docker-compose up -d
```

---

## Step 2: Create a Virtual Environment

```bash
python -m venv venv
```

Activate the environment:

**Windows**

```bash
venv\Scripts\activate
```

**macOS / Linux**

```bash
source venv/bin/activate
```

Install project dependencies:

```bash
pip install -r requirements.txt
```

---

## Step 3: Apply Database Migrations

Generate and execute migrations:

```bash
python manage.py makemigrations
python manage.py migrate
```

---

## Step 4: Launch the Development Server

Run the Django development server:

```bash
python manage.py runserver
```

The application will be available at:

```
http://127.0.0.1:8000/
```

---

# API Documentation

OpenAPI documentation is generated automatically.

Available interfaces:

**Swagger UI**

```
http://127.0.0.1:8000/api/schema/swagger-ui/
```

**Redoc**

```
http://127.0.0.1:8000/api/schema/redoc/
```

These interfaces allow developers to explore, test, and understand every available API endpoint.

---

# Running the Test Suite

Execute all automated tests with:

```bash
pytest
```

The project uses **pytest** together with **pytest-django**. Test execution is configured through `pytest.ini` and runs against an isolated SQLite database, enabling fast and repeatable test runs.
