from rest_framework import serializers
from .models import Recipe, RecipeIngredient, RecipePackaging, ProductionOrder, MaterialConsumption

class RecipeIngredientSerializer(serializers.ModelSerializer):
    raw_material_code = serializers.ReadOnlyField(source='raw_material.code')
    raw_material_name = serializers.ReadOnlyField(source='raw_material.name_ar')
    uom_code = serializers.ReadOnlyField(source='uom.code')

    class Meta:
        model = RecipeIngredient
        fields = '__all__'


class RecipePackagingSerializer(serializers.ModelSerializer):
    packaging_code = serializers.ReadOnlyField(source='packaging_material.code')
    packaging_name = serializers.ReadOnlyField(source='packaging_material.name_ar')
    uom_code = serializers.ReadOnlyField(source='uom.code')

    class Meta:
        model = RecipePackaging
        fields = '__all__'


class RecipeSerializer(serializers.ModelSerializer):
    ingredients = RecipeIngredientSerializer(many=True, read_only=True)
    packaging_materials = RecipePackagingSerializer(many=True, read_only=True)
    product_code = serializers.ReadOnlyField(source='product.code')
    product_name = serializers.ReadOnlyField(source='product.name_ar')

    class Meta:
        model = Recipe
        fields = '__all__'


class MaterialConsumptionSerializer(serializers.ModelSerializer):
    product_code = serializers.ReadOnlyField(source='product.code')
    batch_number = serializers.ReadOnlyField(source='batch.batch_number')
    uom_code = serializers.ReadOnlyField(source='uom.code')

    class Meta:
        model = MaterialConsumption
        fields = '__all__'


class ProductionOrderSerializer(serializers.ModelSerializer):
    material_consumptions = MaterialConsumptionSerializer(many=True, read_only=True)
    product_code = serializers.ReadOnlyField(source='product.code')
    product_name = serializers.ReadOnlyField(source='product.name_ar')
    recipe_name = serializers.ReadOnlyField(source='recipe.name')
    uom_code = serializers.ReadOnlyField(source='uom.code')

    class Meta:
        model = ProductionOrder
        fields = '__all__'
