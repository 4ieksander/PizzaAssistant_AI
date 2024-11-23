from fastapi import FastAPI

from app.modules.analyze_order import AnalyzeOrder;
from app.routers import pizzas, orders

app = FastAPI()


@app.get("/")
async def root():
    return {"message": "Hello World"}

app.include_router(pizzas.router, prefix="/pizzas", tags=["pizzas"])
app.include_router(orders.router, prefix="/orders", tags=["orders"])

