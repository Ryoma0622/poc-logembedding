import logging
from pythonjsonlogger import jsonlogger
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from . import models, schemas
from .database import SessionLocal, engine, Base

# Configure logging
logger = logging.getLogger("app")
logger.setLevel(logging.INFO)

# Ensure the log directory exists
import os
log_dir = "/var/log/app"
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

logHandler = logging.FileHandler(os.path.join(log_dir, "app.log"))
formatter = jsonlogger.JsonFormatter("%(asctime)s %(name)s %(levelname)s %(message)s")
logHandler.setFormatter(formatter)
logger.addHandler(logHandler)

app = FastAPI()

# Create database tables
Base.metadata.create_all(bind=engine)

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/health")
def health_check():
    logger.info("Health check endpoint was called.")
    return {"status": "ok"}

@app.post("/users/", response_model=schemas.User)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user:
        logger.warning(f"Attempted to create duplicate user with email: {user.email}")
        raise HTTPException(status_code=400, detail="Email already registered")

    db_user = models.User(username=user.username, email=user.email)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    logger.info(f"User created: {db_user.username} ({db_user.email})")
    return db_user

@app.get("/users/", response_model=list[schemas.User])
def read_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    users = db.query(models.User).offset(skip).limit(limit).all()
    logger.info(f"Retrieved {len(users)} users.")
    return users

@app.get("/users/{user_id}", response_model=schemas.User)
def read_user(user_id: int, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if db_user is None:
        logger.warning(f"User with ID {user_id} not found.")
        raise HTTPException(status_code=404, detail="User not found")
    logger.info(f"Retrieved user: {db_user.username} (ID: {user_id})")
    return db_user

@app.put("/users/{user_id}", response_model=schemas.User)
def update_user(user_id: int, user: schemas.UserUpdate, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if db_user is None:
        logger.warning(f"Attempted to update non-existent user with ID: {user_id}")
        raise HTTPException(status_code=404, detail="User not found")

    update_data = user.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_user, key, value)

    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    logger.info(f"User updated: {db_user.username} (ID: {user_id})")
    return db_user

@app.delete("/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if db_user is None:
        logger.warning(f"Attempted to delete non-existent user with ID: {user_id}")
        raise HTTPException(status_code=404, detail="User not found")

    db.delete(db_user)
    db.commit()
    logger.info(f"User deleted: {db_user.username} (ID: {user_id})")
    return {"message": "User deleted successfully"}

@app.post("/test/generate-known-error")
def generate_known_error():
    try:
        1 / 0
    except ZeroDivisionError as e:
        logger.error(f"Known error occurred: Division by zero attempt. Details: {e}", extra={"service": "web-app", "error_type": "known_division_by_zero"})
        return {"message": "Known error log generated."}

@app.post("/test/generate-unknown-error")
def generate_unknown_error():
    import random
    error_messages = [
        "Unexpected file system error during write operation.",
        "Corrupted data block detected in cache.",
        "Third-party API rate limit exceeded unexpectedly.",
        "Memory allocation failure in critical background task.",
        "Invalid cryptographic key used for decryption."
    ]
    random_message = random.choice(error_messages)
    logger.error(f"Unknown error occurred: {random_message}", extra={"service": "web-app", "error_type": "unknown_runtime_error"})
    return {"message": "Unknown error log generated."}

@app.post("/test/generate-normal-logs")
def generate_normal_logs():
    logger.info("User login successful.", extra={"service": "web-app", "event_type": "user_login"})
    logger.debug("Database query executed in 15ms.", extra={"service": "web-app", "query_time_ms": 15})
    logger.warning("Low disk space warning on /tmp, 10% remaining.", extra={"service": "web-app", "disk_usage_percent": 10})
    return {"message": "Normal logs generated."}

@app.post("/test/generate-specific-error")
def generate_specific_error():
    logger.error("Unknown error occurred: Invalid cryptographic key used for decryption.", extra={"service": "web-app", "error_type": "specific_crypto_error"})
    return {"message": "Specific error log generated."}
