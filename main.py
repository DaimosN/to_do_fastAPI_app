from typing import List, Optional
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import SessionLocal, engine, Base
from models import TodoItem as TodoItemModel, User as UserModel
from passlib.context import CryptContext
from jose import jwt
from datetime import datetime, timedelta
import secrets
import string

Base.metadata.create_all(bind=engine)

app = FastAPI()

# Для хеширования паролей
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
alphabet = string.ascii_letters + string.digits

SECRET_KEY = ''.join(secrets.choice(alphabet) for i in range(10))
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


class TodoCreate(BaseModel):
    title: str
    description: Optional[str] = None
    completed: bool = False


class TodoItem(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    completed: bool = False

    class Config:
        orm_mode = True


class UserCreate(BaseModel):
    username: str
    password: str


class User(BaseModel):
    id: int
    username: str

    class Config:
        orm_mode = True


class Token(BaseModel):
    access_token: str
    token_type: str


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Хеширование пароля
def hash_password(password: str):
    return pwd_context.hash(password)


# Проверка пароля
def verify_password(plain_password: str, hashed_password: str):
    return pwd_context.verify(plain_password, hashed_password)


# Генерация токена доступа
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt



# Регистрация пользователя
@app.post("/register", response_model=User)
def register(user: UserCreate, db: Session = Depends(get_db)):
    hashed_password = hash_password(user.password)
    db_user = UserModel(username=user.username, hashed_password=hashed_password)

    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    return db_user


# Вход пользователя и получение токена доступа
@app.post("/token", response_model=Token)
def login(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(UserModel).filter(UserModel.username == user.username).first()

    if not db_user or not verify_password(user.password, db_user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect username or password")

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": db_user.username}, expires_delta=access_token_expires)

    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/items", response_model=List[TodoItem])
def get_items(db: Session = Depends(get_db)):
    """Получить все задачи"""
    items = db.query(TodoItemModel).all()
    return items


@app.get("/items/{item_id}", response_model=TodoItem)
def get_item(item_id: int, db: Session = Depends(get_db)):
    """Получить задачу по id"""
    item = db.query(TodoItemModel).filter(TodoItemModel.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


@app.post("/items", response_model=TodoItem)
def create_item(item: TodoCreate, db: Session = Depends(get_db)):
    """Создать задачу"""
    new_item = TodoItemModel(
        title=item.title,
        description=item.description,
        completed=item.completed
    )
    db.add(new_item)
    db.commit()
    db.refresh(new_item)
    return new_item


@app.put("/items/{item_id}", response_model=TodoItem)
def update_item(item_id: int, item: TodoCreate, db: Session = Depends(get_db)):
    db_item = db.query(TodoItemModel).filter(TodoItemModel.id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Item not found")
    db_item.title = item.title
    db_item.description = item.description
    db_item.completed = item.completed
    db.commit()
    db.refresh(db_item)
    return db_item


@app.delete("/items/{item_id}")
def delete_item(item_id: int, db: Session = Depends(get_db)):
    db_item = db.query(TodoItemModel).filter(TodoItemModel.id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Item not found")
    db.delete(db_item)
    db.commit()
    return {"message": "Item deleted"}

