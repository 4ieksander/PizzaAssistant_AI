"""
FastAPI app with endpoints for managing pizzas, ingredients, orders, and clients.
"""
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from .schemas import OrderSchema, InitOrderRequest
from .models import Pizza, Ingredient, Order, Client

from .database import SessionLocal, get_db
import logging

console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
logging.basicConfig(level=logging.INFO, handlers=[console_handler])

log = logging.getLogger(__name__)
# FastAPI instance
app = FastAPI()
app.add_middleware(
    middleware_class=CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Domena React (lub "*" dla wszystkich)
    allow_credentials=True,
    allow_methods=["*"],  # Pozwól na wszystkie metody (GET, POST, OPTIONS, itd.)
    allow_headers=["*"],  # Pozwól na wszystkie nagłówki
)



@app.post("/init-order", response_model=OrderSchema)
def call_and_initiate_order(request: InitOrderRequest, db: Session = Depends(get_db)):
    """
    Call the order and initiate it for the given client.
    """
    phone = request.phone
    log.info("Initiating order")
    client = db.query(Client).filter(Client.phone == phone).first()
    if not client:
        log.info(f"Creating new client with phone: {phone}")
        client = Client(phone=phone)
        db.add(client)
        db.commit()
        db.refresh(client)
    log.info(f"Creating new order for client: {client}")
    order = Order(client_id=client.id)
    db.add(order)
    db.commit()
    db.refresh(order)
    return OrderSchema.model_validate(order)

@app.post("/analyze_transcription")
def analyze_transcription(transcription: str):
    """
    Analyze the given transcription and return the result.
    """
    log.info(f"Analyzing transcription: {transcription}")
    return {"transcription": transcription}

@app.put("/analyze_transcription")
def analyze_transcription(transcription: str):
    """
    Analyze the given transcription and return the result.
    """
    log.info(f"Analyzing transcription: {transcription}")
    return {"transcription": transcription}

@app.get("/current_order_data")
def get_current_order_data():
    """
    Get the data of the current order.
    """
    return {"current_order": "data"}



@app.get("/summarise_order")
def summarise_order():
    """
    Summarise the current order.
    """
    return {"order": "summary"}

@app.get("/confirm_order")
def confirm_order():
    """
    Confirm the current order.
    """
    return {"order": "confirmed"}

# # Include routers
# app.include_router(pizzas.router, prefix="/pizzas", tags=["pizzas"])
# app.include_router(ingredients.router, prefix="/ingredients", tags=["ingredients"])
# #x
# # # app.include_router(pizzas.router, prefix="/pizz")
# #
