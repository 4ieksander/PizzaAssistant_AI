from fastapi import APIRouter, Depends
from app.database import get_db
from sqlalchemy.orm import Session
from app.models import Client, Order
from app.schemas import InitOrderRequest, OrderSchema
from app.utils.logger import get_logger

log = get_logger(__name__)

router = APIRouter()

@router.get("/")
def get_orders(db: Session = Depends(get_db)):
    order_items = db.query(Order).all()
    return order_items


@router.post("/init", response_model=OrderSchema)
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


