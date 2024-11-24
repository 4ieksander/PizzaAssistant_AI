from fastapi import APIRouter, HTTPException
from app.database import SessionLocal
from sqlalchemy.orm import Session
from app.models import Pizza

router = APIRouter()

@router.get("/")
def get_all_pizzas():
    db: Session = SessionLocal()
    pizza_items = db.query(Pizza).all()
    return pizza_items

@router.post("/")
def create_pizza(pizza: Pizza):
    db: Session = SessionLocal()
    db.add(pizza)
    db.commit()
    db.refresh(pizza)
    return pizza

@router.get("/{pizza_id}")
def get_pizza(pizza_id: int):
    db: Session = SessionLocal()
    pizza_item = db.query(Pizza).filter(Pizza.id == pizza_id).first()
    if pizza_item is None:
        raise HTTPException(status_code=404, detail="Pizza not found")
    return pizza_item

@router.put("/{pizza_id}")
def update_pizza(pizza_id: int, pizza: Pizza):
    db: Session = SessionLocal()
    db.query(Pizza).filter(Pizza.id == pizza_id).update(pizza.dict())
    db.commit()
    return {"message": "Pizza updated successfully"}

@router.delete("/{pizza_id}")
def delete_pizza(pizza_id: int):
    db: Session = SessionLocal()
    db.query(Pizza).filter(Pizza.id == pizza_id).delete()
    db.commit()
    return {"message": "Pizza deleted successfully"}
