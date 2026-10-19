import pytest
from decimal import Decimal
from datetime import date, timedelta
from django.contrib.auth import get_user_model
from apps.core.models import (
    LegalEntity, Branch, Warehouse, StorageLocation,
    UnitOfMeasure, Product, ProductUOMConversion, Partner
)
from apps.accounting.models import Account, BankCashAccount, FiscalYear, FiscalPeriod

User = get_user_model()

@pytest.fixture
def admin_user(db):
    user, _ = User.objects.get_or_create(
        username='erp_admin',
        defaults={'email': 'admin@agrochemical-eg.com', 'is_staff': True, 'is_superuser': True}
    )
    user.set_password('AdminSecurePass2026!')
    user.save()
    return user


@pytest.fixture
def setup_master_data(db, admin_user):
    """Sets up standard Egyptian Agrochemical master data, accounts, and warehouses."""
    # 1. Legal Entity
    entity, _ = LegalEntity.objects.get_or_create(
        code='EGY-AGRO-01',
        defaults={
            'name_ar': 'شركة مصر للصناعات الكيماوية والزراعية ش.م.م',
            'name_en': 'Misr Agrochemical & Fertilizer Industries S.A.E',
            'tax_id': '100-200-300',
            'commercial_register': '98765-Giza',
            'currency': 'EGP',
            'address': 'المنطقة الصناعية الثانية - مدينة السادات - المنوفية',
        }
    )

    # 2. Branch & Factory
    factory, _ = Branch.objects.get_or_create(
        code='BR-FACTORY',
        defaults={
            'legal_entity': entity,
            'name_ar': 'مصنع السادات لتركيب وتعبئة المبيدات والأسمدة',
            'name_en': 'Sadat City Chemical Formulation Plant',
            'is_factory': True,
        }
    )

    # 3. Warehouses
    wh_raw, _ = Warehouse.objects.get_or_create(
        code='WH-RAW',
        defaults={'branch': factory, 'name_ar': 'مستودع المواد الخام والمذيبات', 'name_en': 'Raw Materials Warehouse', 'warehouse_type': 'RAW_MATERIALS'}
    )
    wh_fg, _ = Warehouse.objects.get_or_create(
        code='WH-FG',
        defaults={'branch': factory, 'name_ar': 'مستودع المنتج التام', 'name_en': 'Finished Goods Warehouse', 'warehouse_type': 'FINISHED_GOODS'}
    )
    wh_pkg, _ = Warehouse.objects.get_or_create(
        code='WH-PKG',
        defaults={'branch': factory, 'name_ar': 'مستودع مواد التعبئة والتغليف', 'name_en': 'Packaging Materials Warehouse', 'warehouse_type': 'PACKAGING'}
    )

    # 4. Units of Measure
    uom_kg, _ = UnitOfMeasure.objects.get_or_create(
        code='KG', defaults={'name_ar': 'كيلوجرام', 'name_en': 'Kilogram', 'category': 'WEIGHT', 'base_ratio': Decimal('1.000000')}
    )
    uom_g, _ = UnitOfMeasure.objects.get_or_create(
        code='G', defaults={'name_ar': 'جرام', 'name_en': 'Gram', 'category': 'WEIGHT', 'base_ratio': Decimal('0.001000')}
    )
    uom_l, _ = UnitOfMeasure.objects.get_or_create(
        code='L', defaults={'name_ar': 'لتر', 'name_en': 'Liter', 'category': 'VOLUME', 'base_ratio': Decimal('1.000000')}
    )
    uom_bottle, _ = UnitOfMeasure.objects.get_or_create(
        code='BTL', defaults={'name_ar': 'عبوة 1 لتر', 'name_en': '1L Bottle', 'category': 'UNIT', 'base_ratio': Decimal('1.000000')}
    )
    uom_carton, _ = UnitOfMeasure.objects.get_or_create(
        code='CTN', defaults={'name_ar': 'كرتونة 12 عبوة', 'name_en': 'Carton (12 Bottles)', 'category': 'UNIT', 'base_ratio': Decimal('1.000000')}
    )

    # 5. Accounts
    acc_bank, _ = Account.objects.get_or_create(code='1001', defaults={'name_ar': 'البنك الأهلي المصري - جاري', 'name_en': 'NBE Bank Account', 'account_type': 'ASSET'})
    acc_ar, _ = Account.objects.get_or_create(code='1101', defaults={'name_ar': 'العملاء وأوراق القبض', 'name_en': 'Accounts Receivable', 'account_type': 'ASSET', 'is_reconcilable': True})
    acc_wht_rec, _ = Account.objects.get_or_create(code='1105', defaults={'name_ar': 'ضريبة الخصم والإضافة المدينة', 'name_en': 'WHT Receivable', 'account_type': 'ASSET'})
    acc_raw_inv, _ = Account.objects.get_or_create(code='1201', defaults={'name_ar': 'مخزون الخامات', 'name_en': 'Raw Material Inventory', 'account_type': 'ASSET'})
    acc_wip, _ = Account.objects.get_or_create(code='1203', defaults={'name_ar': 'إنتاج تحت التشغيل', 'name_en': 'Work in Process (WIP)', 'account_type': 'ASSET'})
    acc_fg_inv, _ = Account.objects.get_or_create(code='1204', defaults={'name_ar': 'مخزون تام الصنع', 'name_en': 'Finished Goods Inventory', 'account_type': 'ASSET'})
    acc_input_vat, _ = Account.objects.get_or_create(code='1205', defaults={'name_ar': 'ضريبة القيمة المضافة - مدخلات', 'name_en': 'Input VAT', 'account_type': 'ASSET'})
    acc_interim_stock, _ = Account.objects.get_or_create(code='1209', defaults={'name_ar': 'وسيط استلام البضائع', 'name_en': 'Goods Received Clearing', 'account_type': 'ASSET'})
    acc_ap, _ = Account.objects.get_or_create(code='2101', defaults={'name_ar': 'الموردون وأوراق الدفع', 'name_en': 'Accounts Payable', 'account_type': 'LIABILITY', 'is_reconcilable': True})
    acc_wht_pay, _ = Account.objects.get_or_create(code='2106', defaults={'name_ar': 'ضريبة الخصم والتحصيل الدائنة', 'name_en': 'WHT Payable', 'account_type': 'LIABILITY'})
    acc_interim_ap, _ = Account.objects.get_or_create(code='2109', defaults={'name_ar': 'وسيط فواتير الموردين', 'name_en': 'Unbilled Supplier Accrual', 'account_type': 'LIABILITY'})
    acc_output_vat, _ = Account.objects.get_or_create(code='2201', defaults={'name_ar': 'ضريبة القيمة المضافة - مخرجات', 'name_en': 'Output VAT', 'account_type': 'LIABILITY'})
    acc_revenue, _ = Account.objects.get_or_create(code='4101', defaults={'name_ar': 'إيرادات المبيعات', 'name_en': 'Sales Revenue', 'account_type': 'REVENUE'})
    acc_cogs, _ = Account.objects.get_or_create(code='5101', defaults={'name_ar': 'تكلفة البضاعة المباعة', 'name_en': 'Cost of Goods Sold', 'account_type': 'EXPENSE'})
    acc_scrap, _ = Account.objects.get_or_create(code='5105', defaults={'name_ar': 'انحراف وتوالف تصنيع', 'name_en': 'Manufacturing Scrap', 'account_type': 'EXPENSE'})

    # 6. Bank Cash Account
    bank_account, _ = BankCashAccount.objects.get_or_create(
        code='BNK-NBE-01',
        defaults={
            'legal_entity': entity,
            'name_ar': 'البنك الأهلي المصري فرع السادات',
            'name_en': 'National Bank of Egypt - Sadat Branch',
            'gl_account': acc_bank,
            'currency': 'EGP',
            'account_number': '12345678901234'
        }
    )

    # 7. Fiscal Year and Periods
    fy, _ = FiscalYear.objects.get_or_create(
        legal_entity=entity,
        name='FY 2026',
        defaults={'start_date': date(2026, 1, 1), 'end_date': date(2026, 12, 31), 'is_closed': False}
    )
    period_1, _ = FiscalPeriod.objects.get_or_create(
        fiscal_year=fy,
        period_number=1,
        defaults={'name': 'January 2026', 'start_date': date(2026, 1, 1), 'end_date': date(2026, 1, 31), 'is_closed': False}
    )

    # 8. Products
    # Raw Active Ingredient
    chlorpyrifos_tech, _ = Product.objects.get_or_create(
        code='RM-ACT-01',
        defaults={
            'name_ar': 'كلوربيريفوس مادة فنية 98%',
            'name_en': 'Chlorpyrifos Technical Grade 98%',
            'category': 'ACTIVE_INGREDIENT',
            'regulatory_type': 'PESTICIDE_INSECTICIDE',
            'default_uom': uom_kg,
            'density': Decimal('1.3500'), # 1 Liter = 1.35 kg
            'standard_cost': Decimal('350.0000'), # 350 EGP/kg
        }
    )

    # Solvent Raw Material
    solvent_xylene, _ = Product.objects.get_or_create(
        code='RM-SOL-01',
        defaults={
            'name_ar': 'مذيب زيلين صناعي',
            'name_en': 'Xylene Industrial Solvent',
            'category': 'RAW_MATERIAL',
            'default_uom': uom_kg,
            'density': Decimal('0.8600'), # 1 Liter = 0.86 kg
            'standard_cost': Decimal('60.0000'), # 60 EGP/kg
        }
    )

    # Emulsifier Raw Material
    emulsifier_blend, _ = Product.objects.get_or_create(
        code='RM-EMU-01',
        defaults={
            'name_ar': 'خليط مستحلبات كيميائية NP-10',
            'name_en': 'Emulsifier Blend NP-10',
            'category': 'RAW_MATERIAL',
            'default_uom': uom_kg,
            'density': Decimal('1.0500'),
            'standard_cost': Decimal('180.0000'), # 180 EGP/kg
        }
    )

    # Packaging Materials
    bottle_1l, _ = Product.objects.get_or_create(
        code='PKG-BTL-1L',
        defaults={
            'name_ar': 'عبوة بوليمرية معتمة 1 لتر',
            'name_en': '1L Co-ex Fluorinated Bottle',
            'category': 'PACKAGING',
            'default_uom': uom_bottle,
            'density': Decimal('1.0000'),
            'standard_cost': Decimal('8.5000'), # 8.50 EGP/bottle
        }
    )

    # Finished Product: Pyrifos 48% EC
    pyrifos_48ec, _ = Product.objects.get_or_create(
        code='FP-PYRI-48EC',
        defaults={
            'name_ar': 'بيريفوس 48% مركز قابل للاستحلاب EC',
            'name_en': 'Pyrifos 48% EC Insecticide',
            'category': 'FINISHED_PRODUCT',
            'regulatory_type': 'PESTICIDE_INSECTICIDE',
            'formulation_type': 'EC',
            'default_uom': uom_l,
            'density': Decimal('1.1200'), # Density 1.12 kg/L at 20°C
            'target_ph': '5.5 - 6.5',
            'active_ingredient_composition': 'Chlorpyrifos 480 g/L EC',
            'registration_number': 'EG-MALR-2024-4891',
            'standard_cost': Decimal('220.0000'),
            'selling_price': Decimal('320.0000'),
            'standard_shelf_life_days': 730,
        }
    )

    # 9. Partners
    customer, _ = Partner.objects.get_or_create(
        code='CUST-DELTA-01',
        defaults={
            'name_ar': 'شركة الدلتا للتنمية والاستثمار الزراعي',
            'name_en': 'El-Delta Agricultural Development Co.',
            'partner_type': 'CUSTOMER',
            'customer_class': 'DISTRIBUTOR',
            'tax_id': '450-670-890',
            'credit_limit': Decimal('500000.00'),
            'credit_days': 45,
            'territory': 'النوبارية والبحيرة',
            'phone': '01012345678',
        }
    )

    supplier, _ = Partner.objects.get_or_create(
        code='SUPP-GLOBAL-01',
        defaults={
            'name_ar': 'شركة الأهرام لاستيراد الكيماويات والمذيبات',
            'name_en': 'Al-Ahram Chemical & Solvent Imports',
            'partner_type': 'SUPPLIER',
            'tax_id': '111-222-333',
            'credit_limit': Decimal('1000000.00'),
            'credit_days': 60,
            'phone': '01234567890',
        }
    )

    return {
        'entity': entity,
        'factory': factory,
        'wh_raw': wh_raw,
        'wh_fg': wh_fg,
        'wh_pkg': wh_pkg,
        'uom_kg': uom_kg,
        'uom_g': uom_g,
        'uom_l': uom_l,
        'uom_bottle': uom_bottle,
        'uom_carton': uom_carton,
        'chlorpyrifos_tech': chlorpyrifos_tech,
        'solvent_xylene': solvent_xylene,
        'emulsifier_blend': emulsifier_blend,
        'bottle_1l': bottle_1l,
        'pyrifos_48ec': pyrifos_48ec,
        'customer': customer,
        'supplier': supplier,
        'bank_account': bank_account,
        'fy': fy,
        'period_1': period_1,
        'admin_user': admin_user,
    }
