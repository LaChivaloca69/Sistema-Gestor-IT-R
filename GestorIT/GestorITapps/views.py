from django.forms import modelform_factory
from django.http import Http404
from django.urls import reverse
from django.views.generic import CreateView, DeleteView, ListView, TemplateView, UpdateView

from .models import (
	AgendaMantenimiento,
	Area,
	AsignacionEquipo,
	CategoriaEquipo,
	CompraMaterial,
	DetalleCompraMaterial,
	DetallePresupuesto,
	Edificio,
	Equipo,
	Mantenimiento,
	MovimientoEquipo,
	Personal,
	Presupuesto,
	Proveedor,
	Puesto,
	SeguimientoTicket,
	TicketIT,
	Ubicacion,
	ZonaEdificio,
)


MODEL_REGISTRY = {
	model._meta.model_name: model
	for model in [
		Area,
		Puesto,
		Personal,
		Proveedor,
		Edificio,
		ZonaEdificio,
		Ubicacion,
		CategoriaEquipo,
		Equipo,
		MovimientoEquipo,
		AsignacionEquipo,
		Mantenimiento,
		AgendaMantenimiento,
		TicketIT,
		SeguimientoTicket,
		Presupuesto,
		DetallePresupuesto,
		CompraMaterial,
		DetalleCompraMaterial,
	]
}


def get_model_by_slug(model_slug):
	model = MODEL_REGISTRY.get(model_slug)
	if model is None:
		raise Http404("Modelo no encontrado")
	return model


class HomeView(TemplateView):
	template_name = "home.html"

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		context["modelos"] = [
			{
				"slug": slug,
				"nombre": model._meta.verbose_name_plural.title(),
			}
			for slug, model in sorted(
				MODEL_REGISTRY.items(),
				key=lambda item: item[1]._meta.verbose_name_plural,
			)
		]
		return context


class ModelContextMixin:
	model = None

	def dispatch(self, request, *args, **kwargs):
		self.model = get_model_by_slug(kwargs["model_slug"])
		return super().dispatch(request, *args, **kwargs)

	def get_form_class(self):
		return modelform_factory(self.model, fields="__all__")

	def get_success_url(self):
		return reverse("modelo-list", kwargs={"model_slug": self.model._meta.model_name})

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		context["model_slug"] = self.model._meta.model_name
		context["modelo_nombre"] = self.model._meta.verbose_name_plural.title()
		return context


class ModelListView(ModelContextMixin, ListView):
	template_name = "crud/list.html"
	context_object_name = "objetos"
	paginate_by = 25

	def get_queryset(self):
		return self.model.objects.all().order_by("pk")

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		fields = list(self.model._meta.fields)
		context["fields"] = fields
		context["rows"] = [
			{
				"obj": obj,
				"values": [getattr(obj, field.name) for field in fields],
			}
			for obj in context["objetos"]
		]
		return context


class ModelCreateView(ModelContextMixin, CreateView):
	template_name = "crud/form.html"


class ModelUpdateView(ModelContextMixin, UpdateView):
	template_name = "crud/form.html"

	def get_queryset(self):
		return self.model.objects.all()


class ModelDeleteView(ModelContextMixin, DeleteView):
	template_name = "crud/confirm_delete.html"

	def get_queryset(self):
		return self.model.objects.all()
