from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import analyze_order, orders, conversation


app = FastAPI()
app.add_middleware(
    middleware_class=CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analyze_order.router, prefix='/analyzer', tags=["analyze_order"])
app.include_router(orders.router, prefix='/orders' , tags=["orders"])
app.include_router(conversation.router, prefix='/conversation', tags=["conversations"])
