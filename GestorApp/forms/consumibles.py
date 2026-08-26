"""Forms del modulo de consumibles (stock por cantidad)."""
from decimal import Decimal

from django import forms
from django.core.exceptions import ValidationError

from ..models import (
    CategoriaEquipo,
    OrdenCompra,
    Personal,
    ProductoConsumible,
    Proveedor,
    TipoCategoriaInventario,
    TipoMovimientoStock,
    Ubicacion,
    UnidadConsumible,
)


class ProductoConsumibleForm(forms.ModelForm):
    class Meta:
        model = ProductoConsumible
        fields = [
            "sku",
            "nombre",
            "descripcion",
            "categoria",
            "unidad",
            "stock_minimo",
            "costo_aproximado",
            "ubicacion",
            "proveedor",
            "activo",
        ]
        labels = {
            "sku": "SKU / codigo",
            "nombre": "Nombre",
            "descripcion": "Descripcion",
            "categoria": "Categoria",
            "unidad": "Unidad",
            "stock_minimo": "Stock minimo",
            "costo_aproximado": "Costo unitario approx.",
            "ubicacion": "Ubicacion",
            "proveedor": "Proveedor",
            "activo": "Activo",
        }
        help_texts = {
            "sku": "Codigo unico del producto (ej. ALC-ISO-1L).",
            "categoria": "Solo categorias de tipo Consumible.",
            "stock_minimo": "Alerta cuando el stock sea menor o igual a este valor.",
            "costo_aproximado": "Opcional, para estimar valor en almacen.",
        }
        widgets = {
            "descripcion": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["categoria"].queryset = CategoriaEquipo.objects.filter(
            tipo=TipoCategoriaInventario.CONSUMIBLE,
            activo=True,
        ).order_by("nombre_categoria")
        if self.instance and self.instance.categoria_id:
            self.fields["categoria"].queryset = (
                CategoriaEquipo.objects.filter(pk=self.instance.categoria_id)
                | self.fields["categoria"].queryset
            ).distinct().order_by("nombre_categoria")
        self.fields["ubicacion"].queryset = Ubicacion.objects.select_related(
            "edificio", "zona"
        ).order_by("edificio__nombre_edificio", "zona__nombre_zona", "referencia")
        self.fields["ubicacion"].required = False
        self.fields["proveedor"].queryset = Proveedor.objects.filter(activo=True).order_by(
            "nombre_proveedor"
        )
        self.fields["proveedor"].required = False
        self.fields["descripcion"].required = False


class MovimientoStockForm(forms.Form):
    tipo_movimiento = forms.ChoiceField(
        choices=TipoMovimientoStock.choices,
        label="Tipo",
    )
    cantidad = forms.DecimalField(
        min_value=Decimal("0.01"),
        max_digits=12,
        decimal_places=2,
        label="Cantidad",
        help_text="Entrada/Salida: unidades a sumar o restar. Ajuste: stock resultante.",
    )
    motivo = forms.CharField(
        required=False,
        max_length=255,
        label="Motivo",
        widget=forms.TextInput(attrs={"placeholder": "Compra, uso en ticket, conteo..."}),
    )
    responsable = forms.ModelChoiceField(
        queryset=Personal.objects.none(),
        required=False,
        label="Responsable",
    )
    orden_compra = forms.ModelChoiceField(
        queryset=OrdenCompra.objects.none(),
        required=False,
        label="Orden de compra",
        help_text="Opcional, para entradas por compra.",
    )

    def __init__(self, *args, producto=None, tipo_fijo=None, **kwargs):
        self.producto = producto
        super().__init__(*args, **kwargs)
        self.fields["responsable"].queryset = Personal.objects.filter(activo=True).order_by(
            "numero_empleado", "nombre", "apellido_paterno"
        )
        self.fields["orden_compra"].queryset = OrdenCompra.objects.order_by("-creado_en")[:80]
        if tipo_fijo:
            self.fields["tipo_movimiento"].initial = tipo_fijo
            self.fields["tipo_movimiento"].widget = forms.HiddenInput()
            if tipo_fijo == TipoMovimientoStock.AJUSTE:
                self.fields["cantidad"].label = "Stock resultante"
                self.fields["cantidad"].help_text = (
                    f"Stock actual: {producto.stock_actual if producto else 0}. "
                    "Indica el nuevo valor tras el conteo."
                )
                if producto and not self.is_bound:
                    self.fields["cantidad"].initial = producto.stock_actual
            elif tipo_fijo == TipoMovimientoStock.SALIDA:
                self.fields["cantidad"].help_text = (
                    f"Disponible: {producto.stock_actual if producto else 0} "
                    f"{producto.get_unidad_display() if producto else ''}."
                )
            elif tipo_fijo == TipoMovimientoStock.ENTRADA:
                self.fields["orden_compra"].required = False

    def clean_cantidad(self):
        cantidad = self.cleaned_data["cantidad"]
        tipo = self.cleaned_data.get("tipo_movimiento") or self.fields["tipo_movimiento"].initial
        if self.producto and tipo == TipoMovimientoStock.SALIDA:
            if cantidad > (self.producto.stock_actual or Decimal("0")):
                raise ValidationError(
                    f"Stock insuficiente (disponible: {self.producto.stock_actual})."
                )
        if tipo == TipoMovimientoStock.AJUSTE and cantidad < 0:
            raise ValidationError("El stock resultante no puede ser negativo.")
        return cantidad
