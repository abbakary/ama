from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpRequest, HttpResponse
from django.db.models import Count, Avg
from django.utils import timezone
from django.contrib.auth.views import LoginView
from django.contrib import messages
from django.db.models.functions import TruncDate
import json
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User, Group
from django.core.paginator import Paginator
from .models import Customer, Order, Vehicle, InventoryItem
from .forms import (
    CustomerStep1Form,
    CustomerStep2Form,
    CustomerStep3Form,
    CustomerStep4Form,
    VehicleForm,
    OrderForm,
    CustomerEditForm,
)


class CustomLoginView(LoginView):
    template_name = "registration/login.html"

    def form_valid(self, form):
        response = super().form_valid(form)
        remember = self.request.POST.get("remember")
        if not remember:
            self.request.session.set_expiry(0)
        else:
            self.request.session.set_expiry(60 * 60 * 24 * 14)
        return response


@login_required
def dashboard(request: HttpRequest):
    total_orders = Order.objects.count()
    total_customers = Customer.objects.count()
    status_counts_qs = Order.objects.values("status").annotate(c=Count("id"))
    type_counts_qs = Order.objects.values("type").annotate(c=Count("id"))
    priority_counts_qs = Order.objects.values("priority").annotate(c=Count("id"))

    status_counts = {x["status"]: x["c"] for x in status_counts_qs}
    type_counts = {x["type"]: x["c"] for x in type_counts_qs}
    priority_counts = {x["priority"]: x["c"] for x in priority_counts_qs}

    # KPI metrics
    today = timezone.localdate()
    pending_count = status_counts.get("created", 0)
    in_progress_count = status_counts.get("in_progress", 0)
    completed_today_count = Order.objects.filter(status="completed", completed_at__date=today).count()

    # Trend: last 14 days orders created
    dates = [today - timezone.timedelta(days=i) for i in range(13, -1, -1)]
    trend_qs = (
        Order.objects.annotate(day=TruncDate("created_at")).values("day").annotate(c=Count("id"))
    )
    trend_map = {row["day"]: row["c"] for row in trend_qs}
    trend_labels = [d.strftime("%Y-%m-%d") for d in dates]
    trend_values = [trend_map.get(d, 0) for d in dates]

    recent_orders = Order.objects.select_related("customer", "vehicle").order_by("-created_at")[:10]
    completed = status_counts.get("completed", 0)
    completed_percent = int((completed * 100) / total_orders) if total_orders else 0

    charts = {
        "status": {
            "labels": ["Created", "Assigned", "In Progress", "Completed", "Cancelled"],
            "values": [
                status_counts.get("created", 0),
                status_counts.get("assigned", 0),
                status_counts.get("in_progress", 0),
                status_counts.get("completed", 0),
                status_counts.get("cancelled", 0),
            ],
        },
        "type": {
            "labels": ["Service", "Sales", "Consultation"],
            "values": [
                type_counts.get("service", 0),
                type_counts.get("sales", 0),
                type_counts.get("consultation", 0),
            ],
        },
        "priority": {
            "labels": ["Low", "Medium", "High", "Urgent"],
            "values": [
                priority_counts.get("low", 0),
                priority_counts.get("medium", 0),
                priority_counts.get("high", 0),
                priority_counts.get("urgent", 0),
            ],
        },
        "trend": {"labels": trend_labels, "values": trend_values},
    }

    return render(
        request,
        "tracker/dashboard.html",
        {
            "total_orders": total_orders,
            "total_customers": total_customers,
            "pending_count": pending_count,
            "in_progress_count": in_progress_count,
            "completed_today_count": completed_today_count,
            "status_counts": status_counts,
            "type_counts": type_counts,
            "recent_orders": recent_orders,
            "completed_percent": completed_percent,
            "charts_json": json.dumps(charts),
        },
    )


@login_required
@login_required
def customers_list(request: HttpRequest):
    q = request.GET.get('q','').strip()
    qs = Customer.objects.all().order_by('-registration_date')
    if q:
        qs = qs.filter(full_name__icontains=q)
    paginator = Paginator(qs, 20)
    page = request.GET.get('page')
    customers = paginator.get_page(page)
    return render(request, "tracker/customers_list.html", {"customers": customers, "q": q})


@login_required
def customers_search(request: HttpRequest):
    q = request.GET.get("q", "").strip()
    results = []
    if q:
        results = Customer.objects.filter(full_name__icontains=q)[:10]
    data = [
        {
            "id": c.id,
            "code": c.code,
            "name": c.full_name,
            "phone": c.phone,
            "type": c.customer_type,
            "last_visit": c.last_visit.isoformat() if c.last_visit else None,
        }
        for c in results
    ]
    return JsonResponse({"results": data})


@login_required
def customer_detail(request: HttpRequest, pk: int):
    c = get_object_or_404(Customer, pk=pk)
    vehicles = c.vehicles.all()
    orders = c.orders.order_by("-created_at")[:20]
    return render(request, "tracker/customer_detail.html", {"customer": c, "vehicles": vehicles, "orders": orders})


@login_required
def customer_register(request: HttpRequest):
    step = int(request.POST.get("step", request.GET.get("step", 1)))
    if request.method == "POST":
        if step == 1:
            form = CustomerStep1Form(request.POST)
            action = request.POST.get("action")
            if form.is_valid():
                if action == "save_customer":
                    data = form.cleaned_data
                    c = Customer.objects.create(
                        full_name=data.get("full_name"),
                        phone=data.get("phone"),
                        email=data.get("email"),
                        address=data.get("address"),
                        notes=data.get("notes"),
                    )
                    messages.success(request, "Customer saved successfully")
                    return redirect("tracker:customer_detail", pk=c.id)
                request.session["reg_step1"] = form.cleaned_data
                return redirect("tracker:customer_register")
        elif step == 2:
            form = CustomerStep2Form(request.POST)
            if form.is_valid():
                request.session["reg_step2"] = form.cleaned_data
                return redirect("tracker:customer_register")
        elif step == 3:
            form = CustomerStep3Form(request.POST)
            if form.is_valid():
                request.session["reg_step3"] = form.cleaned_data
                return redirect("tracker:customer_register")
        elif step == 4:
            form = CustomerStep4Form(request.POST)
            vehicle_form = VehicleForm(request.POST)
            order_form = OrderForm(request.POST)
            if form.is_valid() and order_form.is_valid():
                data = {**request.session.get("reg_step1", {}), **form.cleaned_data}
                c = Customer.objects.create(
                    full_name=data.get("full_name"),
                    phone=data.get("phone"),
                    email=data.get("email"),
                    address=data.get("address"),
                    notes=data.get("notes"),
                    customer_type=data.get("customer_type"),
                    organization_name=data.get("organization_name"),
                    tax_number=data.get("tax_number"),
                    personal_subtype=data.get("personal_subtype"),
                )
                v = None
                if vehicle_form.is_valid() and any(vehicle_form.cleaned_data.values()):
                    v = vehicle_form.save(commit=False)
                    v.customer = c
                    v.save()
                o = order_form.save(commit=False)
                o.customer = c
                o.vehicle = v
                o.status = "created"
                if o.type == "service":
                    pass
                o.save()
                for key in ["reg_step1", "reg_step2", "reg_step3"]:
                    request.session.pop(key, None)
                messages.success(request, "Customer registered and order created successfully")
                return redirect("tracker:customer_detail", pk=c.id)
            else:
                messages.error(request, "Please correct the highlighted errors and try again")
    # GET or invalid POST
    context = {"step": step}
    if step == 1:
        context["form"] = CustomerStep1Form(initial=request.session.get("reg_step1"))
    elif step == 2:
        context["form"] = CustomerStep2Form(initial=request.session.get("reg_step2"))
    elif step == 3:
        context["form"] = CustomerStep3Form(initial=request.session.get("reg_step3"))
    else:
        context["form"] = CustomerStep4Form()
        context["vehicle_form"] = VehicleForm()
        context["order_form"] = OrderForm()
    return render(request, "tracker/customer_register.html", context)


@login_required
def create_order_for_customer(request: HttpRequest, pk: int):
    c = get_object_or_404(Customer, pk=pk)
    if request.method == "POST":
        form = OrderForm(request.POST)
        # Ensure vehicle belongs to this customer
        form.fields["vehicle"].queryset = c.vehicles.all()
        if form.is_valid():
            o = form.save(commit=False)
            o.customer = c
            o.status = "created"
            o.save()
            messages.success(request, "Order created successfully")
            return redirect("tracker:order_detail", pk=o.id)
        else:
            messages.error(request, "Please fix form errors and try again")
    else:
        form = OrderForm()
        form.fields["vehicle"].queryset = c.vehicles.all()
    return render(request, "tracker/order_create.html", {"customer": c, "form": form})


@login_required
def orders_list(request: HttpRequest):
    status = request.GET.get("status", "all")
    type_ = request.GET.get("type", "all")
    qs = Order.objects.select_related("customer", "vehicle").order_by("-created_at")
    if status != "all":
        qs = qs.filter(status=status)
    if type_ != "all":
        qs = qs.filter(type=type_)
    return render(request, "tracker/orders_list.html", {"orders": qs[:100]})


@login_required
def order_start(request: HttpRequest):
    return render(request, "tracker/order_start.html")


@login_required
def order_detail(request: HttpRequest, pk: int):
    o = get_object_or_404(Order, pk=pk)
    return render(request, "tracker/order_detail.html", {"order": o})


@login_required
def update_order_status(request: HttpRequest, pk: int):
    o = get_object_or_404(Order, pk=pk)
    status = request.POST.get("status")
    now = timezone.now()
    if status in dict(Order.STATUS_CHOICES):
        o.status = status
        if status == "assigned":
            o.assigned_at = now
        elif status == "in_progress":
            o.started_at = now
        elif status == "completed":
            o.completed_at = now
            if o.started_at:
                o.actual_duration = int((now - o.started_at).total_seconds() // 60)
            c = o.customer
            c.total_spent = c.total_spent + 0  # integrate billing later
            c.last_visit = now
            c.current_status = "completed"
            c.save()
        elif status == "cancelled":
            o.cancelled_at = now
        o.save()
        messages.success(request, f"Order status updated to {status.replace('_',' ').title()}")
    else:
        messages.error(request, "Invalid status")
    return redirect("tracker:order_detail", pk=o.id)


@login_required
def analytics(request: HttpRequest):
    # Reuse dashboard datasets for charts
    status_counts_qs = Order.objects.values("status").annotate(c=Count("id"))
    type_counts_qs = Order.objects.values("type").annotate(c=Count("id"))

    status_counts = {x["status"]: x["c"] for x in status_counts_qs}
    type_counts = {x["type"]: x["c"] for x in type_counts_qs}

    today = timezone.localdate()
    dates = [today - timezone.timedelta(days=i) for i in range(13, -1, -1)]
    trend_qs = (
        Order.objects.annotate(day=TruncDate("created_at")).values("day").annotate(c=Count("id"))
    )
    trend_map = {row["day"]: row["c"] for row in trend_qs}
    trend_labels = [d.strftime("%Y-%m-%d") for d in dates]
    trend_values = [trend_map.get(d, 0) for d in dates]

    dur_qs = (
        Order.objects.filter(actual_duration__isnull=False)
        .values("type")
        .annotate(avg=Avg("actual_duration"))
    )
    dur_labels = [
        {"service": "Service", "sales": "Sales", "consultation": "Consultation"}.get(r["type"], r["type"]) for r in dur_qs
    ]
    dur_values = [int(r["avg"]) for r in dur_qs]

    charts = {
        "status": {
            "labels": ["Created", "Assigned", "In Progress", "Completed", "Cancelled"],
            "values": [
                status_counts.get("created", 0),
                status_counts.get("assigned", 0),
                status_counts.get("in_progress", 0),
                status_counts.get("completed", 0),
                status_counts.get("cancelled", 0),
            ],
        },
        "type": {
            "labels": ["Service", "Sales", "Consultation"],
            "values": [
                type_counts.get("service", 0),
                type_counts.get("sales", 0),
                type_counts.get("consultation", 0),
            ],
        },
        "trend": {"labels": trend_labels, "values": trend_values},
        "avg_duration": {"labels": dur_labels, "values": dur_values},
    }

    return render(request, "tracker/analytics.html", {"charts_json": json.dumps(charts)})


@login_required
def reports(request: HttpRequest):
    f_from = request.GET.get("from")
    f_to = request.GET.get("to")
    f_type = request.GET.get("type", "all")
    qs = Order.objects.select_related("customer").order_by("-created_at")
    if f_from:
        try:
            qs = qs.filter(created_at__date__gte=f_from)
        except Exception:
            pass
    if f_to:
        try:
            qs = qs.filter(created_at__date__lte=f_to)
        except Exception:
            pass
    if f_type and f_type != "all":
        qs = qs.filter(type=f_type)

    total = qs.count()
    by_status = dict(qs.values_list("status").annotate(c=Count("id")))
    stats = {
        "total": total,
        "completed": by_status.get("completed", 0),
        "in_progress": by_status.get("in_progress", 0),
        "cancelled": by_status.get("cancelled", 0),
    }
    orders = list(qs[:300])
    return render(
        request,
        "tracker/reports.html",
        {"orders": orders, "stats": stats, "filters": {"from": f_from, "to": f_to, "type": f_type}},
    )

@login_required
def reports_export(request: HttpRequest):
    # Same filters as reports
    f_from = request.GET.get("from")
    f_to = request.GET.get("to")
    f_type = request.GET.get("type", "all")
    qs = Order.objects.select_related("customer").order_by("-created_at")
    if f_from:
        try:
            qs = qs.filter(created_at__date__gte=f_from)
        except Exception:
            pass
    if f_to:
        try:
            qs = qs.filter(created_at__date__lte=f_to)
        except Exception:
            pass
    if f_type and f_type != "all":
        qs = qs.filter(type=f_type)

    # Build CSV
    import csv
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="orders_report.csv"'
    writer = csv.writer(response)
    writer.writerow(["Order", "Customer", "Type", "Status", "Priority", "Created At"])
    for o in qs.iterator():
        writer.writerow([o.order_number, o.customer.full_name, o.type, o.status, o.priority, o.created_at.isoformat()])
    return response

@login_required
def customers_export(request: HttpRequest):
    q = request.GET.get('q','').strip()
    qs = Customer.objects.all().order_by('-registration_date')
    if q:
        qs = qs.filter(full_name__icontains=q)
    import csv
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="customers.csv"'
    writer = csv.writer(response)
    writer.writerow(['Code','Name','Phone','Type','Visits','Last Visit'])
    for c in qs.iterator():
        writer.writerow([c.code, c.full_name, c.phone, c.customer_type, c.total_visits, c.last_visit.isoformat() if c.last_visit else '' ])
    return response

@login_required
def orders_export(request: HttpRequest):
    status = request.GET.get('status','all')
    type_ = request.GET.get('type','all')
    qs = Order.objects.select_related('customer').order_by('-created_at')
    if status != 'all':
        qs = qs.filter(status=status)
    if type_ != 'all':
        qs = qs.filter(type=type_)
    import csv
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="orders.csv"'
    writer = csv.writer(response)
    writer.writerow(["Order","Customer","Type","Status","Priority","Created At"])
    for o in qs.iterator():
        writer.writerow([o.order_number, o.customer.full_name, o.type, o.status, o.priority, o.created_at.isoformat()])
    return response

@login_required
def api_recent_orders(request: HttpRequest):
    recents = Order.objects.select_related("customer", "vehicle").order_by("-created_at")[:10]
    data = [
        {
            "order_number": r.order_number,
            "status": r.status,
            "type": r.type,
            "priority": r.priority,
            "customer": r.customer.full_name,
            "vehicle": r.vehicle.plate_number if r.vehicle else None,
            "created_at": r.created_at.isoformat(),
        }
        for r in recents
    ]
    return JsonResponse({"orders": data})

# Permissions
is_manager = user_passes_test(lambda u: u.is_authenticated and (u.is_superuser or u.groups.filter(name='manager').exists()))

@login_required
@is_manager
def inventory_list(request: HttpRequest):
    q = request.GET.get('q','').strip()
    qs = InventoryItem.objects.all().order_by('-created_at')
    if q:
        qs = qs.filter(name__icontains=q)
    paginator = Paginator(qs, 20)
    page = request.GET.get('page')
    items = paginator.get_page(page)
    return render(request, 'tracker/inventory_list.html', { 'items': items, 'q': q })

@login_required
@is_manager
def inventory_create(request: HttpRequest):
    from .forms import InventoryItemForm
    if request.method == 'POST':
        form = InventoryItemForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Inventory item created')
            return redirect('tracker:inventory_list')
        else:
            messages.error(request, 'Please correct errors and try again')
    else:
        form = InventoryItemForm()
    return render(request, 'tracker/inventory_form.html', { 'form': form, 'mode': 'create' })

@login_required
@is_manager
def inventory_edit(request: HttpRequest, pk: int):
    from .forms import InventoryItemForm
    item = get_object_or_404(InventoryItem, pk=pk)
    if request.method == 'POST':
        form = InventoryItemForm(request.POST, instance=item)
        if form.is_valid():
            form.save()
            messages.success(request, 'Inventory item updated')
            return redirect('tracker:inventory_list')
        else:
            messages.error(request, 'Please correct errors and try again')
    else:
        form = InventoryItemForm(instance=item)
    return render(request, 'tracker/inventory_form.html', { 'form': form, 'mode': 'edit', 'item': item })

@login_required
@is_manager
def inventory_delete(request: HttpRequest, pk: int):
    item = get_object_or_404(InventoryItem, pk=pk)
    if request.method == 'POST':
        item.delete()
        messages.success(request, 'Inventory item deleted')
        return redirect('tracker:inventory_list')
    return render(request, 'tracker/inventory_delete.html', { 'item': item })

@login_required
@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def users_list(request: HttpRequest):
    q = request.GET.get('q','').strip()
    qs = User.objects.all().order_by('-date_joined')
    if q:
        qs = qs.filter(username__icontains=q)
    return render(request, 'tracker/users_list.html', { 'users': qs[:100], 'q': q })

@login_required
@user_passes_test(lambda u: u.is_superuser)
def user_edit(request: HttpRequest, pk: int):
    from .forms import AdminUserForm
    u = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        form = AdminUserForm(request.POST, instance=u)
        if form.is_valid():
            form.save()
            messages.success(request, 'User updated')
            return redirect('tracker:users_list')
        else:
            messages.error(request, 'Please correct errors and try again')
    else:
        form = AdminUserForm(instance=u)
    return render(request, 'tracker/user_edit.html', { 'form': form, 'user_obj': u })


@login_required
def customer_edit(request: HttpRequest, pk: int):
    customer = get_object_or_404(Customer, pk=pk)
    if request.method == 'POST':
        form = CustomerEditForm(request.POST, instance=customer)
        if form.is_valid():
            form.save()
            messages.success(request, 'Customer updated successfully')
            return redirect('tracker:customer_detail', pk=customer.id)
        else:
            messages.error(request, 'Please correct errors and try again')
    else:
        form = CustomerEditForm(instance=customer)
    return render(request, 'tracker/customer_edit.html', { 'form': form, 'customer': customer })
