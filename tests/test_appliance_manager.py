import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from ApplianceManagerFrame import (
    Appliance,
    ShoppingCart,
    ApplianceFilter,
    AVAILABLE_CATEGORIES,
)


def test_appliance_from_dict():
    data = {
        'code': 'TEST001',
        'brand': 'TestBrand',
        'category': 'oven',
        'punten': 50,
        'price_ex': 499.99,
        'option': 'met pyrolyse',
        'img': 'test.jpg'
    }

    appliance = Appliance.from_dict(data)
    assert appliance.code == 'TEST001'
    assert appliance.points == 50
    assert appliance.price_ex == 499.99


def test_shopping_cart():
    cart = ShoppingCart()
    appliance = Appliance('TEST001', 'TestBrand', 'oven', 50, 499.99)

    cart.add_item(appliance)
    assert len(cart.items) == 1
    assert cart.get_total_points() == 50

    cart.add_item(appliance)
    assert len(cart.items) == 1
    assert cart.items[0].quantity == 2
    assert cart.get_total_points() == 100

    cart.remove_item(appliance)
    assert len(cart.items) == 0
    assert cart.get_total_points() == 0


def test_appliance_filter():
    appliances = [
        Appliance('OVEN001', 'Siemens', 'oven', 60, 599.99),
        Appliance('KOOK001', 'Bosch', 'kookplaat', 40, 399.99),
        Appliance('VAAS001', 'Miele', 'vaatwasser', 80, 799.99)
    ]

    filter_obj = ApplianceFilter(appliances)

    ovens = filter_obj.filter(category='oven')
    assert len(ovens) == 1
    assert ovens[0].code == 'OVEN001'

    low_points = filter_obj.filter(max_points=50)
    assert len(low_points) == 1

    siemens = filter_obj.filter(brand='Siemens')
    assert len(siemens) == 1
    assert siemens[0].brand == 'Siemens'


def test_brand_first_helpers():
    appliances = [
        Appliance('OVEN001', 'Siemens', 'oven', 60, 599.99),
        Appliance('KOOK001', 'Siemens', 'kookplaat', 40, 399.99),
        Appliance('VAAS001', 'Miele', 'vaatwasser', 80, 799.99)
    ]

    filter_obj = ApplianceFilter(appliances)

    brands = filter_obj.get_brands()
    assert set(brands) == {'Siemens', 'Miele'}

    categories = filter_obj.get_categories_for_brand('Siemens')
    assert set(categories) == set(AVAILABLE_CATEGORIES)
