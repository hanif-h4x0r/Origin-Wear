import psycopg2
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from pathlib import Path
from fastapi.templating import Jinja2Templates

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