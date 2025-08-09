import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from ApplianceManagerFrame import (
    Appliance,
    ShoppingCart,
    ApplianceFilter,
    sort_appliances,
)


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
        Appliance('OVEN001', 'Siemens', 'oven', 'Siemens oven OVEN001', 600, 590, 560, 0, 0.0, option='pyrolyse'),
        Appliance('OVEN002', 'Bosch', 'oven', 'Bosch oven OVEN002', 600, 590, 560, 0, 0.0, option='hydrolyse'),
        Appliance('KOOK001', 'Bosch', 'kookplaat', 'Bosch kookplaat KOOK001', 600, 590, 560, 0, 0.0),
        Appliance('VAAS001', 'Miele', 'vaatwasser', 'Miele vaatwasser VAAS001', 600, 590, 560, 0, 0.0)
    ]

    filter_obj = ApplianceFilter(appliances)

    ovens = filter_obj.filter(category='oven')
    assert len(ovens) == 2
    assert {o.code for o in ovens} == {'OVEN001', 'OVEN002'}

    siemens = filter_obj.filter(brand='Siemens')
    assert len(siemens) == 1
    assert siemens[0].brand == 'Siemens'

    pyro = filter_obj.filter(category='oven', option='pyrolyse')
    assert len(pyro) == 1
    assert pyro[0].option == 'pyrolyse'


def test_price_logic():
    # catalog price conversions
    a = Appliance('OVEN', 'Brand', 'bakovens', 'desc', 600, 590, 560, 1225, 0)
    assert a.catalog_price == 839
    assert Appliance.points_from_catalog_price(839) == 1225

    # internal price for 21% VAT
    oven = Appliance('OVEN2', 'Brand', 'bakovens', 'desc', 600, 590, 560, 361, 0)
    assert oven.internal_price == 142

    # internal price for 6% VAT (afzuigkappen)
    hood = Appliance('HOOD', 'Brand', 'afzuigkappen', 'desc', 600, 590, 560, 361, 0)
    assert hood.internal_price == 124


def test_sort_appliances_function():
    a1 = Appliance('A1', 'B', 'bakovens', 'Alpha', 600, 590, 560, 100, 0, option='b')
    a2 = Appliance('A2', 'A', 'koelkast', 'Beta', 600, 590, 560, 200, 0, option='a')
    a3 = Appliance('A3', 'C', 'bakovens', 'Gamma', 500, 590, 560, 150, 0)
    # Sort by name ascending
    names = [a.description for a in sort_appliances([a2, a1], 'Naam')]
    assert names == ['Alpha', 'Beta']
    # Sort by points descending
    pts = [a.points for a in sort_appliances([a1, a2], 'Punten', descending=True)]
    assert pts == [200, 100]
    # Sort by price euro ascending
    prices = [a.internal_price for a in sort_appliances([a2, a1], 'Prijs €')]
    assert prices == sorted(prices)
    # Sort by width ascending
    widths = [a.width_mm for a in sort_appliances([a1, a3], 'Breedte mm')]
    assert widths == [500, 600]
    # Sort by brand ascending
    brands = [a.brand for a in sort_appliances([a1, a2, a3], 'Merk')]
    assert brands == ['A', 'B', 'C']
    # Sort by code ascending
    codes = [a.code for a in sort_appliances([a2, a1], 'Code')]
    assert codes == ['A1', 'A2']
    # Sort by category ascending
    cats = [a.category for a in sort_appliances([a2, a1], 'Categorie')]
    assert cats == ['bakovens', 'koelkast']
    # Sort by sub-option ascending
    opts = [a.option for a in sort_appliances([a1, a2], 'Suboptie')]
    assert opts == ['a', 'b']
