# Fitness Tracker API System

A premium FastAPI-based fitness tracking backend with PostgreSQL persistence, JWT authentication, interactive web dashboard, and complete CRUD capabilities. Built with OOP principles and aligned with **SDG 3 (Good Health and Well-being)**.

---

## Project Structure

```
fitness-tracker/
├── main.py              # FastAPI application (all routes, ORM models, auth)
├── database.py          # PostgreSQL connection, SQLAlchemy engine & session
├── test_api.py          # Automated test suite for all 17 endpoints
├── generate_report.py   # Generates hard copy.docx assignment report
├── requirements.txt     # All Python dependencies
├── .gitignore           # Git exclusions
├── README.md            # This file
└── SWAGGER_GUIDE.md     # Step-by-step Swagger UI interaction guide
```

---

## Features

- **17 REST API Endpoints** — Full CRUD for workouts and goals, plus progress tracking
- **PostgreSQL Database** — Persistent storage via SQLAlchemy ORM
- **JWT Authentication** — Secure user registration and login with token-based auth
- **Interactive Dashboard** — Dark-themed web UI served at `http://127.0.0.1:8000/`
- **Swagger UI** — Auto-generated docs at `http://127.0.0.1:8000/docs`
- **Async Design** — All endpoints use `async/await` for non-blocking execution

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| Framework | FastAPI |
| Database | PostgreSQL + SQLAlchemy |
| Auth | JWT (python-jose) + passlib |
| Server | Uvicorn |
| Validation | Pydantic v2 |

---

## Setup & Installation

### 1. Prerequisites
- Python 3.10+
- PostgreSQL running locally with a database named `FitnessTracker`
- A virtual environment (this project uses the one in `../awesome-project/venv/`)

### 2. Install Dependencies
```powershell
..\awesome-project\venv\Scripts\python -m pip install -r requirements.txt
```

### 3. Configure the Database
The database connection is set in `database.py`:
```python
DATABASE_URL = "postgresql://postgres:alpha@localhost/FitnessTracker"
```
Update `alpha` to your PostgreSQL password if different.

### 4. Run the Server
```powershell
..\awesome-project\venv\Scripts\python -m uvicorn main:app --reload
```

### 5. Access the API
| URL | Description |
|-----|-------------|
| http://127.0.0.1:8000/ | Interactive Web Dashboard |
| http://127.0.0.1:8000/docs | Swagger UI (API Documentation) |

---

## API Endpoints

### Auth
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/register` | Register a new user |
| `POST` | `/token` | Login and get JWT access token |
| `GET` | `/users` | List all users |
| `GET` | `/users/me` | Get current authenticated user (requires token) |

### Workouts
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/workouts` | Log a new workout |
| `GET` | `/workouts` | List all workouts (filter by `activity_type`, `min_duration`) |
| `GET` | `/workouts/{id}` | Get a single workout by ID |
| `PUT` | `/workouts/{id}` | Update an existing workout |
| `DELETE` | `/workouts/{id}` | Delete a workout |

### Goals
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/goals` | Set a daily fitness goal |
| `GET` | `/goals` | List all goals (filter by `user_id`) |
| `GET` | `/goals/{id}` | Get a single goal by ID |
| `PUT` | `/goals/{id}` | Update an existing goal |
| `DELETE` | `/goals/{id}` | Delete a goal |

### Progress
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/progress/{user_id}` | Daily summary with goal completion percentages |

### Dashboard
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Interactive web dashboard |

---

## Running the Tests

The automated test suite covers all 17 endpoints:
```powershell
..\awesome-project\venv\Scripts\python test_api.py
```

---

## Generating the Assignment Report

Run this script to compile `hard copy.docx` — the formatted coursework document:
```powershell
..\awesome-project\venv\Scripts\python generate_report.py
```

---

## GitHub Setup

```bash
git init
git add .
git commit -m "Initial commit: Fitness Tracker API with PostgreSQL and JWT Auth"
```

---

## SDG Alignment

This project supports **SDG 3 — Good Health and Well-being** by providing the digital infrastructure for individuals to track physical activity, set measurable goals, and monitor progress over time — promoting consistent healthy habits through accessible technology.

