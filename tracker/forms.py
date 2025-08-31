from django import forms
from django.contrib.auth.models import User, Group
from .models import Customer, Order, Vehicle, InventoryItem

class CustomerEditForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = [
            "full_name","phone","email","address","notes",
            "customer_type","organization_name","tax_number","personal_subtype","current_status",
        ]
    def clean(self):
        cleaned = super().clean()
        t = cleaned.get("customer_type")
        if t in {"government","ngo","company"}:
            if not cleaned.get("organization_name"):
                self.add_error("organization_name","Required for organizational customers")
            if not cleaned.get("tax_number"):
                self.add_error("tax_number","Required for organizational customers")
        return cleaned

class CustomerStep1Form(forms.Form):
    full_name = forms.CharField(max_length=255)
    phone = forms.CharField(max_length=20)
    email = forms.EmailField(required=False)
    address = forms.CharField(widget=forms.Textarea, required=False)
    notes = forms.CharField(widget=forms.Textarea, required=False)

class CustomerStep2Form(forms.Form):
    intent = forms.ChoiceField(choices=[("service", "I need a service"), ("inquiry", "Just an inquiry")])

class CustomerStep3Form(forms.Form):
    service_type = forms.ChoiceField(choices=[("tire", "Tire Sales"), ("car_service", "Car Service")])

class CustomerStep4Form(forms.Form):
    customer_type = forms.ChoiceField(choices=Customer.TYPE_CHOICES)
    organization_name = forms.CharField(required=False)
    tax_number = forms.CharField(required=False)
    personal_subtype = forms.ChoiceField(choices=Customer.PERSONAL_SUBTYPE, required=False)

class VehicleForm(forms.ModelForm):
    class Meta:
        model = Vehicle
        fields = ["plate_number", "make", "model", "vehicle_type"]

class OrderForm(forms.ModelForm):
    SERVICE_OPTIONS = [
        ("oil_change", "Oil Change"),
        ("engine_diagnostics", "Engine Diagnostics"),
        ("brake_repair", "Brake Repair"),
        ("tire_rotation", "Tire Rotation"),
        ("wheel_alignment", "Wheel Alignment"),
        ("battery_check", "Battery Check"),
        ("fluid_top_up", "Fluid Top-Up"),
    ]

    service_selection = forms.MultipleChoiceField(
        choices=SERVICE_OPTIONS, required=False, widget=forms.CheckboxSelectMultiple
    )

    class Meta:
        model = Order
        fields = [
            "type",
            "vehicle",
            "priority",
            "description",
            "estimated_duration",
            "item_name",
            "brand",
            "quantity",
            "tire_type",
            "inquiry_type",
            "questions",
            "contact_preference",
            "follow_up_date",
        ]
        widgets = {
            "follow_up_date": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["item_name"].widget = forms.Select(choices=[
            ("All-Season", "All-Season"),
            ("Summer", "Summer"),
            ("Winter", "Winter"),
            ("Performance", "Performance"),
            ("Off-Road", "Off-Road"),
            ("Eco", "Eco"),
            ("Run-Flat", "Run-Flat"),
        ])
        self.fields["brand"].widget = forms.Select(choices=[
            ("Michelin", "Michelin"),
            ("Bridgestone", "Bridgestone"),
            ("Continental", "Continental"),
            ("Pirelli", "Pirelli"),
            ("Goodyear", "Goodyear"),
        ])
        self.fields["tire_type"].widget = forms.Select(choices=[
            ("New", "New"), ("Used", "Used"), ("Refurbished", "Refurbished")
        ])
        self.fields["inquiry_type"].widget = forms.Select(choices=[
            ("Pricing", "Pricing"), ("Services", "Services"), ("Appointment Booking", "Appointment Booking"), ("General", "General")
        ])
        self.fields["contact_preference"].widget = forms.Select(choices=[
            ("phone", "Phone"), ("email", "Email")
        ])

    def clean(self):
        cleaned = super().clean()
        t = cleaned.get("type")
        if t == "sales":
            for f in ["item_name", "brand"]:
                if not cleaned.get(f):
                    self.add_error(f, "Required for Sales orders")
            q = cleaned.get("quantity")
            if not q or q < 1:
                self.add_error("quantity", "Quantity must be at least 1")
        elif t == "service":
            if not cleaned.get("description"):
                self.add_error("description", "Problem description required for Service orders")
            if not cleaned.get("estimated_duration"):
                self.add_error("estimated_duration", "Estimated duration required for Service orders")
            services = cleaned.get("service_selection") or []
            if services:
                desc = cleaned.get("description") or ""
                desc_services = "\nSelected services: " + ", ".join(dict(self.SERVICE_OPTIONS)[s] for s in services)
                cleaned["description"] = (desc + desc_services).strip()
        elif t == "consultation":
            if not cleaned.get("inquiry_type"):
                self.add_error("inquiry_type", "Inquiry type is required")
            if not cleaned.get("questions"):
                self.add_error("questions", "Please provide your questions")
        return cleaned

class InventoryItemForm(forms.ModelForm):
    class Meta:
        model = InventoryItem
        fields = ["name", "brand", "quantity", "price"]

class AdminUserForm(forms.ModelForm):
    group_manager = forms.BooleanField(required=False, label="Manager role")

    class Meta:
        model = User
        fields = ["first_name", "last_name", "email", "is_active", "is_staff"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        mgr, _ = Group.objects.get_or_create(name="manager")
        self.fields["group_manager"].initial = mgr in self.instance.groups.all()

    def save(self, commit=True):
        user = super().save(commit)
        mgr, _ = Group.objects.get_or_create(name="manager")
        if self.cleaned_data.get("group_manager"):
            user.groups.add(mgr)
        else:
            user.groups.remove(mgr)
        if commit:
            user.save()
        return user
