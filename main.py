import psycopg2
from fastapi import FastAPI, Request, HTTPException
from pathlib import Path
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel


BASE = Path(__file__).parent

app = FastAPI(title="Origin Wear Shop")
templates = Jinja2Templates(directory=BASE / "templates")

def get_conn():
    return psycopg2.connect(
        dbname="origin_wear",
        user="postgres",
        password="123",
        host="localhost",
        port="5432"
    )

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
def create_product(product: ProductCreate):
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
def delete_products(product_id: int):
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
def update_product(product_id: int, product: ProductCreate):
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