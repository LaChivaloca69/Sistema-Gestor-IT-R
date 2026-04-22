from django.forms import modelform_factory
from django.http import Http404
from django.urls import reverse
from django.views.generic import CreateView, DeleteView, ListView, TemplateView, UpdateView
# Modelos importados para registro y mapeo dinamico en vistas genericas.
from .models import (
	AgendaMantenimiento,
	Answer,
	Area,
	AsignacionEquipo,
	Bitacora,
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

# Registro de modelos para acceso rapido en vistas genericas.
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
		Bitacora,
		Answer,
		Presupuesto,
		DetallePresupuesto,
		CompraMaterial,
		DetalleCompraMaterial,
	]
}

# Config de secciones y modelos para inicio, con orden y descripcion. 
HOME_MODEL_SECTIONS = [
	{
		"titulo": "Organizacion",
		"descripcion": "Catalogos de personal y estructura interna.",
		"slugs": ["area", "puesto", "personal"],
	},
	{
		"titulo": "Ubicaciones",
		"descripcion": "Jerarquia fisica de edificios y zonas.",
		"slugs": ["edificio", "zonaedificio", "ubicacion"],
	},
	{
		"titulo": "Inventario",
		"descripcion": "Catalogos y activos de TI.",
		"slugs": ["categoriaequipo", "equipo", "proveedor"],
	},
	{
		"titulo": "Operaciones de Activos",
		"descripcion": "Movimientos, asignaciones y mantenimientos.",
		"slugs": ["movimientoequipo", "asignacionequipo", "mantenimiento", "agendamantenimiento"],
	},
	{
		"titulo": "Soporte",
		"descripcion": "Gestion de Support, Check, Bitacora y Answer.",
		"slugs": ["ticketit", "seguimientoticket", "bitacora", "answer"],
	},
	{
		"titulo": "Gestion Economica",
		"descripcion": "Presupuestos y compras de material.",
		"slugs": ["presupuesto", "detallepresupuesto", "compramaterial", "detallecompramaterial"],
	},
]

# Manejo de error 404 para modelos no encontrados
def get_model_by_slug(model_slug):
	model = MODEL_REGISTRY.get(model_slug)
	if model is None:
		raise Http404("Modelo no encontrado")
	return model

# Views genericas para CRUD
class HomeView(TemplateView):
	template_name = "home.html"

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		all_models = {
			slug: {
				"slug": slug,
				"nombre": model._meta.verbose_name_plural.title(),
			}
			for slug, model in MODEL_REGISTRY.items()
		}

		sections = []
		used_slugs = set()

		for section in HOME_MODEL_SECTIONS:
			items = []
			for slug in section["slugs"]:
				item = all_models.get(slug)
				if item:
					items.append(item)
					used_slugs.add(slug)

			if items:
				sections.append(
					{
						"titulo": section["titulo"],
						"descripcion": section["descripcion"],
						"items": items,
					}
				)

		restantes = sorted(
			[
				item
				for slug, item in all_models.items()
				if slug not in used_slugs
			],
			key=lambda item: item["nombre"],
		)

		if restantes:
			sections.append(
				{
					"titulo": "Otros",
					"descripcion": "Modelos no clasificados en una seccion principal.",
					"items": restantes,
				}
			)

		context["model_sections"] = sections
		return context

# Mixin para compartir logica comun de manejo de modelos dinamicos en vistas genericas.
class ModelContextMixin:
	model = None

	def dispatch(self, request, *args, **kwargs):
		self.model = get_model_by_slug(kwargs["model_slug"])
		return super().dispatch(request, *args, **kwargs)

	def get_form_class(self):
		# Evita exponer IDs/autocampos en formularios dinamicos.
		form_fields = [
			field.name
			for field in self.model._meta.fields
			if field.editable and not field.primary_key and not field.auto_created
		]
		return modelform_factory(self.model, fields=form_fields)

	def get_success_url(self):
		return reverse("modelo-list", kwargs={"model_slug": self.model._meta.model_name})

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		context["model_slug"] = self.model._meta.model_name
		context["modelo_nombre"] = self.model._meta.verbose_name_plural.title()
		return context

	def get_model_template_names(self, template_filename):
		model_slug = self.model._meta.model_name
		return [f"crud/{model_slug}/{template_filename}"]

# Views Genericas para List, Create, Update y Delete, utilizando el mixin para manejo dinamico de modelos y formularios. Templates personalizados por modelo si existen, sino caen al template generico.
class ModelListView(ModelContextMixin, ListView):
	template_name = "crud/list.html"
	context_object_name = "objetos"
	paginate_by = 25

	def get_template_names(self):
		return self.get_model_template_names("list.html")

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

	def get_template_names(self):
		return self.get_model_template_names("form.html")


class ModelUpdateView(ModelContextMixin, UpdateView):
	template_name = "crud/form.html"

	def get_template_names(self):
		return self.get_model_template_names("form.html")

	def get_queryset(self):
		return self.model.objects.all()


class ModelDeleteView(ModelContextMixin, DeleteView):
	template_name = "crud/confirm_delete.html"

	def get_template_names(self):
		return self.get_model_template_names("confirm_delete.html")

	def get_queryset(self):
		return self.model.objects.all()
