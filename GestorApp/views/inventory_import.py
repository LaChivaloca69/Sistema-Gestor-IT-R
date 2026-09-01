"""Wizard de importacion masiva de inventario desde Excel."""
import uuid

from django import forms
from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import redirect, render

from ..inventory_import import (
    MAX_FILE_BYTES,
    ImportRow,
    build_import_template,
    execute_import,
    parse_import_workbook,
    summarize_rows,
)

SESSION_KEY = "inventory_import_batch"


class InventarioImportUploadForm(forms.Form):
    archivo = forms.FileField(
        label="Archivo Excel (.xlsx)",
        help_text="Use la plantilla con hojas Equipos y Perifericos.",
    )

    def clean_archivo(self):
        uploaded = self.cleaned_data["archivo"]
        name = (uploaded.name or "").lower()
        if not name.endswith(".xlsx"):
            raise forms.ValidationError("Solo se aceptan archivos .xlsx.")
        if uploaded.size > MAX_FILE_BYTES:
            raise forms.ValidationError(
                f"El archivo supera el limite de {MAX_FILE_BYTES // (1024 * 1024)} MB."
            )
        return uploaded


def _get_batch(request):
    return request.session.get(SESSION_KEY)


def _save_batch(request, rows):
    request.session[SESSION_KEY] = {
        "id": str(uuid.uuid4()),
        "rows": [row.to_session() for row in rows],
    }
    request.session.modified = True


def _clear_batch(request):
    if SESSION_KEY in request.session:
        del request.session[SESSION_KEY]
        request.session.modified = True


def _rows_from_batch(batch) -> list[ImportRow]:
    return [ImportRow.from_session(item) for item in batch.get("rows", [])]


def inventario_importar_plantilla(request):
    content = build_import_template()
    response = HttpResponse(
        content,
        content_type=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
    )
    response["Content-Disposition"] = 'attachment; filename="plantilla_inventario.xlsx"'
    return response


def inventario_importar(request):
    if request.method == "POST":
        form = InventarioImportUploadForm(request.POST, request.FILES)
        if form.is_valid():
            rows, global_errors = parse_import_workbook(form.cleaned_data["archivo"])
            if global_errors:
                for error in global_errors:
                    messages.error(request, error)
                return render(
                    request,
                    "equipo/importar.html",
                    {"form": form},
                )
            _save_batch(request, rows)
            return redirect("inventario_importar_preview")
    else:
        form = InventarioImportUploadForm()

    return render(request, "equipo/importar.html", {"form": form})


def inventario_importar_preview(request):
    batch = _get_batch(request)
    if not batch:
        messages.warning(request, "Sube un archivo Excel para continuar.")
        return redirect("inventario_importar")

    rows = _rows_from_batch(batch)
    summary = summarize_rows(rows)
    return render(
        request,
        "equipo/importar_preview.html",
        {
            "rows": rows,
            "summary": summary,
            "batch_id": batch.get("id"),
        },
    )


def inventario_importar_confirmar(request):
    if request.method != "POST":
        return redirect("inventario_importar_preview")

    batch = _get_batch(request)
    if not batch:
        messages.warning(request, "La sesion de importacion expiro. Vuelve a subir el archivo.")
        return redirect("inventario_importar")

    batch_id = request.POST.get("batch_id", "")
    if batch_id != batch.get("id"):
        messages.error(request, "La vista previa no coincide. Vuelve a subir el archivo.")
        return redirect("inventario_importar")

    rows = _rows_from_batch(batch)
    summary = summarize_rows(rows)
    if summary["importables"] == 0:
        messages.error(request, "No hay filas validas para importar.")
        return redirect("inventario_importar_preview")

    result = execute_import(rows, request=request)
    _clear_batch(request)

    if result["equipos_creados"] or result["perifericos_creados"]:
        messages.success(
            request,
            (
                f"Importacion completada: {result['equipos_creados']} equipo(s), "
                f"{result['perifericos_creados']} periferico(s)."
            ),
        )
    if result["asignaciones_creadas"]:
        messages.info(
            request,
            f"Se crearon {result['asignaciones_creadas']} asignacion(es).",
        )
    if result["filas_omitidas"]:
        messages.warning(
            request,
            f"{result['filas_omitidas']} fila(s) omitidas por errores.",
        )
    for error in result["errores_ejecucion"][:5]:
        messages.error(request, error)

    return render(
        request,
        "equipo/importar_resultado.html",
        {
            "result": result,
            "summary": summary,
            "rows": rows,
        },
    )


def inventario_importar_cancelar(request):
    _clear_batch(request)
    messages.info(request, "Importacion cancelada.")
    return redirect("equipo_dashboard")
