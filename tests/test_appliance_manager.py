import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from ApplianceManagerFrame import Appliance, ShoppingCart, ApplianceFilter


def test_appliance_from_dict():
    data = {
        'code': 'TEST001',
        'brand': 'TestBrand',
        'category': 'oven',
        'description': 'TestBrand oven TEST001',
        'width_mm': 600,
        'height_mm': 590,
        'depth_mm': 560,
        'punten': 0,
        'price': 0.0,
        'option': 'met pyrolyse',
        'img': 'test.jpg'
    }

    appliance = Appliance.from_dict(data)
    assert appliance.code == 'TEST001'
    assert appliance.description == 'TestBrand oven TEST001'
    assert appliance.width_mm == 600


def test_shopping_cart():
    cart = ShoppingCart()
    appliance = Appliance('TEST001', 'TestBrand', 'oven',
                          'TestBrand oven TEST001', 600, 590, 560, 0, 0.0)

    cart.add_item(appliance)
    assert len(cart.items) == 1
    assert cart.get_total_points() == 0

    cart.add_item(appliance)
    assert len(cart.items) == 1
    assert cart.items[0].quantity == 2
    assert cart.get_total_points() == 0

    cart.remove_item(appliance)
    assert len(cart.items) == 0
    assert cart.get_total_points() == 0


def test_appliance_filter():
    appliances = [
        Appliance('OVEN001', 'Siemens', 'oven', 'Siemens oven OVEN001', 600, 590, 560, 0, 0.0),
        Appliance('KOOK001', 'Bosch', 'kookplaat', 'Bosch kookplaat KOOK001', 600, 590, 560, 0, 0.0),
        Appliance('VAAS001', 'Miele', 'vaatwasser', 'Miele vaatwasser VAAS001', 600, 590, 560, 0, 0.0)
    ]

    filter_obj = ApplianceFilter(appliances)

    ovens = filter_obj.filter(category='oven')
    assert len(ovens) == 1
    assert ovens[0].code == 'OVEN001'

    siemens = filter_obj.filter(brand='Siemens')
    assert len(siemens) == 1
    assert siemens[0].brand == 'Siemens'
