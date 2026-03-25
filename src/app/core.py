def add_tax(price: float, tax_rate: float = 0.18) -> float:
    """
    Adds tax to given price. Default 18%.
    """
    return round(price * (1 + tax_rate), 2)
