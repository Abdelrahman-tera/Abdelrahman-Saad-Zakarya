from decimal import Decimal
from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.core.models import (
    LegalEntity, Branch, Warehouse, StorageLocation, UnitOfMeasure,
    Product, ProductUOMConversion, Partner
)
from apps.accounting.models import Account, BankCashAccount, FiscalYear, FiscalPeriod, JournalEntry, JournalItem
from apps.inventory.models import Batch, InventoryService
from apps.manufacturing.models import Recipe, RecipeIngredient, RecipePackaging, ProductionOrder
from apps.quality.models import QualitySpecification, QualityParameter, QualityInspection, QualityInspectionResult

User = get_user_model()

class Command(BaseCommand):
    help = 'Seeds enterprise demo test data for Egyptian Agrochemical Manufacturing (NON-PRODUCTION).'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('Seeding demo data (NON-PRODUCTION)...'))

        # 1. Admin User
        admin_user, created = User.objects.get_or_create(
            username='admin',
            defaults={'email': 'admin@demo.agrochemical-eg.com', 'is_staff': True, 'is_superuser': True}
        )
        if created:
            admin_user.set_password('AdminPass2026!')
            admin_user.save()
            self.stdout.write('Created superuser: admin / AdminPass2026!')

        # 2. Legal Entity
        entity, _ = LegalEntity.objects.get_or_create(
            code='EGY-DEMO-01',
            defaults={
                'name_ar': 'شركة مصر للصناعات الكيماوية والزراعية ش.م.م (بيانات تجريبية)',
                'name_en': 'Misr Agrochemical & Fertilizer Industries S.A.E (NON-PRODUCTION DEMO)',
                'tax_id': '100-200-300',
                'commercial_register': '98765-Giza',
                'currency': 'EGP',
                'address': 'المنطقة الصناعية الثانية - مدينة السادات - مصر',
            }
        )

        # 3. Factory & Warehouses
        factory, _ = Branch.objects.get_or_create(
            code='BR-SADAT',
            defaults={
                'legal_entity': entity,
                'name_ar': 'مصنع السادات لتركيب وتعبئة المبيدات والأسمدة',
                'name_en': 'Sadat City Chemical Formulation Plant',
                'is_factory': True,
            }
        )
        wh_raw, _ = Warehouse.objects.get_or_create(
            code='WH-RAW',
            defaults={'branch': factory, 'name_ar': 'مستودع المواد الخام الكيميائية والمذيبات', 'name_en': 'Raw Chemical & Solvent Warehouse', 'warehouse_type': 'RAW_MATERIALS'}
        )
        wh_fg, _ = Warehouse.objects.get_or_create(
            code='WH-FG',
            defaults={'branch': factory, 'name_ar': 'مستودع المنتج التام للأسمدة والمبيدات', 'name_en': 'Finished Agrochemicals Warehouse', 'warehouse_type': 'FINISHED_GOODS'}
        )
        wh_pkg, _ = Warehouse.objects.get_or_create(
            code='WH-PKG',
            defaults={'branch': factory, 'name_ar': 'مستودع مواد التعبئة والأغطية', 'name_en': 'Packaging Materials Warehouse', 'warehouse_type': 'PACKAGING'}
        )
        wh_quar, _ = Warehouse.objects.get_or_create(
            code='WH-QUAR',
            defaults={'branch': factory, 'name_ar': 'مستودع الحجر والفحص الكيميائي', 'name_en': 'Chemical Quarantine Warehouse', 'warehouse_type': 'QUARANTINE'}
        )

        # 4. Units of Measure
        uom_kg, _ = UnitOfMeasure.objects.get_or_create(code='KG', defaults={'name_ar': 'كيلوجرام', 'name_en': 'Kilogram', 'category': 'WEIGHT', 'base_ratio': Decimal('1.000000')})
        uom_g, _ = UnitOfMeasure.objects.get_or_create(code='G', defaults={'name_ar': 'جرام', 'name_en': 'Gram', 'category': 'WEIGHT', 'base_ratio': Decimal('0.001000')})
        uom_ton, _ = UnitOfMeasure.objects.get_or_create(code='TON', defaults={'name_ar': 'طن متري', 'name_en': 'Metric Ton', 'category': 'WEIGHT', 'base_ratio': Decimal('1000.000000')})
        uom_l, _ = UnitOfMeasure.objects.get_or_create(code='L', defaults={'name_ar': 'لتر', 'name_en': 'Liter', 'category': 'VOLUME', 'base_ratio': Decimal('1.000000')})
        uom_btl, _ = UnitOfMeasure.objects.get_or_create(code='BTL', defaults={'name_ar': 'عبوة 1 لتر', 'name_en': '1L Bottle', 'category': 'UNIT', 'base_ratio': Decimal('1.000000')})
        uom_ctn, _ = UnitOfMeasure.objects.get_or_create(code='CTN', defaults={'name_ar': 'كرتونة 12 عبوة', 'name_en': 'Carton (12x1L)', 'category': 'UNIT', 'base_ratio': Decimal('1.000000')})

        # 5. Accounts
        acc_bank, _ = Account.objects.get_or_create(code='1001', defaults={'name_ar': 'البنك الأهلي المصري - حساب جاري', 'name_en': 'NBE Bank Account', 'account_type': 'ASSET'})
        acc_ar, _ = Account.objects.get_or_create(code='1101', defaults={'name_ar': 'العملاء وأوراق القبض', 'name_en': 'Accounts Receivable', 'account_type': 'ASSET', 'is_reconcilable': True})
        acc_wht_rec, _ = Account.objects.get_or_create(code='1105', defaults={'name_ar': 'ضريبة الخصم والإضافة المدينة (أ.ت.ص)', 'name_en': 'WHT Receivable', 'account_type': 'ASSET'})
        acc_raw_inv, _ = Account.objects.get_or_create(code='1201', defaults={'name_ar': 'مخزون المواد الخام الكيماوية', 'name_en': 'Raw Materials Inventory', 'account_type': 'ASSET'})
        acc_wip, _ = Account.objects.get_or_create(code='1203', defaults={'name_ar': 'إنتاج تحت التشغيل (WIP)', 'name_en': 'Work In Process (WIP)', 'account_type': 'ASSET'})
        acc_fg_inv, _ = Account.objects.get_or_create(code='1204', defaults={'name_ar': 'مخزون الإنتاج التام', 'name_en': 'Finished Goods Inventory', 'account_type': 'ASSET'})
        acc_input_vat, _ = Account.objects.get_or_create(code='1205', defaults={'name_ar': 'ضريبة القيمة المضافة - مدخلات', 'name_en': 'Input VAT Recoverable', 'account_type': 'ASSET'})
        acc_interim_stock, _ = Account.objects.get_or_create(code='1209', defaults={'name_ar': 'وسيط استلام البضائع والمواد', 'name_en': 'Goods Received Interim Clearing', 'account_type': 'ASSET'})
        acc_ap, _ = Account.objects.get_or_create(code='2101', defaults={'name_ar': 'الموردون وأوراق الدفع', 'name_en': 'Accounts Payable', 'account_type': 'LIABILITY', 'is_reconcilable': True})
        acc_wht_pay, _ = Account.objects.get_or_create(code='2106', defaults={'name_ar': 'ضريبة الخصم والتحصيل الدائنة (منبع)', 'name_en': 'Withholding Tax Payable', 'account_type': 'LIABILITY'})
        acc_interim_ap, _ = Account.objects.get_or_create(code='2109', defaults={'name_ar': 'وسيط فواتير الموردين غير المستلمة', 'name_en': 'Unbilled Supplier Accrual', 'account_type': 'LIABILITY'})
        acc_output_vat, _ = Account.objects.get_or_create(code='2201', defaults={'name_ar': 'ضريبة القيمة المضافة - مخرجات', 'name_en': 'Output VAT Payable', 'account_type': 'LIABILITY'})
        acc_revenue, _ = Account.objects.get_or_create(code='4101', defaults={'name_ar': 'إيرادات مبيعات المبيدات والأسمدة', 'name_en': 'Sales Revenue', 'account_type': 'REVENUE'})
        acc_cogs, _ = Account.objects.get_or_create(code='5101', defaults={'name_ar': 'تكلفة البضاعة المباعة (COGS)', 'name_en': 'Cost of Goods Sold', 'account_type': 'EXPENSE'})
        acc_scrap, _ = Account.objects.get_or_create(code='5105', defaults={'name_ar': 'انحراف وتوالف تصنيع كيميائي', 'name_en': 'Manufacturing Scrap Variance', 'account_type': 'EXPENSE'})

        # Bank Account
        BankCashAccount.objects.get_or_create(
            code='BNK-NBE-DEMO',
            defaults={'legal_entity': entity, 'name_ar': 'البنك الأهلي المصري - فرع السادات', 'name_en': 'NBE Bank Sadat', 'gl_account': acc_bank, 'currency': 'EGP', 'account_number': '1234567890'}
        )

        # 6. Agrochemical Products Catalog
        # Product 1: Insecticide Pyrifos 48% EC
        p1, _ = Product.objects.get_or_create(
            code='FP-PYRI-48EC',
            defaults={
                'name_ar': 'مبيد بيريفوس 48% مركز قابل للاستحلاب EC',
                'name_en': 'Pyrifos 48% EC Insecticide',
                'category': 'FINISHED_PRODUCT',
                'regulatory_type': 'PESTICIDE_INSECTICIDE',
                'formulation_type': 'EC',
                'default_uom': uom_l,
                'density': Decimal('1.1200'),
                'target_ph': '5.5 - 6.5',
                'active_ingredient_composition': 'Chlorpyrifos 480 g/L EC',
                'registration_number': 'EG-MALR-2024-4891',
                'standard_cost': Decimal('220.0000'),
                'selling_price': Decimal('320.0000'),
                'reorder_level': Decimal('500.0000'),
                'safety_stock': Decimal('200.0000'),
            }
        )

        # Product 2: Fertilizer NPK 20-20-20 + TE Soluble
        p2, _ = Product.objects.get_or_create(
            code='FP-NPK-202020',
            defaults={
                'name_ar': 'سماد مركب ذواب NPK 20-20-20 + عناصر صغرى',
                'name_en': 'Water-Soluble NPK 20-20-20 + TE Fertilizer',
                'category': 'FINISHED_PRODUCT',
                'regulatory_type': 'FERTILIZER_NPK_SOLUBLE',
                'formulation_type': 'POWDER',
                'default_uom': uom_kg,
                'density': Decimal('1.0000'),
                'active_ingredient_composition': 'N: 20%, P2O5: 20%, K2O: 20% + Fe, Zn, Mn, Cu, B, Mo',
                'registration_number': 'EG-FERT-2025-1022',
                'standard_cost': Decimal('85.0000'),
                'selling_price': Decimal('125.0000'),
                'reorder_level': Decimal('2000.0000'),
                'safety_stock': Decimal('500.0000'),
            }
        )

        # Product 3: Biostimulant Amino Acid Liquid
        p3, _ = Product.objects.get_or_create(
            code='FP-BIO-AMINO',
            defaults={
                'name_ar': 'منشط حيوي أحماض أمينية حرة 25% سائل',
                'name_en': 'Free Amino Acids 25% Liquid Biostimulant',
                'category': 'FINISHED_PRODUCT',
                'regulatory_type': 'BIOSTIMULANT',
                'formulation_type': 'LIQUID',
                'default_uom': uom_l,
                'density': Decimal('1.1800'),
                'target_ph': '4.5 - 5.5',
                'registration_number': 'EG-BIO-2025-0914',
                'standard_cost': Decimal('110.0000'),
                'selling_price': Decimal('175.0000'),
            }
        )

        # Product 4: Raw Active Ingredient
        rm1, _ = Product.objects.get_or_create(
            code='RM-CHLOR-TECH',
            defaults={
                'name_ar': 'كلوربيريفوس خام فني 98%',
                'name_en': 'Chlorpyrifos Technical Grade 98%',
                'category': 'ACTIVE_INGREDIENT',
                'regulatory_type': 'PESTICIDE_INSECTICIDE',
                'default_uom': uom_kg,
                'density': Decimal('1.3500'),
                'standard_cost': Decimal('350.0000'),
            }
        )

        # Product 5: Solvent Xylene
        rm2, _ = Product.objects.get_or_create(
            code='RM-XYLENE',
            defaults={
                'name_ar': 'مذيب زيلين صناعي نقي',
                'name_en': 'Pure Industrial Xylene Solvent',
                'category': 'RAW_MATERIAL',
                'default_uom': uom_kg,
                'density': Decimal('0.8600'),
                'standard_cost': Decimal('60.0000'),
            }
        )

        # Product 6: Packaging Bottle
        pkg1, _ = Product.objects.get_or_create(
            code='PKG-BTL-1L',
            defaults={
                'name_ar': 'عبوة بوليمرية متعددة الطبقات 1 لتر',
                'name_en': '1L Co-ex Fluorinated Bottle with Induction Seal Cap',
                'category': 'PACKAGING',
                'default_uom': uom_btl,
                'density': Decimal('1.0000'),
                'standard_cost': Decimal('8.5000'),
            }
        )

        # 7. Partners
        cust1, _ = Partner.objects.get_or_create(
            code='CUST-DELTA-01',
            defaults={
                'name_ar': 'شركة الدلتا للتنمية والاستثمار الزراعي',
                'name_en': 'El-Delta Agricultural Development Co.',
                'partner_type': 'CUSTOMER',
                'customer_class': 'DISTRIBUTOR',
                'tax_id': '450-670-890',
                'commercial_register': '88412-Damanhour',
                'credit_limit': Decimal('750000.00'),
                'credit_days': 45,
                'territory': 'النوبارية والبحيرة',
                'phone': '01012345678',
            }
        )

        supp1, _ = Partner.objects.get_or_create(
            code='SUPP-AHRAM-01',
            defaults={
                'name_ar': 'شركة الأهرام لاستيراد الكيماويات والمذيبات',
                'name_en': 'Al-Ahram Chemical & Solvent Imports',
                'partner_type': 'SUPPLIER',
                'tax_id': '111-222-333',
                'commercial_register': '33412-Cairo',
                'credit_limit': Decimal('1500000.00'),
                'credit_days': 60,
                'phone': '01234567890',
            }
        )

        # 8. Seed Batches and Stock
        today = date(2026, 1, 15)
        b_p1, _ = Batch.objects.get_or_create(
            product=p1, batch_number='PYRI-B26-001',
            defaults={'manufacturing_date': today - timedelta(days=10), 'expiry_date': today + timedelta(days=720), 'status': 'RELEASED', 'initial_quantity': Decimal('2000.0000'), 'uom': uom_l}
        )
        InventoryService.record_movement('RECEIPT_PRODUCTION', p1, wh_fg, Decimal('2000.0000'), uom_l, Decimal('220.0000'), 'INIT-SEED', b_p1)

        b_p2, _ = Batch.objects.get_or_create(
            product=p2, batch_number='NPK-B26-101',
            defaults={'manufacturing_date': today - timedelta(days=5), 'expiry_date': today + timedelta(days=1095), 'status': 'RELEASED', 'initial_quantity': Decimal('5000.0000'), 'uom': uom_kg}
        )
        InventoryService.record_movement('RECEIPT_PRODUCTION', p2, wh_fg, Decimal('5000.0000'), uom_kg, Decimal('85.0000'), 'INIT-SEED', b_p2)

        b_rm1, _ = Batch.objects.get_or_create(
            product=rm1, batch_number='CHLOR-LOT-9901',
            defaults={'supplier_lot_number': 'SINO-TECH-9901', 'manufacturing_date': today - timedelta(days=30), 'expiry_date': today + timedelta(days=700), 'status': 'RELEASED', 'initial_quantity': Decimal('3000.0000'), 'uom': uom_kg}
        )
        InventoryService.record_movement('RECEIPT_PURCHASE', rm1, wh_raw, Decimal('3000.0000'), uom_kg, Decimal('350.0000'), 'INIT-SEED', b_rm1)

        b_rm2, _ = Batch.objects.get_or_create(
            product=rm2, batch_number='XYL-LOT-4410',
            defaults={'supplier_lot_number': 'PETRO-XYL-4410', 'manufacturing_date': today - timedelta(days=20), 'expiry_date': today + timedelta(days=710), 'status': 'RELEASED', 'initial_quantity': Decimal('6000.0000'), 'uom': uom_kg}
        )
        InventoryService.record_movement('RECEIPT_PURCHASE', rm2, wh_raw, Decimal('6000.0000'), uom_kg, Decimal('60.0000'), 'INIT-SEED', b_rm2)

        # 9. Seed Approved Formulation Recipe for Pyrifos 48% EC
        rec, _ = Recipe.objects.get_or_create(
            product=p1, version='v1.0',
            defaults={
                'name': 'التركيبة المعتمدة لبيريفوس 48% مركز قابل للاستحلاب',
                'reference_batch_size': Decimal('1000.0000'),
                'uom': uom_l,
                'expected_yield_percent': Decimal('98.50'),
                'loss_tolerance_percent': Decimal('2.00'),
                'status': 'APPROVED',
                'approved_by': admin_user
            }
        )
        RecipeIngredient.objects.get_or_create(recipe=rec, raw_material=rm1, defaults={'quantity_required': Decimal('490.0000'), 'uom': uom_kg, 'is_active_ingredient': True, 'sequence': 1})
        RecipeIngredient.objects.get_or_create(recipe=rec, raw_material=rm2, defaults={'quantity_required': Decimal('530.0000'), 'uom': uom_kg, 'is_active_ingredient': False, 'sequence': 2})
        RecipePackaging.objects.get_or_create(recipe=rec, packaging_material=pkg1, defaults={'quantity_required': Decimal('1000.0000'), 'uom': uom_btl, 'label_revision': 'REV-2025-B', 'is_label_approved': True})

        self.stdout.write(self.style.SUCCESS('Successfully seeded complete enterprise Agrochemical ERP demo test data!'))
