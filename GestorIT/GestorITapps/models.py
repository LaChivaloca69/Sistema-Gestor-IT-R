from django.db import models
from django.utils import timezone

# =====================================
# 1) USUARIOS
# =====================================

class AppUser(models.Model):
    """Custom user model for the IT Inventory system"""
    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(max_length=254, unique=True)
    password_hash = models.CharField(max_length=128)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'app_user'
        ordering = ['username']

    def __str__(self):
        return self.username


# =====================================
# 2) UBICACIONES (Jerarquía)
# =====================================

class Site(models.Model):
    """Physical site/location (company headquarters, branch office, etc.)"""
    code = models.CharField(max_length=30, unique=True)
    name = models.CharField(max_length=120)
    address = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'site'
        ordering = ['code']

    def __str__(self):
        return f"{self.code} - {self.name}"


class Building(models.Model):
    """Building within a site"""
    site = models.ForeignKey(Site, on_delete=models.PROTECT, related_name='buildings')
    code = models.CharField(max_length=30)
    name = models.CharField(max_length=120)

    class Meta:
        db_table = 'building'
        unique_together = [['site', 'code']]
        ordering = ['site', 'code']

    def __str__(self):
        return f"{self.site.code} - {self.code}"


class Zone(models.Model):
    """Zone/area within a building (floor, department, etc.)"""
    building = models.ForeignKey(Building, on_delete=models.PROTECT, related_name='zones')
    code = models.CharField(max_length=30)
    name = models.CharField(max_length=120)
    floor = models.CharField(max_length=30, blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'zone'
        unique_together = [['building', 'code']]
        ordering = ['building', 'code']

    def __str__(self):
        return f"{self.building.site.code} - {self.building.code} - {self.code}"


# =====================================
# 3) EMPLEADOS
# =====================================

class Employee(models.Model):
    """Employee/user profile"""
    user = models.OneToOneField(AppUser, on_delete=models.PROTECT, unique=True)
    employee_code = models.CharField(max_length=50, blank=True, null=True)
    first_name = models.CharField(max_length=120)
    last_name = models.CharField(max_length=120)
    phone = models.CharField(max_length=50, blank=True, null=True)
    department = models.CharField(max_length=120, blank=True, null=True)
    job_title = models.CharField(max_length=120, blank=True, null=True)

    base_site = models.ForeignKey(Site, on_delete=models.PROTECT, related_name='employees_site', blank=True, null=True)
    base_building = models.ForeignKey(Building, on_delete=models.PROTECT, related_name='employees_building', blank=True, null=True)
    base_zone = models.ForeignKey(Zone, on_delete=models.PROTECT, related_name='employees_zone', blank=True, null=True)

    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'employee'
        ordering = ['first_name', 'last_name']

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    def clean(self):
        """Validate hierarchical location constraints"""
        from django.core.exceptions import ValidationError
        if self.base_zone and not self.base_building:
            raise ValidationError("base_building must be set if base_zone is set.")
        if self.base_building and not self.base_site:
            raise ValidationError("base_site must be set if base_building is set.")


# =====================================
# 4) CATÁLOGO DE ACTIVOS
# =====================================

class AssetCategory(models.Model):
    """Asset category (Computer, Printer, Monitor, etc.)"""
    name = models.CharField(max_length=80, unique=True)
    assignable = models.BooleanField(default=True, help_text="Can this category be assigned to employees?")
    requires_serial = models.BooleanField(default=False)

    class Meta:
        db_table = 'asset_category'
        ordering = ['name']
        verbose_name_plural = 'Asset Categories'

    def __str__(self):
        return self.name


class Manufacturer(models.Model):
    """Asset manufacturer (Dell, HP, Canon, etc.)"""
    name = models.CharField(max_length=120, unique=True)

    class Meta:
        db_table = 'manufacturer'
        ordering = ['name']

    def __str__(self):
        return self.name


class AssetModel(models.Model):
    """Asset model (Dell OptiPlex 7090, HP LaserJet Pro M404, etc.)"""
    category = models.ForeignKey(AssetCategory, on_delete=models.PROTECT, related_name='models')
    manufacturer = models.ForeignKey(Manufacturer, on_delete=models.PROTECT, related_name='models')
    model_name = models.CharField(max_length=120)
    default_maintenance_interval_days = models.IntegerField(blank=True, null=True, help_text="Default maintenance interval in days")
    notes = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'asset_model'
        unique_together = [['category', 'manufacturer', 'model_name']]
        ordering = ['manufacturer', 'model_name']

    def __str__(self):
        return f"{self.manufacturer.name} {self.model_name}"


# =====================================
# 5) PROVEEDORES
# =====================================

class Vendor(models.Model):
    """Vendor/supplier for maintenance, repairs, or rentals"""
    name = models.CharField(max_length=120, unique=True)
    contact_name = models.CharField(max_length=120, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=50, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'vendor'
        ordering = ['name']

    def __str__(self):
        return self.name


# =====================================
# 6) INVENTARIO (ACTIVOS)
# =====================================

class Asset(models.Model):
    """Individual asset/equipment"""
    ASSET_STATUS_CHOICES = [
        ('IN_STOCK', 'In Stock'),
        ('ASSIGNED', 'Assigned'),
        ('IN_REPAIR', 'In Repair'),
        ('RETIRED', 'Retired'),
        ('LOST', 'Lost'),
    ]
    
    OWNERSHIP_CHOICES = [
        ('OWNED', 'Owned'),
        ('RENTED', 'Rented'),
        ('VENDOR_OWNED', 'Vendor Owned'),
    ]

    category = models.ForeignKey(AssetCategory, on_delete=models.PROTECT, related_name='assets')
    model = models.ForeignKey(AssetModel, on_delete=models.PROTECT, related_name='assets')

    asset_tag = models.CharField(max_length=60, unique=True, blank=True, null=True, help_text="Physical asset tag")
    serial_number = models.CharField(max_length=120, unique=True, blank=True, null=True)

    status = models.CharField(max_length=20, choices=ASSET_STATUS_CHOICES, default='IN_STOCK')
    ownership = models.CharField(max_length=20, choices=OWNERSHIP_CHOICES, default='OWNED')
    vendor = models.ForeignKey(Vendor, on_delete=models.PROTECT, blank=True, null=True, related_name='assets')

    purchase_date = models.DateField(blank=True, null=True)
    warranty_end = models.DateField(blank=True, null=True)

    current_site = models.ForeignKey(Site, on_delete=models.PROTECT, related_name='assets_site', blank=True, null=True)
    current_building = models.ForeignKey(Building, on_delete=models.PROTECT, related_name='assets_building', blank=True, null=True)
    current_zone = models.ForeignKey(Zone, on_delete=models.PROTECT, related_name='assets_zone', blank=True, null=True)

    notes = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'asset'
        ordering = ['asset_tag']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['model']),
        ]

    def __str__(self):
        return f"{self.category.name} - {self.asset_tag or self.serial_number or f'ID:{self.id}'}"

    def clean(self):
        """Validate asset constraints"""
        from django.core.exceptions import ValidationError
        
        # Validate hierarchical location constraints
        if self.current_building and not self.current_site:
            raise ValidationError("current_site must be set if current_building is set.")
        if self.current_zone and not self.current_building:
            raise ValidationError("current_building must be set if current_zone is set.")
        
        # Validate vendor requirement for non-owned assets
        if self.ownership != 'OWNED' and not self.vendor:
            raise ValidationError(f"Vendor is required for ownership type '{self.ownership}'.")
        
        # Validate asset_tag for assignable categories
        if self.category.assignable and not self.asset_tag:
            raise ValidationError(f"asset_tag is required for assignable category '{self.category.name}'.")


class AssetSpecification(models.Model):
    """Flexible key-value specifications for assets (RAM, CPU, IP address, etc.)"""
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, related_name='specifications')
    spec_key = models.CharField(max_length=80)
    spec_value = models.CharField(max_length=255)

    class Meta:
        db_table = 'asset_specification'
        unique_together = [['asset', 'spec_key']]

    def __str__(self):
        return f"{self.asset} - {self.spec_key}: {self.spec_value}"


# =====================================
# 7) ASIGNACIONES
# =====================================

class AssetAssignment(models.Model):
    """Assignment of assets to employees"""
    asset = models.ForeignKey(Asset, on_delete=models.PROTECT, related_name='assignments')
    employee = models.ForeignKey(Employee, on_delete=models.PROTECT, related_name='asset_assignments')

    assigned_at = models.DateTimeField(auto_now_add=True)
    returned_at = models.DateTimeField(blank=True, null=True)

    assigned_by_user = models.ForeignKey(AppUser, on_delete=models.PROTECT, blank=True, null=True, related_name='assignments_made')

    condition_out = models.TextField(blank=True, null=True, help_text="Condition when assigned out")
    condition_in = models.TextField(blank=True, null=True, help_text="Condition when returned")

    class Meta:
        db_table = 'asset_assignment'
        ordering = ['-assigned_at']
        indexes = [
            models.Index(fields=['employee']),
        ]

    def __str__(self):
        status = "Active" if not self.returned_at else "Returned"
        return f"{self.asset} → {self.employee} ({status})"


# =====================================
# 8) MANTENIMIENTO
# =====================================

class MaintenancePlan(models.Model):
    """Maintenance plan template"""
    name = models.CharField(max_length=120)
    interval_days = models.IntegerField(help_text="Maintenance interval in days")

    applies_to_category = models.ForeignKey(AssetCategory, on_delete=models.PROTECT, blank=True, null=True, related_name='maintenance_plans_category')
    applies_to_model = models.ForeignKey(AssetModel, on_delete=models.PROTECT, blank=True, null=True, related_name='maintenance_plans_model')

    active = models.BooleanField(default=True)

    class Meta:
        db_table = 'maintenance_plan'
        ordering = ['name']

    def __str__(self):
        return self.name

    def clean(self):
        """Validate at least one scope is defined"""
        from django.core.exceptions import ValidationError
        if not self.applies_to_category and not self.applies_to_model:
            raise ValidationError("At least applies_to_category or applies_to_model must be defined.")


class MaintenanceWorkOrder(models.Model):
    """Maintenance work order for an asset"""
    MAINTENANCE_TYPE_CHOICES = [
        ('PREVENTIVE', 'Preventive'),
        ('CORRECTIVE', 'Corrective'),
    ]
    
    STATUS_CHOICES = [
        ('OPEN', 'Open'),
        ('IN_PROGRESS', 'In Progress'),
        ('DONE', 'Done'),
        ('CANCELED', 'Canceled'),
    ]

    asset = models.ForeignKey(Asset, on_delete=models.PROTECT, related_name='maintenance_orders')
    plan = models.ForeignKey(MaintenancePlan, on_delete=models.PROTECT, blank=True, null=True, related_name='work_orders')
    vendor = models.ForeignKey(Vendor, on_delete=models.PROTECT, blank=True, null=True, related_name='maintenance_work_orders')

    m_type = models.CharField(max_length=20, choices=MAINTENANCE_TYPE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='OPEN')

    opened_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    next_due_at = models.DateTimeField(blank=True, null=True)

    findings = models.TextField(blank=True, null=True)
    actions_taken = models.TextField(blank=True, null=True)
    cost = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)

    class Meta:
        db_table = 'maintenance_work_order'
        ordering = ['-opened_at']
        indexes = [
            models.Index(fields=['asset', 'status']),
        ]

    def __str__(self):
        return f"MWO {self.id} - {self.asset} ({self.get_status_display()})"


# =====================================
# 9) TICKETS IT
# =====================================

class TicketCategory(models.Model):
    """Ticket category (Hardware Issue, Software Support, etc.)"""
    name = models.CharField(max_length=80, unique=True)

    class Meta:
        db_table = 'ticket_category'
        ordering = ['name']
        verbose_name_plural = 'Ticket Categories'

    def __str__(self):
        return self.name


class Ticket(models.Model):
    """Support ticket"""
    PRIORITY_CHOICES = [
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
        ('URGENT', 'Urgent'),
    ]
    
    STATUS_CHOICES = [
        ('OPEN', 'Open'),
        ('IN_PROGRESS', 'In Progress'),
        ('WAITING_VENDOR', 'Waiting Vendor'),
        ('RESOLVED', 'Resolved'),
        ('CLOSED', 'Closed'),
    ]

    requester_employee = models.ForeignKey(Employee, on_delete=models.PROTECT, related_name='tickets_created')
    assigned_to_employee = models.ForeignKey(Employee, on_delete=models.PROTECT, blank=True, null=True, related_name='tickets_assigned')

    site = models.ForeignKey(Site, on_delete=models.PROTECT, blank=True, null=True, related_name='tickets')
    building = models.ForeignKey(Building, on_delete=models.PROTECT, blank=True, null=True, related_name='tickets')
    zone = models.ForeignKey(Zone, on_delete=models.PROTECT, blank=True, null=True, related_name='tickets')

    asset = models.ForeignKey(Asset, on_delete=models.PROTECT, blank=True, null=True, related_name='tickets')

    category = models.ForeignKey(TicketCategory, on_delete=models.PROTECT, related_name='tickets')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='MEDIUM')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='OPEN')

    subject = models.CharField(max_length=200)
    description = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = 'ticket'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'priority']),
            models.Index(fields=['requester_employee']),
            models.Index(fields=['asset']),
        ]

    def __str__(self):
        return f"TKT#{self.id} - {self.subject}"


class TicketComment(models.Model):
    """Comment on a ticket"""
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='comments')
    author_employee = models.ForeignKey(Employee, on_delete=models.PROTECT)
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ticket_comment'
        ordering = ['created_at']

    def __str__(self):
        return f"Comment on TKT#{self.ticket.id} by {self.author_employee}"


# =====================================
# 10) HISTORIAL DE ACTIVOS
# =====================================

class AssetEvent(models.Model):
    """Asset movement/event history"""
    EVENT_TYPE_CHOICES = [
        ('ASSIGNED', 'Assigned'),
        ('RETURNED', 'Returned'),
        ('MOVED_LOCATION', 'Moved Location'),
        ('MAINTENANCE_CREATED', 'Maintenance Created'),
        ('MAINTENANCE_DONE', 'Maintenance Done'),
        ('STATUS_CHANGED', 'Status Changed'),
        ('OTHER', 'Other'),
    ]

    asset = models.ForeignKey(Asset, on_delete=models.PROTECT, related_name='events')
    event_type = models.CharField(max_length=30, choices=EVENT_TYPE_CHOICES)

    from_employee = models.ForeignKey(Employee, on_delete=models.PROTECT, blank=True, null=True, related_name='asset_events_from')
    to_employee = models.ForeignKey(Employee, on_delete=models.PROTECT, blank=True, null=True, related_name='asset_events_to')

    from_zone = models.ForeignKey(Zone, on_delete=models.PROTECT, blank=True, null=True, related_name='asset_events_from_zone')
    to_zone = models.ForeignKey(Zone, on_delete=models.PROTECT, blank=True, null=True, related_name='asset_events_to_zone')

    related_assignment = models.ForeignKey(AssetAssignment, on_delete=models.SET_NULL, blank=True, null=True, related_name='events')
    related_mwo = models.ForeignKey(MaintenanceWorkOrder, on_delete=models.SET_NULL, blank=True, null=True, related_name='events')

    occurred_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, null=True)
    created_by_user = models.ForeignKey(AppUser, on_delete=models.PROTECT, related_name='asset_events_created')

    class Meta:
        db_table = 'asset_event'
        ordering = ['-occurred_at']
        indexes = [
            models.Index(fields=['asset', 'occurred_at']),
        ]

    def __str__(self):
        return f"{self.asset} - {self.get_event_type_display()} ({self.occurred_at})"
