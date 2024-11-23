from fastapi import APIRouter, HTTPException
from app.database import SessionLocal
from sqlalchemy.orm import Session
from app.models import Order

router = APIRouter()

@router.get("/")
def get_orders():
    db: Session = SessionLocal()
    order_items = db.query(Order).all()
    return order_items
 