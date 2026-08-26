"""Consumibles: stock por cantidad (productos + kardex)."""
from decimal import Decimal

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .. import historial
from ..forms.consumibles import MovimientoStockForm, ProductoConsumibleForm
from ..models import (
    AccionHistorial,
    CategoriaEquipo,
    ModuloHistorial,
    MovimientoStock,
    NivelHistorial,
    ProductoConsumible,
    TipoCategoriaInventario,
    TipoMovimientoStock,
)


def _categorias_consumible():
    return CategoriaEquipo.objects.filter(
        tipo=TipoCategoriaInventario.CONSUMIBLE
    ).order_by("nombre_categoria")


def _producto_queryset():
    return ProductoConsumible.objects.select_related(
        "categoria", "ubicacion", "ubicacion__edificio", "proveedor"
    )


def _get_responsable_from_user(user):
    if not user or not getattr(user, "is_authenticated", False):
        return None
    try:
        return user.personal_profile
    except Exception:
        return None


def _productos_bajo_stock_q():
    return Q(stock_actual__lte=0) | (
        Q(stock_minimo__gt=0) & Q(stock_actual__lte=F("stock_minimo"))
    )


def _aplicar_movimiento_stock(
    producto,
    tipo_movimiento,
    cantidad,
    motivo=None,
    responsable=None,
    orden_compra=None,
    request=None,
):
    """Aplica entrada/salida/ajuste y deja rastro en kardex + historial."""
    cantidad = Decimal(cantidad)
    with transaction.atomic():
        producto = ProductoConsumible.objects.select_for_update().get(pk=producto.pk)
        antes = producto.stock_actual or Decimal("0")

        if tipo_movimiento == TipoMovimientoStock.ENTRADA:
            despues = antes + cantidad
            qty_registrada = cantidad
        elif tipo_movimiento == TipoMovimientoStock.SALIDA:
            if cantidad > antes:
                raise ValidationError(f"Stock insuficiente (disponible: {antes}).")
            despues = antes - cantidad
            qty_registrada = cantidad
        elif tipo_movimiento == TipoMovimientoStock.AJUSTE:
            despues = cantidad
            if despues < 0:
                raise ValidationError("El stock resultante no puede ser negativo.")
            qty_registrada = abs(despues - antes)
        else:
            raise ValidationError("Tipo de movimiento no valido.")

        producto.stock_actual = despues
        producto.save(update_fields=["stock_actual", "fecha_actualizacion"])

        movimiento = MovimientoStock.objects.create(
            producto=producto,
            tipo_movimiento=tipo_movimiento,
            cantidad=qty_registrada,
            stock_antes=antes,
            stock_despues=despues,
            motivo=motivo or None,
            responsable=responsable,
            orden_compra=orden_compra,
        )

        historial.registrar_historial(
            request=request,
            modulo=ModuloHistorial.CONSUMIBLE,
            accion=AccionHistorial.OTRO,
            titulo=f"{tipo_movimiento}: {producto.sku} ({antes} → {despues})",
            descripcion=motivo or "",
            objeto=movimiento,
            objeto_etiqueta=str(producto),
            entidad_relacionada=producto,
            enlace_nombre="producto_consumible_detail",
            enlace_pk=producto.pk,
            es_automatico=False,
            nivel=NivelHistorial.INFO,
            metadata={
                "tipo": tipo_movimiento,
                "cantidad": str(qty_registrada),
                "stock_antes": str(antes),
                "stock_despues": str(despues),
            },
        )
    return movimiento


def producto_consumible_list(request):
    items = _producto_queryset().order_by("nombre", "sku")
    search_query = (request.GET.get("q") or "").strip()
    selected_categoria = request.GET.get("categoria", "")
    selected_activo = request.GET.get("activo", "true")
    selected_alerta = (request.GET.get("alerta") or "").strip()

    if search_query:
        items = items.filter(
            Q(sku__icontains=search_query)
            | Q(nombre__icontains=search_query)
            | Q(descripcion__icontains=search_query)
        )
    if selected_categoria:
        items = items.filter(categoria_id=selected_categoria)
    if selected_activo == "true":
        items = items.filter(activo=True)
    elif selected_activo == "false":
        items = items.filter(activo=False)
    if selected_alerta == "bajo":
        items = items.filter(_productos_bajo_stock_q())

    bajo_reales = ProductoConsumible.objects.filter(activo=True).filter(
        _productos_bajo_stock_q()
    ).count()

    return render(
        request,
        "consumible/list.html",
        {
            "items": items,
            "search_query": search_query,
            "selected_categoria": selected_categoria,
            "selected_activo": selected_activo,
            "selected_alerta": selected_alerta,
            "categoria_choices": _categorias_consumible().values_list(
                "id", "nombre_categoria"
            ),
            "bajo_count": bajo_reales,
        },
    )


def producto_consumible_detail(request, pk):
    producto = get_object_or_404(_producto_queryset(), pk=pk)
    movimientos = (
        MovimientoStock.objects.select_related("responsable", "orden_compra")
        .filter(producto=producto)
        .order_by("-fecha_movimiento", "-pk")[:40]
    )
    return render(
        request,
        "consumible/detail.html",
        {
            "object": producto,
            "movimientos": movimientos,
        },
    )


def producto_consumible_create(request):
    if request.method == "POST":
        form = ProductoConsumibleForm(request.POST)
        if form.is_valid():
            producto = form.save(commit=False)
            producto.stock_actual = Decimal("0")
            producto.save()
            historial.registrar_creacion(
                request,
                modulo=ModuloHistorial.CONSUMIBLE,
                titulo=f"Producto consumible: {producto.sku}",
                objeto=producto,
                enlace_nombre="producto_consumible_detail",
            )
            messages.success(
                request,
                "Producto creado. Registra una entrada para cargar stock inicial.",
            )
            return redirect("producto_consumible_movimiento", pk=producto.pk, tipo="entrada")
    else:
        form = ProductoConsumibleForm()
    return render(
        request,
        "consumible/form.html",
        {"form": form},
    )


def producto_consumible_update(request, pk):
    producto = get_object_or_404(_producto_queryset(), pk=pk)
    if request.method == "POST":
        form = ProductoConsumibleForm(request.POST, instance=producto)
        if form.is_valid():
            producto = form.save()
            historial.registrar_actualizacion(
                request,
                modulo=ModuloHistorial.CONSUMIBLE,
                titulo=f"Producto actualizado: {producto.sku}",
                objeto=producto,
                form=form,
                enlace_nombre="producto_consumible_detail",
            )
            messages.success(request, "Producto actualizado.")
            return redirect("producto_consumible_detail", pk=producto.pk)
    else:
        form = ProductoConsumibleForm(instance=producto)
    return render(
        request,
        "consumible/form.html",
        {"form": form, "object": producto},
    )


def producto_consumible_delete(request, pk):
    producto = get_object_or_404(_producto_queryset(), pk=pk)
    if request.method == "POST":
        sku = producto.sku
        historial.registrar_eliminacion(
            request,
            modulo=ModuloHistorial.CONSUMIBLE,
            titulo=f"Producto eliminado: {sku}",
            objeto=producto,
            metadata={"sku": sku},
            nivel=NivelHistorial.CRITICO,
        )
        producto.delete()
        messages.success(request, "Producto eliminado.")
        return redirect("producto_consumible_list")
    return render(
        request,
        "consumible/confirm_delete.html",
        {"object": producto},
    )


def producto_consumible_movimiento(request, pk, tipo=None):
    producto = get_object_or_404(_producto_queryset(), pk=pk)
    tipo_map = {
        "entrada": TipoMovimientoStock.ENTRADA,
        "salida": TipoMovimientoStock.SALIDA,
        "ajuste": TipoMovimientoStock.AJUSTE,
    }
    tipo_fijo = tipo_map.get((tipo or "").lower())
    if tipo and not tipo_fijo:
        messages.error(request, "Tipo de movimiento no valido.")
        return redirect("producto_consumible_detail", pk=pk)

    if request.method == "POST":
        form = MovimientoStockForm(request.POST, producto=producto, tipo_fijo=tipo_fijo)
        if form.is_valid():
            tipo_mov = form.cleaned_data["tipo_movimiento"]
            try:
                _aplicar_movimiento_stock(
                    producto,
                    tipo_mov,
                    form.cleaned_data["cantidad"],
                    motivo=form.cleaned_data.get("motivo"),
                    responsable=form.cleaned_data.get("responsable")
                    or _get_responsable_from_user(request.user),
                    orden_compra=form.cleaned_data.get("orden_compra"),
                    request=request,
                )
            except ValidationError as exc:
                messages.error(
                    request,
                    "; ".join(exc.messages) if hasattr(exc, "messages") else str(exc),
                )
            else:
                messages.success(request, f"{tipo_mov} registrada correctamente.")
                return redirect("producto_consumible_detail", pk=pk)
    else:
        form = MovimientoStockForm(producto=producto, tipo_fijo=tipo_fijo)
        resp = _get_responsable_from_user(request.user)
        if resp:
            form.fields["responsable"].initial = resp.pk

    titulo = {
        TipoMovimientoStock.ENTRADA: "Entrada de stock",
        TipoMovimientoStock.SALIDA: "Salida de stock",
        TipoMovimientoStock.AJUSTE: "Ajuste de stock",
    }.get(tipo_fijo, "Movimiento de stock")

    return render(
        request,
        "consumible/movimiento_form.html",
        {
            "object": producto,
            "form": form,
            "titulo": titulo,
            "tipo_fijo": tipo_fijo,
        },
    )


def movimiento_stock_list(request):
    items = MovimientoStock.objects.select_related(
        "producto", "producto__categoria", "responsable", "orden_compra"
    ).order_by("-fecha_movimiento", "-pk")
    selected_tipo = request.GET.get("tipo", "")
    selected_producto = request.GET.get("producto", "")
    search_query = (request.GET.get("q") or "").strip()

    if selected_tipo:
        items = items.filter(tipo_movimiento=selected_tipo)
    if selected_producto:
        items = items.filter(producto_id=selected_producto)
    if search_query:
        items = items.filter(
            Q(producto__sku__icontains=search_query)
            | Q(producto__nombre__icontains=search_query)
            | Q(motivo__icontains=search_query)
        )

    return render(
        request,
        "consumible/movimientos_list.html",
        {
            "items": items[:200],
            "selected_tipo": selected_tipo,
            "selected_producto": selected_producto,
            "search_query": search_query,
            "tipo_choices": TipoMovimientoStock.choices,
            "producto_choices": [
                (p.pk, f"{p.sku} — {p.nombre}")
                for p in ProductoConsumible.objects.order_by("nombre")[:300]
            ],
        },
    )


def consumible_dashboard(request):
    qs = _producto_queryset().filter(activo=True)
    bajo = list(qs.filter(_productos_bajo_stock_q()).order_by("stock_actual", "nombre")[:20])
    total = qs.count()
    valor = Decimal("0")
    for p in qs.only("stock_actual", "costo_aproximado"):
        valor += (p.stock_actual or Decimal("0")) * (p.costo_aproximado or Decimal("0"))
    recientes = (
        MovimientoStock.objects.select_related("producto", "responsable")
        .order_by("-fecha_movimiento")[:12]
    )
    return render(
        request,
        "consumible/dashboard.html",
        {
            "total": total,
            "bajo": bajo,
            "bajo_count": ProductoConsumible.objects.filter(activo=True)
            .filter(_productos_bajo_stock_q())
            .count(),
            "valor_estimado": valor,
            "recientes": recientes,
            "today": timezone.localdate(),
        },
    )


def _consumibles_alerta_context():
    qs = ProductoConsumible.objects.filter(activo=True).filter(_productos_bajo_stock_q())
    return {
        "consumibles_bajo_count": qs.count(),
        "consumibles_bajo": list(qs.order_by("stock_actual", "nombre")[:8]),
    }
