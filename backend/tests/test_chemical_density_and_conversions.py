import pytest
from decimal import Decimal
from apps.core.models import Product, UnitOfMeasure, ProductUOMConversion

@pytest.mark.django_db
def test_chemical_density_weight_volume_conversions(setup_master_data):
    """
    TEST CHEMICAL DENSITY & UOM CONVERSIONS:
    Verify that:
    1. Agrochemical weight-volume conversion never assumes 1L == 1kg.
    2. Uses chemical density at 20°C:
       - Chlorpyrifos Tech (density 1.35 kg/L): 1000 Liters = 1350 kg.
       - Xylene Solvent (density 0.86 kg/L): 1000 Liters = 860 kg.
    3. Packaging conversions: 1 Carton = 12 Bottles.
    """
    data = setup_master_data
    uom_kg = data['uom_kg']
    uom_l = data['uom_l']
    uom_btl = data['uom_bottle']
    uom_ctn = data['uom_carton']

    chlor_tech = data['chlorpyrifos_tech'] # Density: 1.3500 kg/L
    xylene = data['solvent_xylene']         # Density: 0.8600 kg/L

    # 1. Convert 1000 Liters of Chlorpyrifos Tech to KG
    # 1000 L * 1.35 kg/L = 1350 kg
    chlor_kg = chlor_tech.convert_quantity(Decimal('1000.0000'), from_uom=uom_l, to_uom=uom_kg)
    assert chlor_kg == Decimal('1350.0000')

    # Reverse: 1350 kg of Chlorpyrifos to Liters = 1000 L
    chlor_liters = chlor_tech.convert_quantity(Decimal('1350.0000'), from_uom=uom_kg, to_uom=uom_l)
    assert chlor_liters == Decimal('1000.0000')

    # 2. Convert 1000 Liters of Xylene Solvent to KG
    # 1000 L * 0.86 kg/L = 860 kg
    xylene_kg = xylene.convert_quantity(Decimal('1000.0000'), from_uom=uom_l, to_uom=uom_kg)
    assert xylene_kg == Decimal('860.0000')

    # 3. Explicit Packaging Conversion: 1 Carton = 12 Bottles
    pyrifos_product = data['pyrifos_48ec']
    ProductUOMConversion.objects.create(
        product=pyrifos_product,
        from_uom=uom_ctn,
        to_uom=uom_btl,
        conversion_factor=Decimal('12.000000')
    )

    # 5 Cartons = 60 Bottles
    bottles = pyrifos_product.convert_quantity(Decimal('5.0000'), from_uom=uom_ctn, to_uom=uom_btl)
    assert bottles == Decimal('60.000000')

    # 60 Bottles = 5 Cartons
    cartons = pyrifos_product.convert_quantity(Decimal('60.0000'), from_uom=uom_btl, to_uom=uom_ctn)
    assert cartons == Decimal('5.000000')
