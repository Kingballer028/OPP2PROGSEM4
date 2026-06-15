from fastapi import FastAPI, HTTPException, Query, Depends, status
from fastapi.responses import HTMLResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
import asyncio
from datetime import datetime, date, timedelta
from contextlib import asynccontextmanager
from jose import JWTError, jwt
from passlib.context import CryptContext

from sqlalchemy import Column, Integer, String, Date, Boolean
from sqlalchemy.orm import Session
from database import Base, engine, get_db, SessionLocal

# --- Auth Configuration ---
SECRET_KEY = "fitness-tracker-secret-key-2026"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

pwd_context = CryptContext(schemes=["sha256_crypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)

def create_access_token(data: dict, expires_delta=None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user_from_token(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = db.query(UserDB).filter(UserDB.username == username).first()
    if user is None:
        raise credentials_exception
    return user

# --- ORM Models (SQLAlchemy) ---

class UserDB(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)

class WorkoutDB(Base):
    __tablename__ = "workouts"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    activity_type = Column(String, index=True)
    duration_minutes = Column(Integer)
    calories_burned = Column(Integer)
    date_logged = Column(Date, default=date.today)

class GoalDB(Base):
    __tablename__ = "goals"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    goal_type = Column(String)  # 'calories' or 'duration'
    target_value = Column(Integer)
    date_set = Column(Date, default=date.today)

# Create tables immediately on module import
Base.metadata.create_all(bind=engine)

# --- Pydantic Schemas (FastAPI validation) ---

class Workout(BaseModel):
    id: int
    user_id: int
    activity_type: str = Field(..., example="Running")
    duration_minutes: int = Field(..., gt=0, example=30)
    calories_burned: int = Field(..., gt=0, example=300)
    date_logged: date = Field(default_factory=date.today)

    class Config:
        from_attributes = True
        orm_mode = True

class Goal(BaseModel):
    id: int
    user_id: int
    goal_type: str = Field(..., example="calories", description="Either 'calories' or 'duration'")
    target_value: int = Field(..., gt=0, example=500)
    date_set: date = Field(default_factory=date.today)

    class Config:
        from_attributes = True
        orm_mode = True

class ProgressSummary(BaseModel):
    user_id: int
    date: date
    total_workouts: int
    total_duration_minutes: int
    total_calories_burned: int
    goals: List[Dict]

class User(BaseModel):
    id: int
    username: str
    is_active: bool

    class Config:
        from_attributes = True
        orm_mode = True

class Token(BaseModel):
    access_token: str
    token_type: str


# --- Tracker Manager (OOP Logic & Database Operations) ---

class FitnessTrackerManager:
    async def log_workout(self, db: Session, user_id: int, activity_type: str, duration_minutes: int, calories_burned: int, date_logged: Optional[date] = None) -> WorkoutDB:
        # Simulate latency
        await asyncio.sleep(0.5)
        
        target_date = date_logged or date.today()
        workout = WorkoutDB(
            user_id=user_id,
            activity_type=activity_type,
            duration_minutes=duration_minutes,
            calories_burned=calories_burned,
            date_logged=target_date
        )
        db.add(workout)
        db.commit()
        db.refresh(workout)
        return workout

    async def get_workouts(self, db: Session, activity_type: Optional[str] = None, min_duration: Optional[int] = None) -> List[WorkoutDB]:
        await asyncio.sleep(0.2)
        query = db.query(WorkoutDB)
        
        if activity_type:
            query = query.filter(WorkoutDB.activity_type.ilike(activity_type))
        if min_duration:
            query = query.filter(WorkoutDB.duration_minutes >= min_duration)
            
        return query.all()

    async def set_goal(self, db: Session, user_id: int, goal_type: str, target_value: int, date_set: Optional[date] = None) -> GoalDB:
        await asyncio.sleep(0.5)
        if goal_type.lower() not in ["calories", "duration"]:
            raise ValueError("Goal type must be either 'calories' or 'duration'.")
            
        target_date = date_set or date.today()
        goal = GoalDB(
            user_id=user_id,
            goal_type=goal_type.lower(),
            target_value=target_value,
            date_set=target_date
        )
        db.add(goal)
        db.commit()
        db.refresh(goal)
        return goal

    async def get_progress(self, db: Session, user_id: int, target_date: Optional[date] = None) -> ProgressSummary:
        await asyncio.sleep(0.5)
        eval_date = target_date or date.today()
        
        # Query workouts on date
        user_workouts = db.query(WorkoutDB).filter(
            WorkoutDB.user_id == user_id,
            WorkoutDB.date_logged == eval_date
        ).all()
        
        total_workouts = len(user_workouts)
        total_duration = sum(w.duration_minutes for w in user_workouts)
        total_calories = sum(w.calories_burned for w in user_workouts)
        
        # Query goals on date
        user_goals = db.query(GoalDB).filter(
            GoalDB.user_id == user_id,
            GoalDB.date_set == eval_date
        ).all()
        
        goals_progress = []
        for goal in user_goals:
            current_value = 0
            if goal.goal_type == "calories":
                current_value = total_calories
            elif goal.goal_type == "duration":
                current_value = total_duration
                
            achieved = current_value >= goal.target_value
            progress_pct = min(100.0, (current_value / goal.target_value) * 100.0) if goal.target_value > 0 else 0.0
            
            goals_progress.append({
                "goal_id": goal.id,
                "goal_type": goal.goal_type,
                "target_value": goal.target_value,
                "current_value": current_value,
                "progress_percentage": round(progress_pct, 2),
                "achieved": achieved
            })
            
        return ProgressSummary(
            user_id=user_id,
            date=eval_date,
            total_workouts=total_workouts,
            total_duration_minutes=total_duration,
            total_calories_burned=total_calories,
            goals=goals_progress
        )

# Instantiate our tracker manager
tracker_manager = FitnessTrackerManager()

# --- Lifespan startup/shutdown ---

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Pre-populate default sample database data for User 101 if empty
    db = SessionLocal()
    try:
        user_101_exists = db.query(WorkoutDB).filter(WorkoutDB.user_id == 101).first()
        if not user_101_exists:
            await tracker_manager.log_workout(db, 101, "Running", 30, 320, date.today())
            await tracker_manager.log_workout(db, 101, "Yoga", 45, 150, date.today())
            await tracker_manager.set_goal(db, 101, "calories", 500, date.today())
            await tracker_manager.set_goal(db, 101, "duration", 60, date.today())
    finally:
        db.close()
    yield

app = FastAPI(
    title="Fitness Tracker API", 
    description="An API to log workout activities, set goals, and monitor progress, designed for OOP and SDG 3 alignment.",
    lifespan=lifespan
)

import time
from fastapi import Request

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    # Print formatted request log to the terminal console
    print(f"INFO:     REQUEST: {request.method} {request.url.path} - STATUS: {response.status_code} ({duration:.3f}s)", flush=True)
    return response


# --- Request Schemas ---

class WorkoutCreate(BaseModel):
    user_id: int = Field(..., example=101)
    activity_type: str = Field(..., example="Running")
    duration_minutes: int = Field(..., gt=0, example=45)
    calories_burned: int = Field(..., gt=0, example=400)
    date_logged: Optional[date] = Field(default=None, description="YYYY-MM-DD. Defaults to today.")

class GoalCreate(BaseModel):
    user_id: int = Field(..., example=101)
    goal_type: str = Field(..., example="calories", description="Either 'calories' or 'duration'")
    target_value: int = Field(..., gt=0, example=500)
    date_set: Optional[date] = Field(default=None, description="YYYY-MM-DD. Defaults to today.")

class WorkoutUpdate(BaseModel):
    activity_type: Optional[str] = Field(None, example="Cycling")
    duration_minutes: Optional[int] = Field(None, gt=0, example=45)
    calories_burned: Optional[int] = Field(None, gt=0, example=400)
    date_logged: Optional[date] = None

class GoalUpdate(BaseModel):
    goal_type: Optional[str] = Field(None, example="duration")
    target_value: Optional[int] = Field(None, gt=0, example=90)
    date_set: Optional[date] = None

class UserCreate(BaseModel):
    username: str = Field(..., example="alice")
    password: str = Field(..., example="securepassword123")


# --- API Endpoints ---

@app.post("/workouts", response_model=Workout, status_code=201)
async def log_workout(workout_data: WorkoutCreate, db: Session = Depends(get_db)):
    try:
        workout = await tracker_manager.log_workout(
            db=db,
            user_id=workout_data.user_id,
            activity_type=workout_data.activity_type,
            duration_minutes=workout_data.duration_minutes,
            calories_burned=workout_data.calories_burned,
            date_logged=workout_data.date_logged
        )
        return workout
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/workouts", response_model=List[Workout])
async def get_workouts(
    activity_type: Optional[str] = Query(None, description="Filter by type of activity"),
    min_duration: Optional[int] = Query(None, description="Filter workouts with duration greater than or equal to this (in minutes)"),
    db: Session = Depends(get_db)
):
    return await tracker_manager.get_workouts(db=db, activity_type=activity_type, min_duration=min_duration)

@app.post("/goals", response_model=Goal, status_code=201)
async def set_goal(goal_data: GoalCreate, db: Session = Depends(get_db)):
    try:
        goal = await tracker_manager.set_goal(
            db=db,
            user_id=goal_data.user_id,
            goal_type=goal_data.goal_type,
            target_value=goal_data.target_value,
            date_set=goal_data.date_set
        )
        return goal
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/progress/{user_id}", response_model=ProgressSummary)
async def get_progress(
    user_id: int,
    date_query: Optional[date] = Query(None, alias="date", description="Query date in YYYY-MM-DD. Defaults to today."),
    db: Session = Depends(get_db)
):
    try:
        summary = await tracker_manager.get_progress(db=db, user_id=user_id, target_date=date_query)
        return summary
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# --- Workouts: GET by ID, UPDATE, DELETE ---

@app.get("/workouts/{workout_id}", response_model=Workout, tags=["Workouts"])
async def get_workout_by_id(workout_id: int, db: Session = Depends(get_db)):
    """Retrieve a single workout by its ID."""
    workout = db.query(WorkoutDB).filter(WorkoutDB.id == workout_id).first()
    if not workout:
        raise HTTPException(status_code=404, detail=f"Workout with ID {workout_id} not found.")
    return workout

@app.put("/workouts/{workout_id}", response_model=Workout, tags=["Workouts"])
async def update_workout(workout_id: int, update_data: WorkoutUpdate, db: Session = Depends(get_db)):
    """Update an existing workout's details."""
    workout = db.query(WorkoutDB).filter(WorkoutDB.id == workout_id).first()
    if not workout:
        raise HTTPException(status_code=404, detail=f"Workout with ID {workout_id} not found.")
    if update_data.activity_type is not None:
        workout.activity_type = update_data.activity_type
    if update_data.duration_minutes is not None:
        workout.duration_minutes = update_data.duration_minutes
    if update_data.calories_burned is not None:
        workout.calories_burned = update_data.calories_burned
    if update_data.date_logged is not None:
        workout.date_logged = update_data.date_logged
    db.commit()
    db.refresh(workout)
    return workout

@app.delete("/workouts/{workout_id}", status_code=204, tags=["Workouts"])
async def delete_workout(workout_id: int, db: Session = Depends(get_db)):
    """Delete a workout by its ID."""
    workout = db.query(WorkoutDB).filter(WorkoutDB.id == workout_id).first()
    if not workout:
        raise HTTPException(status_code=404, detail=f"Workout with ID {workout_id} not found.")
    db.delete(workout)
    db.commit()

# --- Goals: LIST ALL, GET by ID, UPDATE, DELETE ---

@app.get("/goals", response_model=List[Goal], tags=["Goals"])
async def get_all_goals(
    user_id: Optional[int] = Query(None, description="Filter goals by user ID"),
    db: Session = Depends(get_db)
):
    """Retrieve all goals, optionally filtered by user."""
    query = db.query(GoalDB)
    if user_id:
        query = query.filter(GoalDB.user_id == user_id)
    return query.all()

@app.get("/goals/{goal_id}", response_model=Goal, tags=["Goals"])
async def get_goal_by_id(goal_id: int, db: Session = Depends(get_db)):
    """Retrieve a single goal by its ID."""
    goal = db.query(GoalDB).filter(GoalDB.id == goal_id).first()
    if not goal:
        raise HTTPException(status_code=404, detail=f"Goal with ID {goal_id} not found.")
    return goal

@app.put("/goals/{goal_id}", response_model=Goal, tags=["Goals"])
async def update_goal(goal_id: int, update_data: GoalUpdate, db: Session = Depends(get_db)):
    """Update an existing goal."""
    goal = db.query(GoalDB).filter(GoalDB.id == goal_id).first()
    if not goal:
        raise HTTPException(status_code=404, detail=f"Goal with ID {goal_id} not found.")
    if update_data.goal_type is not None:
        if update_data.goal_type.lower() not in ["calories", "duration"]:
            raise HTTPException(status_code=400, detail="goal_type must be 'calories' or 'duration'.")
        goal.goal_type = update_data.goal_type.lower()
    if update_data.target_value is not None:
        goal.target_value = update_data.target_value
    if update_data.date_set is not None:
        goal.date_set = update_data.date_set
    db.commit()
    db.refresh(goal)
    return goal

@app.delete("/goals/{goal_id}", status_code=204, tags=["Goals"])
async def delete_goal(goal_id: int, db: Session = Depends(get_db)):
    """Delete a goal by its ID."""
    goal = db.query(GoalDB).filter(GoalDB.id == goal_id).first()
    if not goal:
        raise HTTPException(status_code=404, detail=f"Goal with ID {goal_id} not found.")
    db.delete(goal)
    db.commit()

# --- Users: REGISTER, LOGIN, LIST ---

@app.post("/register", response_model=User, status_code=201, tags=["Auth"])
async def register_user(user_data: UserCreate, db: Session = Depends(get_db)):
    """Register a new user account."""
    existing = db.query(UserDB).filter(UserDB.username == user_data.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already registered.")
    user = UserDB(
        username=user_data.username,
        hashed_password=hash_password(user_data.password)
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@app.post("/token", response_model=Token, tags=["Auth"])
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Login with username and password to receive a JWT access token."""
    user = db.query(UserDB).filter(UserDB.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token(data={"sub": user.username})
    return {"access_token": token, "token_type": "bearer"}

@app.get("/users", response_model=List[User], tags=["Auth"])
async def get_all_users(db: Session = Depends(get_db)):
    """List all registered users."""
    return db.query(UserDB).all()

@app.get("/users/me", response_model=User, tags=["Auth"])
async def get_current_user(current_user: UserDB = Depends(get_current_user_from_token)):
    """Get the currently authenticated user's profile."""
    return current_user


# --- Interactive Web Frontend Dashboard ---

@app.get("/", response_class=HTMLResponse)
async def get_dashboard():
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>FitTrack - Premium Fitness Tracker Dashboard</title>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Outfit:wght@400;500;600;700&display=swap" rel="stylesheet">
        <style>
            :root {
                --bg-color: #080b11;
                --card-bg: rgba(17, 24, 39, 0.7);
                --primary: #3b82f6;
                --primary-glow: rgba(59, 130, 246, 0.15);
                --accent: #10b981;
                --accent-glow: rgba(16, 185, 129, 0.15);
                --text: #f3f4f6;
                --text-muted: #9ca3af;
                --border: rgba(255, 255, 255, 0.07);
                --card-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
            }

            * {
                box-sizing: border-box;
                margin: 0;
                padding: 0;
            }

            body {
                font-family: 'Inter', sans-serif;
                background-color: var(--bg-color);
                color: var(--text);
                min-height: 100vh;
                display: flex;
                flex-direction: column;
                background-image: radial-gradient(circle at 10% 20%, rgba(59, 130, 246, 0.08) 0%, transparent 40%),
                                  radial-gradient(circle at 90% 80%, rgba(16, 185, 129, 0.06) 0%, transparent 40%);
            }

            header {
                padding: 20px 40px;
                border-bottom: 1px solid var(--border);
                backdrop-filter: blur(12px);
                background-color: rgba(8, 11, 17, 0.8);
                position: sticky;
                top: 0;
                z-index: 10;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }

            h1, h2, h3 {
                font-family: 'Outfit', sans-serif;
            }

            .logo {
                font-size: 24px;
                font-weight: 700;
                background: linear-gradient(135deg, #3b82f6 0%, #10b981 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                display: flex;
                align-items: center;
                gap: 8px;
            }

            .logo span {
                font-size: 14px;
                padding: 2px 8px;
                border-radius: 20px;
                background: rgba(59, 130, 246, 0.15);
                color: var(--primary);
                -webkit-text-fill-color: initial;
            }

            .user-selector {
                display: flex;
                align-items: center;
                gap: 12px;
            }

            .user-selector label {
                font-size: 14px;
                color: var(--text-muted);
            }

            .user-selector select {
                background-color: rgba(255, 255, 255, 0.05);
                color: var(--text);
                border: 1px solid var(--border);
                padding: 8px 16px;
                border-radius: 8px;
                outline: none;
                font-weight: 500;
                cursor: pointer;
                transition: all 0.3s;
            }

            .user-selector select:focus {
                border-color: var(--primary);
                box-shadow: 0 0 0 2px var(--primary-glow);
            }

            main {
                flex: 1;
                padding: 40px;
                max-width: 1400px;
                width: 100%;
                margin: 0 auto;
                display: flex;
                flex-direction: column;
                gap: 30px;
            }

            .summary-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
                gap: 20px;
            }

            .summary-card {
                background: var(--card-bg);
                backdrop-filter: blur(16px);
                border: 1px solid var(--border);
                border-radius: 16px;
                padding: 24px;
                display: flex;
                align-items: center;
                gap: 20px;
                box-shadow: var(--card-shadow);
                position: relative;
                overflow: hidden;
                transition: transform 0.3s, box-shadow 0.3s;
            }

            .summary-card:hover {
                transform: translateY(-4px);
                box-shadow: 0 12px 40px 0 rgba(0, 0, 0, 0.5);
            }

            .card-icon {
                width: 56px;
                height: 56px;
                border-radius: 12px;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 24px;
            }

            .summary-card.workouts .card-icon {
                background-color: var(--primary-glow);
                color: var(--primary);
            }

            .summary-card.calories .card-icon {
                background-color: rgba(239, 68, 68, 0.1);
                color: #ef4444;
            }

            .summary-card.duration .card-icon {
                background-color: var(--accent-glow);
                color: var(--accent);
            }

            .card-info h3 {
                font-size: 14px;
                color: var(--text-muted);
                text-transform: uppercase;
                letter-spacing: 0.05em;
                margin-bottom: 4px;
            }

            .card-info p {
                font-size: 28px;
                font-weight: 700;
                font-family: 'Outfit', sans-serif;
            }

            .card-glow {
                position: absolute;
                bottom: -20px;
                right: -20px;
                width: 80px;
                height: 80px;
                border-radius: 50%;
                filter: blur(40px);
                opacity: 0.15;
            }

            .workouts .card-glow { background-color: var(--primary); }
            .calories .card-glow { background-color: #ef4444; }
            .duration .card-glow { background-color: var(--accent); }

            .dashboard-layout {
                display: grid;
                grid-template-columns: 1fr 1.5fr;
                gap: 30px;
            }

            @media (max-width: 1024px) {
                .dashboard-layout {
                    grid-template-columns: 1fr;
                }
            }

            .form-column {
                display: flex;
                flex-direction: column;
                gap: 30px;
            }

            .glass-panel {
                background: var(--card-bg);
                backdrop-filter: blur(16px);
                border: 1px solid var(--border);
                border-radius: 16px;
                padding: 30px;
                box-shadow: var(--card-shadow);
            }

            .panel-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 24px;
            }

            .panel-header h2 {
                font-size: 20px;
                font-weight: 600;
                display: flex;
                align-items: center;
                gap: 10px;
            }

            .form-group {
                margin-bottom: 20px;
            }

            .form-group label {
                display: block;
                font-size: 14px;
                color: var(--text-muted);
                margin-bottom: 8px;
                font-weight: 500;
            }

            .form-group input, .form-group select {
                width: 100%;
                background-color: rgba(255, 255, 255, 0.04);
                border: 1px solid var(--border);
                color: var(--text);
                padding: 12px 16px;
                border-radius: 8px;
                font-family: inherit;
                font-size: 15px;
                outline: none;
                transition: all 0.3s;
            }

            .form-group input:focus, .form-group select:focus {
                border-color: var(--primary);
                background-color: rgba(255, 255, 255, 0.07);
                box-shadow: 0 0 0 2px var(--primary-glow);
            }

            .btn {
                width: 100%;
                background: linear-gradient(135deg, var(--primary) 0%, #2563eb 100%);
                color: white;
                border: none;
                padding: 14px;
                border-radius: 8px;
                font-weight: 600;
                font-size: 15px;
                cursor: pointer;
                transition: all 0.3s;
                font-family: 'Outfit', sans-serif;
                box-shadow: 0 4px 12px rgba(37, 99, 235, 0.2);
            }

            .btn:hover {
                transform: translateY(-2px);
                box-shadow: 0 6px 20px rgba(37, 99, 235, 0.35);
            }

            .btn-accent {
                background: linear-gradient(135deg, var(--accent) 0%, #059669 100%);
                box-shadow: 0 4px 12px rgba(16, 185, 129, 0.2);
            }

            .btn-accent:hover {
                box-shadow: 0 6px 20px rgba(16, 185, 129, 0.35);
            }

            .goal-item {
                background: rgba(255, 255, 255, 0.02);
                border: 1px solid var(--border);
                border-radius: 12px;
                padding: 16px;
                margin-bottom: 16px;
            }

            .goal-meta {
                display: flex;
                justify-content: space-between;
                margin-bottom: 8px;
                font-size: 14px;
            }

            .goal-title {
                font-weight: 600;
                text-transform: capitalize;
            }

            .goal-target {
                color: var(--text-muted);
            }

            .progress-container {
                width: 100%;
                height: 10px;
                background-color: rgba(255, 255, 255, 0.05);
                border-radius: 5px;
                overflow: hidden;
                position: relative;
                margin-bottom: 8px;
            }

            .progress-bar {
                height: 100%;
                border-radius: 5px;
                transition: width 0.8s cubic-bezier(0.4, 0, 0.2, 1);
            }

            .goal-item.achieved .progress-bar {
                background: linear-gradient(90deg, #10b981, #34d399);
                box-shadow: 0 0 8px rgba(16, 185, 129, 0.5);
            }

            .goal-item.in-progress .progress-bar {
                background: linear-gradient(90deg, #3b82f6, #60a5fa);
            }

            .goal-status {
                display: flex;
                justify-content: space-between;
                font-size: 12px;
            }

            .status-badge {
                padding: 2px 6px;
                border-radius: 4px;
                font-size: 10px;
                font-weight: 700;
                letter-spacing: 0.05em;
            }

            .achieved .status-badge {
                background-color: rgba(16, 185, 129, 0.15);
                color: var(--accent);
            }

            .in-progress .status-badge {
                background-color: rgba(59, 130, 246, 0.15);
                color: var(--primary);
            }

            .table-container {
                overflow-x: auto;
            }

            table {
                width: 100%;
                border-collapse: collapse;
                text-align: left;
            }

            th, td {
                padding: 14px 16px;
                border-bottom: 1px solid var(--border);
            }

            th {
                color: var(--text-muted);
                font-weight: 500;
                font-size: 14px;
                text-transform: uppercase;
                letter-spacing: 0.05em;
            }

            td {
                font-size: 15px;
            }

            tr:last-child td {
                border-bottom: none;
            }

            .badge-activity {
                padding: 4px 10px;
                border-radius: 20px;
                font-size: 12px;
                font-weight: 500;
                display: inline-block;
                background-color: rgba(255, 255, 255, 0.05);
                border: 1px solid var(--border);
            }

            .running { color: #3b82f6; border-color: rgba(59, 130, 246, 0.3); background-color: rgba(59, 130, 246, 0.05); }
            .cycling { color: #f59e0b; border-color: rgba(245, 158, 11, 0.3); background-color: rgba(245, 158, 11, 0.05); }
            .swimming { color: #06b6d4; border-color: rgba(6, 182, 212, 0.3); background-color: rgba(6, 182, 212, 0.05); }
            .yoga { color: #a855f7; border-color: rgba(168, 85, 247, 0.3); background-color: rgba(168, 85, 247, 0.05); }

            .no-data {
                text-align: center;
                padding: 40px;
                color: var(--text-muted);
                font-style: italic;
            }

            .toast-container {
                position: fixed;
                bottom: 20px;
                right: 20px;
                z-index: 100;
                display: flex;
                flex-direction: column;
                gap: 10px;
            }

            .toast {
                background: rgba(17, 24, 39, 0.9);
                border-left: 4px solid var(--primary);
                color: var(--text);
                padding: 16px 20px;
                border-radius: 8px;
                box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.5);
                backdrop-filter: blur(8px);
                min-width: 280px;
                transform: translateX(120%);
                transition: transform 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
                display: flex;
                justify-content: space-between;
                align-items: center;
            }

            .toast.show {
                transform: translateX(0);
            }

            .toast.success {
                border-left-color: var(--accent);
            }

            .toast.error {
                border-left-color: #ef4444;
            }
        </style>
    </head>
    <body>
        <header>
            <div class="logo">FitTrack <span>Active</span></div>
            <div class="user-selector">
                <label for="userSelect">User Profile</label>
                <select id="userSelect" onchange="loadDashboard()">
                    <option value="101" selected>User 101 (Demo Profile)</option>
                    <option value="102">User 102</option>
                    <option value="999">User 999 (Test Suite Profile)</option>
                </select>
            </div>
        </header>

        <main>
            <!-- Summary Stats Cards -->
            <div class="summary-grid">
                <div class="summary-card workouts">
                    <div class="card-icon">🏃</div>
                    <div class="card-info">
                        <h3>Workouts Today</h3>
                        <p id="statWorkouts">0</p>
                    </div>
                    <div class="card-glow"></div>
                </div>
                <div class="summary-card calories">
                    <div class="card-icon">🔥</div>
                    <div class="card-info">
                        <h3>Calories Burned</h3>
                        <p id="statCalories">0 kcal</p>
                    </div>
                    <div class="card-glow"></div>
                </div>
                <div class="summary-card duration">
                    <div class="card-icon">⏱️</div>
                    <div class="card-info">
                        <h3>Active Duration</h3>
                        <p id="statDuration">0 min</p>
                    </div>
                    <div class="card-glow"></div>
                </div>
            </div>

            <!-- Dashboard Columns -->
            <div class="dashboard-layout">
                <!-- Forms and Goals -->
                <div class="form-column">
                    <!-- Goals Panel -->
                    <div class="glass-panel">
                        <div class="panel-header">
                            <h2>🎯 Today's Goals</h2>
                        </div>
                        <div id="goalsContainer">
                            <!-- Goal Items Rendered Here -->
                        </div>
                    </div>

                    <!-- Log Workout Form -->
                    <div class="glass-panel">
                        <div class="panel-header">
                            <h2>💪 Log New Workout</h2>
                        </div>
                        <form id="workoutForm" onsubmit="submitWorkout(event)">
                            <div class="form-group">
                                <label for="activityType">Activity Type</label>
                                <select id="activityType" required>
                                    <option value="Running">🏃 Running</option>
                                    <option value="Cycling">🚴 Cycling</option>
                                    <option value="Swimming">🏊 Swimming</option>
                                    <option value="Yoga">🧘 Yoga</option>
                                </select>
                            </div>
                            <div class="form-group">
                                <label for="duration">Duration (Minutes)</label>
                                <input type="number" id="duration" min="1" placeholder="e.g. 30" required>
                            </div>
                            <div class="form-group">
                                <label for="calories">Calories Burned (kcal)</label>
                                <input type="number" id="calories" min="1" placeholder="e.g. 300" required>
                            </div>
                            <button type="submit" class="btn">Log Activity</button>
                        </form>
                    </div>

                    <!-- Add Goal Form -->
                    <div class="glass-panel">
                        <div class="panel-header">
                            <h2>🏁 Set Today's Goal</h2>
                        </div>
                        <form id="goalForm" onsubmit="submitGoal(event)">
                            <div class="form-group">
                                <label for="goalType">Goal Metric</label>
                                <select id="goalType" required>
                                    <option value="calories">🔥 Calorie Target (kcal)</option>
                                    <option value="duration">⏱️ Duration Target (minutes)</option>
                                </select>
                            </div>
                            <div class="form-group">
                                <label for="targetValue">Target Value</label>
                                <input type="number" id="targetValue" min="1" placeholder="e.g. 500" required>
                            </div>
                            <button type="submit" class="btn btn-accent">Set Daily Goal</button>
                        </form>
                    </div>
                </div>

                <!-- Workout History -->
                <div class="glass-panel">
                    <div class="panel-header">
                        <h2>📊 Today's Workout History</h2>
                    </div>
                    <div class="table-container">
                        <table>
                            <thead>
                                <tr>
                                    <th>Activity</th>
                                    <th>Duration</th>
                                    <th>Calories</th>
                                    <th>Date</th>
                                </tr>
                            </thead>
                            <tbody id="workoutsTableBody">
                                <!-- Workout rows rendered here -->
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </main>

        <div class="toast-container" id="toastContainer"></div>

        <script>
            // Show toast notifications
            function showToast(message, type = 'info') {
                const container = document.getElementById('toastContainer');
                const toast = document.createElement('div');
                toast.className = `toast ${type}`;
                toast.innerHTML = `
                    <span>${message}</span>
                    <span style="cursor:pointer; margin-left: 15px; font-weight: bold;" onclick="this.parentElement.remove()">×</span>
                `;
                container.appendChild(toast);
                
                // Trigger transition
                setTimeout(() => toast.classList.add('show'), 50);
                
                // Auto remove
                setTimeout(() => {
                    toast.classList.remove('show');
                    setTimeout(() => toast.remove(), 300);
                }, 4000);
            }

            // Load and render stats, goals, and history
            async function loadDashboard() {
                const userId = document.getElementById('userSelect').value;
                const todayStr = new Date().toISOString().split('T')[0];
                
                try {
                    // Fetch progress stats
                    const progressRes = await fetch(`/progress/${userId}?date=${todayStr}`);
                    if (!progressRes.ok) throw new Error("Could not load progress data");
                    const progress = await progressRes.json();
                    
                    // Update Stats Cards
                    document.getElementById('statWorkouts').textContent = progress.total_workouts;
                    document.getElementById('statCalories').textContent = `${progress.total_calories_burned} kcal`;
                    document.getElementById('statDuration').textContent = `${progress.total_duration_minutes} min`;
                    
                    // Render goals
                    const goalsContainer = document.getElementById('goalsContainer');
                    goalsContainer.innerHTML = '';
                    
                    if (progress.goals.length === 0) {
                        goalsContainer.innerHTML = '<div class="no-data">No goals set for today yet.</div>';
                    } else {
                        progress.goals.forEach(goal => {
                            const isAchieved = goal.achieved;
                            const goalClass = isAchieved ? 'achieved' : 'in-progress';
                            const badgeText = isAchieved ? 'COMPLETED' : 'IN PROGRESS';
                            const metric = goal.goal_type === 'calories' ? 'kcal' : 'min';
                            
                            const html = `
                                <div class="goal-item ${goalClass}">
                                    <div class="goal-meta">
                                        <span class="goal-title">${goal.goal_type} Goal</span>
                                        <span class="goal-target">${goal.current_value} / ${goal.target_value} ${metric}</span>
                                    </div>
                                    <div class="progress-container">
                                        <div class="progress-bar" style="width: ${goal.progress_percentage}%"></div>
                                    </div>
                                    <div class="goal-status">
                                        <span class="status-badge">${badgeText}</span>
                                        <span style="color: var(--text-muted); font-size: 11px;">${goal.progress_percentage}% achieved</span>
                                    </div>
                                </div>
                            `;
                            goalsContainer.innerHTML += html;
                        });
                    }

                    // Fetch workouts history
                    const workoutsRes = await fetch(`/workouts`);
                    if (!workoutsRes.ok) throw new Error("Could not load workouts");
                    const workouts = await workoutsRes.json();
                    
                    // Filter workouts for selected user and today
                    const userWorkouts = workouts.filter(w => w.user_id == userId && w.date_logged === todayStr);
                    
                    const tableBody = document.getElementById('workoutsTableBody');
                    tableBody.innerHTML = '';
                    
                    if (userWorkouts.length === 0) {
                        tableBody.innerHTML = '<tr><td colspan="4" class="no-data">No workouts logged today. Start moving!</td></tr>';
                    } else {
                        userWorkouts.reverse().forEach(w => {
                            const badgeClass = w.activity_type.toLowerCase();
                            const row = `
                                <tr>
                                    <td><span class="badge-activity ${badgeClass}">${w.activity_type}</span></td>
                                    <td>${w.duration_minutes} min</td>
                                    <td>${w.calories_burned} kcal</td>
                                    <td>${w.date_logged}</td>
                                </tr>
                            `;
                            tableBody.innerHTML += row;
                        });
                    }
                    
                } catch (err) {
                    showToast(err.message, 'error');
                }
            }

            // Form Submissions
            async function submitWorkout(e) {
                e.preventDefault();
                const userId = document.getElementById('userSelect').value;
                const activityType = document.getElementById('activityType').value;
                const duration = parseInt(document.getElementById('duration').value);
                const calories = parseInt(document.getElementById('calories').value);
                
                try {
                    const response = await fetch('/workouts', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            user_id: parseInt(userId),
                            activity_type: activityType,
                            duration_minutes: duration,
                            calories_burned: calories
                        })
                    });
                    
                    if (!response.ok) {
                        const errData = await response.json();
                        throw new Error(errData.detail || "Error logging workout");
                    }
                    
                    showToast("Workout activity logged successfully!", "success");
                    document.getElementById('workoutForm').reset();
                    loadDashboard();
                } catch (err) {
                    showToast(err.message, "error");
                }
            }

            async function submitGoal(e) {
                e.preventDefault();
                const userId = document.getElementById('userSelect').value;
                const goalType = document.getElementById('goalType').value;
                const targetValue = parseInt(document.getElementById('targetValue').value);
                
                try {
                    const response = await fetch('/goals', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            user_id: parseInt(userId),
                            goal_type: goalType,
                            target_value: targetValue
                        })
                    });
                    
                    if (!response.ok) {
                        const errData = await response.json();
                        throw new Error(errData.detail || "Error setting goal");
                    }
                    
                    showToast("Daily fitness goal configured!", "success");
                    document.getElementById('goalForm').reset();
                    loadDashboard();
                } catch (err) {
                    showToast(err.message, "error");
                }
            }

            // Initial load
            window.addEventListener('DOMContentLoaded', loadDashboard);
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)
#TO START THE APP
#uvicorn main:app --reload

#HOW TO ACTIVATE VENV
#venv\Scripts\activate