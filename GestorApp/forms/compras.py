"""Forms de plantillas y órdenes de compra."""

from django import forms

from .. import document_engine
from ..models import (
    DetalleOrdenCompra,
    EstadoOrdenCompra,
    IvaOpcion,
    OrdenCompra,
    PlantillaDocumento,
    Proveedor,
    TipoPlantillaDocumento,
)


class PlantillaDocumentoForm(forms.ModelForm):
    class Meta:
        model = PlantillaDocumento
        fields = ["nombre", "descripcion", "archivo", "activo"]
        labels = {
            "nombre": "Nombre",
            "descripcion": "Descripcion",
            "archivo": "Archivo de la plantilla",
            "activo": "Activa",
        }
        help_texts = {
            "archivo": (
                "Sube un archivo .docx, .xlsx o .pdf (maximo 50 MB). En Word/Excel "
                "escribe los campos como {{nombre_campo}}; en PDF usa un archivo "
                "con campos de formulario."
            ),
        }
        widgets = {
            "descripcion": forms.Textarea(attrs={"rows": 3}),
        }

    def clean_archivo(self):
        from ..media_security import validate_plantilla_upload

        archivo = validate_plantilla_upload(self.cleaned_data.get("archivo"))
        if not archivo:
            return archivo

        nombre_archivo = archivo.name.lower()
        # Tras sanitize el nombre es uuid.ext; usar extension detectada.
        from ..media_security import normalize_extension

        ext = normalize_extension(archivo.name)
        if ext == ".docx":
            tipo_archivo = TipoPlantillaDocumento.DOCX
        elif ext == ".xlsx":
            tipo_archivo = TipoPlantillaDocumento.XLSX
        elif ext == ".pdf":
            tipo_archivo = TipoPlantillaDocumento.PDF
        else:
            raise forms.ValidationError("Formato no permitido. Usa .docx, .xlsx o .pdf.")

        try:
            campos = document_engine.detectar_campos(archivo, tipo_archivo)
        except document_engine.DocumentEngineError as exc:
            raise forms.ValidationError(str(exc))

        self.instance.tipo_archivo = tipo_archivo
        self.instance.campos = campos
        return archivo



# =========== OrdenCompra views =============
def _validar_pdf_upload(archivo):
    from ..media_security import validate_pdf_upload

    return validate_pdf_upload(archivo)



def _sync_iva_porcentaje(form, cleaned_data):
    from decimal import Decimal

    opcion = cleaned_data.get("iva_opcion")
    if opcion == IvaOpcion.OCHO:
        cleaned_data["iva_porcentaje"] = Decimal("8")
    elif opcion == IvaOpcion.DIECISEIS:
        cleaned_data["iva_porcentaje"] = Decimal("16")
    elif opcion == IvaOpcion.OTRO and cleaned_data.get("iva_porcentaje") is None:
        form.add_error("iva_porcentaje", "Indica el porcentaje de IVA.")
    return cleaned_data



class OrdenCompraCrearForm(forms.ModelForm):
    class Meta:
        model = OrdenCompra
        fields = [
            "folio_orden",
            "fecha",
            "proveedor",
            "tipo_moneda",
            "iva_opcion",
            "iva_porcentaje",
            "comentarios",
            "estado",
            "notas",
            "plantilla",
        ]
        labels = {
            "folio_orden": "Folio / orden",
            "fecha": "Fecha",
            "proveedor": "Proveedor",
            "tipo_moneda": "Tipo de moneda",
            "iva_opcion": "IVA",
            "iva_porcentaje": "Porcentaje IVA",
            "comentarios": "Comentarios",
            "estado": "Estado",
            "notas": "Notas",
            "plantilla": "Plantilla PDF",
        }
        widgets = {
            "folio_orden": forms.TextInput(attrs={"class": "form-control"}),
            "fecha": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "proveedor": forms.Select(attrs={"class": "form-select"}),
            "comentarios": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
            "notas": forms.Textarea(attrs={"rows": 2, "class": "form-control"}),
            "estado": forms.Select(attrs={"class": "form-select"}),
            "plantilla": forms.Select(attrs={"class": "form-select"}),
            "iva_porcentaje": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0"}),
            "iva_opcion": forms.RadioSelect,
            "tipo_moneda": forms.RadioSelect,
        }

    def __init__(self, *args, restrict_estado=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.restrict_estado = restrict_estado
        self.fields["folio_orden"].required = False
        self.fields["folio_orden"].help_text = "Dejalo vacio para generar uno automatico (OC-000001)."
        self.fields["proveedor"].queryset = Proveedor.objects.filter(activo=True).order_by("nombre_proveedor")
        self.fields["proveedor"].required = True
        self.fields["plantilla"].queryset = PlantillaDocumento.objects.filter(activo=True).order_by("nombre")
        self.fields["plantilla"].required = False
        self.fields["plantilla"].empty_label = "Plantilla por defecto"
        self.fields["iva_porcentaje"].required = False
        if restrict_estado:
            self.fields["estado"].disabled = True
            self.fields["estado"].help_text = "Solo IT puede marcar la orden como Terminada."
            if not (self.instance and self.instance.pk):
                self.fields["estado"].initial = EstadoOrdenCompra.BORRADOR

    def clean(self):
        cleaned = super().clean()
        cleaned = _sync_iva_porcentaje(self, cleaned)
        if self.restrict_estado:
            if self.instance and self.instance.pk:
                cleaned["estado"] = self.instance.estado
            else:
                cleaned["estado"] = EstadoOrdenCompra.BORRADOR
        return cleaned



class OrdenCompraSubirForm(forms.ModelForm):
    class Meta:
        model = OrdenCompra
        fields = ["folio_orden", "archivo_pdf", "estado", "notas"]
        labels = {
            "folio_orden": "Folio / orden",
            "archivo_pdf": "Archivo PDF",
            "estado": "Estado",
            "notas": "Notas",
        }
        widgets = {
            "notas": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, restrict_estado=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.restrict_estado = restrict_estado
        self.fields["folio_orden"].required = False
        self.fields["folio_orden"].help_text = "Dejalo vacio para generar uno automatico (OC-000001)."
        tiene_pdf = bool(
            self.instance and self.instance.pk and getattr(self.instance, "archivo_pdf", None)
        )
        self.fields["archivo_pdf"].required = not tiene_pdf
        if tiene_pdf:
            self.fields["archivo_pdf"].help_text = (
                "Opcional: deja vacio para conservar el PDF actual."
            )
        if restrict_estado:
            self.fields["estado"].disabled = True
            self.fields["estado"].help_text = "Solo IT puede marcar la orden como Terminada."
            if not (self.instance and self.instance.pk):
                self.fields["estado"].initial = EstadoOrdenCompra.BORRADOR

    def clean(self):
        cleaned = super().clean()
        if self.restrict_estado:
            if self.instance and self.instance.pk:
                cleaned["estado"] = self.instance.estado
            else:
                cleaned["estado"] = EstadoOrdenCompra.BORRADOR
        return cleaned

    def clean_archivo_pdf(self):
        archivo = self.cleaned_data.get("archivo_pdf")
        if not archivo:
            return archivo
        return _validar_pdf_upload(archivo)



class DetalleOrdenCompraForm(forms.ModelForm):
    class Meta:
        model = DetalleOrdenCompra
        fields = ["id_producto", "descripcion", "cantidad", "precio_unitario"]
        labels = {
            "id_producto": "ID producto",
            "descripcion": "Descripcion",
            "cantidad": "Cantidad",
            "precio_unitario": "P.U. / unit price",
        }
        widgets = {
            "id_producto": forms.TextInput(attrs={"class": "form-control form-control-sm"}),
            "descripcion": forms.TextInput(attrs={"class": "form-control form-control-sm"}),
            "cantidad": forms.NumberInput(attrs={"class": "form-control form-control-sm", "step": "0.01", "min": "0"}),
            "precio_unitario": forms.NumberInput(attrs={"class": "form-control form-control-sm", "step": "0.01", "min": "0"}),
        }



DetalleOrdenCompraFormSet = forms.inlineformset_factory(
    OrdenCompra,
    DetalleOrdenCompra,
    form=DetalleOrdenCompraForm,
    extra=1,
    can_delete=True,
    min_num=1,
    validate_min=True,
)



class DetalleOrdenCompraCapturaForm(forms.ModelForm):
    """Lineas minimas para OC subidas al marcar Terminado."""

    class Meta:
        model = DetalleOrdenCompra
        fields = ["descripcion", "cantidad", "id_producto", "precio_unitario"]
        labels = {
            "descripcion": "Descripcion / producto",
            "cantidad": "Cantidad",
            "id_producto": "ID producto (opcional)",
            "precio_unitario": "P.U. (opcional)",
        }
        widgets = {
            "descripcion": forms.TextInput(attrs={"class": "form-control form-control-sm"}),
            "cantidad": forms.NumberInput(
                attrs={"class": "form-control form-control-sm", "step": "1", "min": "1"}
            ),
            "id_producto": forms.TextInput(attrs={"class": "form-control form-control-sm"}),
            "precio_unitario": forms.NumberInput(
                attrs={"class": "form-control form-control-sm", "step": "0.01", "min": "0"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["descripcion"].required = True
        self.fields["cantidad"].required = True
        self.fields["id_producto"].required = False
        self.fields["precio_unitario"].required = False
        self.fields["precio_unitario"].initial = 0



DetalleOrdenCompraCapturaFormSet = forms.inlineformset_factory(
    OrdenCompra,
    DetalleOrdenCompra,
    form=DetalleOrdenCompraCapturaForm,
    extra=2,
    can_delete=True,
    min_num=1,
    validate_min=True,
)

