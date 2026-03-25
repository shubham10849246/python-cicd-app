from fastapi import APIRouter, HTTPException
from .models import Item
from .core import add_tax

router = APIRouter()
_FAKE_DB = {}

@router.post("/items", response_model=Item)
def create_item(item: Item):
    if item.id in _FAKE_DB:
        raise HTTPException(status_code=409, detail="Item already exists")

    item.price_with_tax = add_tax(item.price)
    _FAKE_DB[item.id] = item
    return item

@router.get("/items/{item_id}", response_model=Item)
def get_item(item_id: int):
    if item_id not in _FAKE_DB:
        raise HTTPException(status_code=404, detail="Item not found")

    return _FAKE_DB[item_id]

