from pydantic import BaseModel, Field

class Item(BaseModel):
    id: int = Field(..., ge=1)
    name: str = Field(..., min_length=2)
    price: float = Field(..., gt=0)
    price_with_tax: float | None = None
