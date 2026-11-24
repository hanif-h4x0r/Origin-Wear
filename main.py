import os
import jwt
import psycopg2
import bcrypt
from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException
from pathlib import Path
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")

BASE = Path(__file__).parent

security = HTTPBearer()

app = FastAPI(title="Origin Wear Shop")
templates = Jinja2Templates(directory=BASE / "templates")

def get_conn():
    return psycopg2.connect(
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
    )


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user_id = int(payload["sub"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired, login again")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    return user_id


@app.get("/")
def home(request: Request):
    return templates.TemplateResponse(request, "index.html")

@app.get("/products")
def products_page(request: Request):
    return templates.TemplateResponse(request, "products.html")

@app.get("/api/products")
def products():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT name, price FROM products;")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    result = []
    for name, price in rows:
        result.append({"name": name, "price": price})
    return result
class ProductCreate(BaseModel):
    name: str
    price: int

@app.post("/api/products", status_code=201)
def create_product(product: ProductCreate, user_id: int = Depends(get_current_user)):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("INSERT INTO products (name, price) VALUES (%s, %s) RETURNING id;", (product.name, product.price))
    new_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    return {"id": new_id, "name": product.name, "price": product.price}

@app.get("/api/products/{product_id}")
def get_product(product_id: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, name, price FROM products WHERE id = %s", (product_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    if row is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"id": row[0], "name": row[1], "price": row[2]}

@app.delete("/api/products/{product_id}")
def delete_products(product_id: int, user_id: int = Depends(get_current_user)):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM products WHERE id = %s RETURNING id;", (product_id,))
    row = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    if row is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"message": "Product deleted", "id": product_id}

@app.put("/api/products/{product_id}")
def update_product(product_id: int, product: ProductCreate, user_id: int = Depends(get_current_user)):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE products SET name = %s, price = %s WHERE id = %s RETURNING id;", (product.name, product.price, product_id))
    row = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    if row is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"id": product_id, "name": product.name, "price": product.price}

class UserCreate(BaseModel):
    email: str
    password: str

@app.post("/api/register", status_code=201)
def register(user: UserCreate):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE email = %s;", (user.email,))
    if cur.fetchone() is not None:
        cur.close()
        conn.close()
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed = bcrypt.hashpw(user.password.encode(), bcrypt.gensalt())
    cur.execute(
        "INSERT INTO users (email, password_hash) VALUES (%s, %s) RETURNING id;",
        (user.email, hashed.decode()),
    )
    new_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    return {"id": new_id, "email": user.email}

class UserLogin(BaseModel):
    email: str
    password: str

@app.post("/api/login")
def login(user: UserLogin):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, password_hash FROM users WHERE email = %s;", (user.email,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    if row is None:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    user_id, password_hash = row
    if not bcrypt.checkpw(user.password.encode(), password_hash.encode()):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = jwt.encode(
        {"sub": str(user_id), "exp": datetime.now(timezone.utc) + timedelta(hours=24)},
        SECRET_KEY,
        algorithm="HS256",
    )
    return {"access_token": token, "token_type": "bearer"}



