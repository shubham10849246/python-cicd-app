import pytest
from app.models import Item

def test_item_valid():
    item = Item(id=1, name="Pen", price=10.0)
    assert item.id == 1

def test_item_invalid_price():
    with pytest.raises(Exception):
        Item(id=1, name="Pen", price=-10.0)
