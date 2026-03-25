from app.core import add_tax

def test_add_tax_default():
    assert add_tax(100) == 118.00

def test_add_tax_custom():
    assert add_tax(200, 0.10) == 220.00
