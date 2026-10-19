import uuid
from decimal import Decimal
from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

User = get_user_model()


class AuditLog(models.Model):
    """Authoritative audit log recording all administrative and business changes."""
    ACTION_CHOICES = [
        ('CREATE', _('Create')),
        ('UPDATE', _('Update')),
        ('DELETE', _('Delete')),
        ('POST', _('Post')),
        ('REVERSE', _('Reverse')),
        ('APPROVE', _('Approve')),
        ('REJECT', _('Reject')),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='audit_logs')
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    model_name = models.CharField(max_length=100, db_index=True)
    object_id = models.CharField(max_length=100, db_index=True)
    description = models.TextField(blank=True, default='')
    payload_before = models.JSONField(null=True, blank=True)
    payload_after = models.JSONField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        ordering = ['-timestamp']
        verbose_name = _('Audit Log')
        verbose_name_plural = _('Audit Logs')

    def __str__(self):
        return f"{self.timestamp} - {self.user} - {self.action} {self.model_name}({self.object_id})"


class LegalEntity(models.Model):
    """Company legal entity supporting multi-entity enterprise structures in Egypt."""
    code = models.CharField(max_length=20, unique=True)
    name_ar = models.CharField(max_length=255, verbose_name=_('Company Name (Arabic)'))
    name_en = models.CharField(max_length=255, verbose_name=_('Company Name (English)'))
    tax_id = models.CharField(max_length=50, verbose_name=_('Tax Registration Number (رقم التسجيل الضريبي)'))
    commercial_register = models.CharField(max_length=50, blank=True, default='', verbose_name=_('Commercial Register (السجل التجاري)'))
    currency = models.CharField(max_length=10, default='EGP', verbose_name=_('Base Currency'))
    address = models.TextField(blank=True, default='', verbose_name=_('Address'))
    phone = models.CharField(max_length=50, blank=True, default='', verbose_name=_('Phone'))
    email = models.EmailField(blank=True, default='', verbose_name=_('Email'))
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Legal Entity')
        verbose_name_plural = _('Legal Entities')

    def __str__(self):
        return f"{self.code} - {self.name_ar}"


class Branch(models.Model):
    """Company branches, factories, and operational offices."""
    legal_entity = models.ForeignKey(LegalEntity, on_delete=models.CASCADE, related_name='branches')
    code = models.CharField(max_length=20, unique=True)
    name_ar = models.CharField(max_length=255, verbose_name=_('Branch Name (Arabic)'))
    name_en = models.CharField(max_length=255, verbose_name=_('Branch Name (English)'))
    is_factory = models.BooleanField(default=False, verbose_name=_('Is Chemical Factory / Formulation Plant'))
    address = models.TextField(blank=True, default='')
    phone = models.CharField(max_length=50, blank=True, default='')
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = _('Branch')
        verbose_name_plural = _('Branches')

    def __str__(self):
        return f"{self.code} - {self.name_ar}"


class Warehouse(models.Model):
    """Warehouses and specialized chemical storage facilities."""
    WAREHOUSE_TYPES = [
        ('RAW_MATERIALS', _('Chemical Raw Materials')),
        ('ACTIVE_INGREDIENTS', _('Active Ingredients & Technical Actives')),
        ('PACKAGING', _('Packaging Materials')),
        ('WIP', _('Work-In-Process / Intermediates')),
        ('FINISHED_GOODS', _('Finished Goods')),
        ('QUARANTINE', _('Quarantine / Awaiting Inspection')),
        ('QUALITY_HOLD', _('Quality Hold')),
        ('DAMAGED_REJECTED', _('Damaged / Rejected Stock')),
        ('EXPIRED', _('Expired Stock')),
    ]
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='warehouses')
    code = models.CharField(max_length=20, unique=True)
    name_ar = models.CharField(max_length=255)
    name_en = models.CharField(max_length=255)
    warehouse_type = models.CharField(max_length=30, choices=WAREHOUSE_TYPES, default='FINISHED_GOODS')
    is_temperature_controlled = models.BooleanField(default=False, help_text=_('For temperature-sensitive pesticides/biostimulants'))
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = _('Warehouse')
        verbose_name_plural = _('Warehouses')

    def __str__(self):
        return f"{self.code} - {self.name_ar} ({self.get_warehouse_type_display()})"


class StorageLocation(models.Model):
    """Bin, rack, tank, or silo within a warehouse."""
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='locations')
    code = models.CharField(max_length=30)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, default='')
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('warehouse', 'code')
        verbose_name = _('Storage Location')
        verbose_name_plural = _('Storage Locations')

    def __str__(self):
        return f"{self.warehouse.code} / {self.code}"


class UnitOfMeasure(models.Model):
    """Units of Measure (UOM) with categorical classification."""
    UOM_TYPES = [
        ('WEIGHT', _('Weight (kg, g, ton)')),
        ('VOLUME', _('Volume (L, mL, m3)')),
        ('UNIT', _('Unit / Count (piece, bottle, carton, drum, pallet)')),
    ]
    code = models.CharField(max_length=10, unique=True)
    name_ar = models.CharField(max_length=50)
    name_en = models.CharField(max_length=50)
    category = models.CharField(max_length=20, choices=UOM_TYPES)
    base_ratio = models.DecimalField(max_digits=16, decimal_places=6, default=Decimal('1.000000'),
                                     help_text=_('Ratio relative to the standard unit of the category, e.g. 1 ton = 1000 kg'))

    class Meta:
        verbose_name = _('Unit of Measure')
        verbose_name_plural = _('Units of Measure')

    def __str__(self):
        return f"{self.code} ({self.name_ar})"


class Product(models.Model):
    """Chemical master catalog: pesticides, fertilizers, nutrients, raw materials, packaging."""
    PRODUCT_CATEGORIES = [
        ('RAW_MATERIAL', _('Chemical Raw Material / Solvent / Emulsifier')),
        ('ACTIVE_INGREDIENT', _('Active Ingredient (Technical Grade)')),
        ('PACKAGING', _('Packaging Material (Bottle, Cap, Label, Carton)')),
        ('INTERMEDIATE', _('Formulated Intermediate / Bulk Blend')),
        ('FINISHED_PRODUCT', _('Finished Agricultural Product')),
    ]
    REGULATORY_TYPES = [
        ('PESTICIDE_INSECTICIDE', _('Agricultural Insecticide (مبيد حشري)')),
        ('PESTICIDE_FUNGICIDE', _('Agricultural Fungicide (مبيد فطري)')),
        ('PESTICIDE_HERBICIDE', _('Agricultural Herbicide (مبيد حشائش)')),
        ('PESTICIDE_ACARICIDE', _('Acaricide / Nematicide (مبيد أكاروسي/نيماتودي)')),
        ('FERTILIZER_MINERAL', _('Mineral / Chemical Fertilizer (سماد كيميائي/معدني)')),
        ('FERTILIZER_NPK_SOLUBLE', _('Water-Soluble NPK (سماد مركب ذواب)')),
        ('FERTILIZER_SUSPENSION', _('Suspension / Liquid Fertilizer (سماد سائل/معلق)')),
        ('MICRONUTRIENT', _('Chelated Micronutrient (عناصر صغرى مخلبية)')),
        ('BIOSTIMULANT', _('Biostimulant / Amino Acids (منشط حيوي/أحماض أمينية)')),
        ('ADJUVANT', _('Agricultural Adjuvant / Spreader (مادة ناشرة/لاصقة)')),
        ('NON_REGULATED', _('Packaging or General Industrial Material')),
    ]
    FORMULATION_TYPES = [
        ('EC', 'Emulsifiable Concentrate (مركز قابل للاستحلاب)'),
        ('SC', 'Suspension Concentrate (مركز معلق)'),
        ('SL', 'Soluble Liquid (سائل قابل للذوبان)'),
        ('WP', 'Wettable Powder (مسحوق قابل للبلل)'),
        ('WG', 'Water Dispersible Granules (حبيبات قابلة للانتشار بالماء)'),
        ('SP', 'Soluble Powder (مسحوق ذواب)'),
        ('EW', 'Emulsion, Oil in Water (مستحلب زيت في ماء)'),
        ('GR', 'Granules (محببات)'),
        ('LIQUID', 'Liquid Solution (محلول سائل)'),
        ('POWDER', 'Powder / Crystal (بودرة / بلورات)'),
        ('NONE', 'Not Applicable / Packaging'),
    ]

    code = models.CharField(max_length=50, unique=True)
    name_ar = models.CharField(max_length=255, verbose_name=_('Trade / Commercial Name (Arabic)'))
    name_en = models.CharField(max_length=255, verbose_name=_('Trade / Commercial Name (English)'))
    category = models.CharField(max_length=30, choices=PRODUCT_CATEGORIES, default='FINISHED_PRODUCT')
    regulatory_type = models.CharField(max_length=40, choices=REGULATORY_TYPES, default='NON_REGULATED')
    formulation_type = models.CharField(max_length=20, choices=FORMULATION_TYPES, default='NONE')
    default_uom = models.ForeignKey(UnitOfMeasure, on_delete=models.PROTECT, related_name='products')

    # Chemical & Physical Technical Specifications
    density = models.DecimalField(
        max_digits=8, decimal_places=4, default=Decimal('1.0000'),
        help_text=_('Product-specific density in kg/L at 20°C for exact weight-volume conversion')
    )
    target_ph = models.CharField(max_length=50, blank=True, default='', help_text=_('Target pH specification range, e.g. 5.5 - 6.5'))
    viscosity = models.CharField(max_length=50, blank=True, default='', help_text=_('Viscosity specification (cP or mPa.s)'))
    active_ingredient_composition = models.TextField(
        blank=True, default='',
        help_text=_('Declared chemical active ingredients e.g. Chlorpyrifos 480 g/L or NPK 20-20-20 + TE')
    )
    registration_number = models.CharField(
        max_length=100, blank=True, default='',
        verbose_name=_('Ministry of Agriculture Registration No (رقم التسجيل بوزارة الزراعة)')
    )
    registration_expiry = models.DateField(null=True, blank=True, verbose_name=_('Registration Expiry Date'))
    standard_shelf_life_days = models.PositiveIntegerField(default=730, help_text=_('Shelf life in days from manufacturing'))

    # Valuation & Planning
    standard_cost = models.DecimalField(max_digits=14, decimal_places=4, default=Decimal('0.0000'))
    selling_price = models.DecimalField(max_digits=14, decimal_places=4, default=Decimal('0.0000'))
    reorder_level = models.DecimalField(max_digits=14, decimal_places=4, default=Decimal('0.0000'))
    safety_stock = models.DecimalField(max_digits=14, decimal_places=4, default=Decimal('0.0000'))
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['code']
        verbose_name = _('Product / Material')
        verbose_name_plural = _('Products & Materials')

    def __str__(self):
        return f"{self.code} - {self.name_ar}"

    def convert_quantity(self, quantity: Decimal, from_uom: UnitOfMeasure, to_uom: UnitOfMeasure) -> Decimal:
        """
        Converts quantity between UOMs using product-specific conversions or chemical density.
        Crucial: Never assumes 1L == 1kg without product density!
        """
        if from_uom == to_uom:
            return quantity

        # 1. Check for explicit conversion record
        explicit = ProductUOMConversion.objects.filter(
            product=self, from_uom=from_uom, to_uom=to_uom
        ).first()
        if explicit:
            return quantity * explicit.conversion_factor

        reverse_explicit = ProductUOMConversion.objects.filter(
            product=self, from_uom=to_uom, to_uom=from_uom
        ).first()
        if reverse_explicit and reverse_explicit.conversion_factor > Decimal('0'):
            return quantity / reverse_explicit.conversion_factor

        # 2. Check if within same category (e.g. g to kg, or mL to L)
        if from_uom.category == to_uom.category:
            base_amount = quantity * from_uom.base_ratio
            return base_amount / to_uom.base_ratio

        # 3. Inter-category conversion: Weight <-> Volume using chemical density (kg/L)
        if from_uom.category == 'VOLUME' and to_uom.category == 'WEIGHT':
            liters = quantity * from_uom.base_ratio
            kg = liters * self.density
            return kg / to_uom.base_ratio

        if from_uom.category == 'WEIGHT' and to_uom.category == 'VOLUME':
            kg = quantity * from_uom.base_ratio
            if self.density <= Decimal('0'):
                raise ValueError(f"Cannot convert weight to volume: Invalid density {self.density} for product {self.code}")
            liters = kg / self.density
            return liters / to_uom.base_ratio

        raise ValueError(f"No valid conversion available between {from_uom.code} and {to_uom.code} for product {self.code}")


class ProductUOMConversion(models.Model):
    """Product-specific packaging and UOM conversion factors."""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='uom_conversions')
    from_uom = models.ForeignKey(UnitOfMeasure, on_delete=models.CASCADE, related_name='+')
    to_uom = models.ForeignKey(UnitOfMeasure, on_delete=models.CASCADE, related_name='+')
    conversion_factor = models.DecimalField(
        max_digits=16, decimal_places=6,
        help_text=_('Factor to multiply from_uom quantity by to obtain to_uom quantity (e.g. 1 Carton = 12 Bottles)')
    )

    class Meta:
        unique_together = ('product', 'from_uom', 'to_uom')
        verbose_name = _('Product UOM Conversion')
        verbose_name_plural = _('Product UOM Conversions')

    def __str__(self):
        return f"{self.product.code}: 1 {self.from_uom.code} = {self.conversion_factor} {self.to_uom.code}"


class Partner(models.Model):
    """Customers, suppliers, and agricultural distribution agents in Egypt."""
    PARTNER_TYPES = [
        ('CUSTOMER', _('Customer / Distributor / Agricultural Agent')),
        ('SUPPLIER', _('Supplier / Chemical Importer / Packaging Manufacturer')),
        ('BOTH', _('Customer & Supplier')),
    ]
    CUSTOMER_CLASSES = [
        ('KEY_ACCOUNT', _('Key Agricultural Account / Mega Farm')),
        ('DISTRIBUTOR', _('Wholesale Chemical Distributor (تاجر جملة)')),
        ('RETAILER', _('Agricultural Retailer / Agro Pharmacy (محل مبيدات وأسمدة)')),
        ('DIRECT_FARM', _('Direct Farm / Reclamation Project')),
        ('EXPORT', _('International / Export Client')),
    ]
    code = models.CharField(max_length=30, unique=True)
    name_ar = models.CharField(max_length=255, verbose_name=_('Name (Arabic)'))
    name_en = models.CharField(max_length=255, verbose_name=_('Name (English)'))
    partner_type = models.CharField(max_length=20, choices=PARTNER_TYPES, default='CUSTOMER')
    customer_class = models.CharField(max_length=30, choices=CUSTOMER_CLASSES, default='DISTRIBUTOR')

    # Egyptian Tax & Commercial Identifiers
    tax_id = models.CharField(max_length=50, blank=True, default='', verbose_name=_('Tax Registration No (رقم التسجيل الضريبي)'))
    commercial_register = models.CharField(max_length=50, blank=True, default='', verbose_name=_('Commercial Register (السجل التجاري)'))
    national_id = models.CharField(max_length=20, blank=True, default='', verbose_name=_('National ID (الرقم القومي للتاجر/المزارع)'))

    # Credit Policies & Payment Terms
    credit_limit = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'), verbose_name=_('Credit Limit (EGP)'))
    credit_days = models.PositiveIntegerField(default=0, verbose_name=_('Credit Days'))
    payment_terms = models.CharField(max_length=100, blank=True, default='', verbose_name=_('Payment Terms Description'))
    territory = models.CharField(max_length=100, blank=True, default='', help_text=_('Agricultural Governorate / Territory in Egypt, e.g. Beheira, Nobariya, Sharkia, Sadat'))

    phone = models.CharField(max_length=50, blank=True, default='')
    email = models.EmailField(blank=True, default='')
    address = models.TextField(blank=True, default='')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['code']
        verbose_name = _('Business Partner')
        verbose_name_plural = _('Business Partners')

    def __str__(self):
        return f"{self.code} - {self.name_ar} ({self.get_partner_type_display()})"
