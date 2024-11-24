from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from models import Ingredient

from app.database import get_db
from app.serializers import IngredientResponse, IngredientCreate

router = APIRouter()

@router.post("/ingredients", response_model=IngredientResponse, status_code=201)
def create_ingredient(ingredient: IngredientCreate, db: Session = Depends(get_db)):
    try:
        # Sprawdzanie, czy składnik już istnieje
        existing_ingredient = db.query(Ingredient).filter(Ingredient.name == ingredient.name).first()
        if existing_ingredient:
            raise HTTPException(status_code=400, detail="Ingredient with this name already exists")

        # Tworzenie nowego składnika
        new_ingredient = Ingredient(
            name=ingredient.name,
            price=ingredient.price,
            category=ingredient.category,
            in_stock=ingredient.in_stock
        )
        db.add(new_ingredient)
        db.commit()
        db.refresh(new_ingredient)

        return new_ingredient
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))