from fastapi import APIRouter, HTTPException, Depends
from app.database import SessionLocal, get_db
from sqlalchemy.orm import Session
from app.models import Order

router = APIRouter()

@router.get("/")
def get_orders(db: Session = Depends(get_db)):
    order_items = db.query(Order).all()
    return order_items
 
# @router.get("/{order_id}")
# def get_order(order_id: int, db: Session = Depends(get_db)):
#     order_item = db.query(Order).filter(Order.id == order_id).first()
#     if order_item is None:
#         raise HTTPException(status_code=404, detail="Order not found")
#     return order_item
#
# @router.post("/")
# def create_order(order: Order):
#     db: Session = SessionLocal()
#     db.add(order)
#     db.commit()
#     db.refresh(order)
#     return order
#
# @router.put("/{order_id}")
# def update_order(order_id: int, order: Order):
#     db: Session = SessionLocal()
#     db.query(Order).filter(Order.id == order_id).update(order.dict())
#     db.commit()
#     return {"message": "Order updated successfully"}


