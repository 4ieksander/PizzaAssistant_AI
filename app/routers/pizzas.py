from fastapi import APIRouter, HTTPException
from app.database import SessionLocal
from sqlalchemy.orm import Session
from app.models import Pizza

router = APIRouter()

@router.get("/")
def get_menu():
    db: Session = SessionLocal()
    pizza_items = db.query(Pizza).all()
    return pizza_items

@router.post("/test")
def post_test(request):
    print(request.data)