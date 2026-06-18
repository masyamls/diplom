import os
from datetime import datetime, timedelta
from functools import wraps

from flask import Flask, flash, redirect, render_template, request, session, url_for

from models import db, Delivery, Material, Supplier, SupplyRequest, User


REQUEST_STATUSES = ["новая", "на согласовании", "одобрена", "отклонена", "в закупке", "выполнена"]
DELIVERY_STATUSES = ["Запланирована", "В пути", "Доставлена"]
USER_ROLES = ["Администратор", "Менеджер снабжения", "Кладовщик"]
STATUS_COLORS = {
    "новая": "#94a3b8",
    "на согласовании": "#f59e0b",
    "одобрена": "#3b82f6",
    "отклонена": "#ef4444",
    "в закупке": "#8b5cf6",
    "выполнена": "#22c55e",
}
ROLE_PERMISSIONS = {
    "Администратор": {
        "dashboard.view",
        "requests.view",
        "requests.create",
        "requests.edit",
        "requests.approve",
        "requests.delete",
        "materials.view",
        "materials.manage",
        "suppliers.view",
        "suppliers.manage",
        "deliveries.view",
        "stock.view",
        "reports.view",
        "users.view",
        "users.create",
        "users.edit",
        "users.delete",
    },
    "Менеджер снабжения": {
        "dashboard.view",
        "requests.view",
        "requests.create",
        "requests.edit",
        "requests.approve",
        "materials.view",
        "suppliers.view",
        "suppliers.manage",
        "deliveries.view",
        "stock.view",
        "reports.view",
    },
    "Кладовщик": {
        "dashboard.view",
        "requests.view",
        "requests.create",
        "materials.view",
        "deliveries.view",
        "stock.view",
    },
}


def create_app():
    app = Flask(__name__)

    instance_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), "instance")
    os.makedirs(instance_path, exist_ok=True)
    db_path = os.path.join(instance_path, "database.db")

    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "diploma-secret-key-2026")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
        "DATABASE_URL", f"sqlite:///{db_path.replace(os.sep, '/')}"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)

    with app.app_context():
        db.create_all()
        if User.query.count() == 0:
            from seed import seed_if_empty

            seed_if_empty()

    def get_current_user():
        user_id = session.get("user_id")
        if not user_id:
            return None
        return db.session.get(User, user_id)

    def has_permission(user, permission):
        if not user or not user.is_active:
            return False
        return permission in ROLE_PERMISSIONS.get(user.role, set())

    def login_required(view_func):
        @wraps(view_func)
        def wrapped_view(*args, **kwargs):
            if not get_current_user():
                flash("Для доступа к системе необходимо выполнить вход.", "warning")
                return redirect(url_for("login"))
            return view_func(*args, **kwargs)

        return wrapped_view

    def permission_required(permission):
        def decorator(view_func):
            @wraps(view_func)
            def wrapped_view(*args, **kwargs):
                user = get_current_user()
                if not user:
                    flash("Для доступа к системе необходимо выполнить вход.", "warning")
                    return redirect(url_for("login"))
                if not has_permission(user, permission):
                    flash("У вас нет прав для выполнения этого действия.", "danger")
                    return redirect(url_for("dashboard"))
                return view_func(*args, **kwargs)

            return wrapped_view

        return decorator

    def request_status_options(user):
        if has_permission(user, "requests.approve"):
            return REQUEST_STATUSES
        return ["новая", "на согласовании"]

    @app.template_filter("format_number")
    def format_number(value):
        if value is None:
            return ""
        try:
            value = float(value)
            if value.is_integer():
                return str(int(value))
            return f"{value:.2f}".rstrip("0").rstrip(".")
        except (ValueError, TypeError):
            return value

    @app.template_filter("format_currency")
    def format_currency(value):
        if value is None:
            return ""
        try:
            value = float(value)
            formatted = f"{value:,.2f}".replace(",", " ")
            if formatted.endswith(".00"):
                return formatted[:-3]
            return formatted.rstrip("0").rstrip(".")
        except (ValueError, TypeError):
            return value

    @app.context_processor
    def inject_user():
        user = get_current_user()
        return {
            "current_user": user,
            "can": lambda permission: has_permission(user, permission),
        }

    def build_trend(current_value, previous_value):
        delta = current_value - previous_value
        if previous_value == 0:
            percent = 100 if current_value > 0 else 0
        else:
            percent = round((delta / previous_value) * 100)

        if delta > 0:
            direction = "up"
            icon = "bi-arrow-up-right"
            tone = "positive"
            prefix = "+"
        elif delta < 0:
            direction = "down"
            icon = "bi-arrow-down-right"
            tone = "negative"
            prefix = ""
        else:
            direction = "flat"
            icon = "bi-dash"
            tone = "neutral"
            prefix = ""

        return {
            "delta": delta,
            "percent": percent,
            "prefix": prefix,
            "direction": direction,
            "icon": icon,
            "tone": tone,
        }

    def build_sparkline(values):
        cleaned = [max(int(value), 0) for value in values]
        top = max(cleaned) if cleaned else 1
        return [
            {"value": value, "height": max(18, round((value / top) * 54)) if top else 18}
            for value in cleaned
        ]

    def weekly_counts(model, date_field, extra_filter=None, weeks=6):
        now = datetime.now()
        result = []
        for index in range(weeks - 1, -1, -1):
            end = now - timedelta(days=index * 7)
            start = end - timedelta(days=7)
            query = model.query.filter(date_field >= start, date_field < end)
            if extra_filter is not None:
                query = query.filter(extra_filter)
            result.append(query.count())
        return result

    def status_segments(total_requests):
        cumulative = 0
        segments = []
        for status in REQUEST_STATUSES:
            count = SupplyRequest.query.filter_by(status=status).count()
            percent = round((count / total_requests) * 100, 2) if total_requests else 0
            start = cumulative
            cumulative += percent
            segments.append(
                {
                    "status": status,
                    "count": count,
                    "percent": percent,
                    "start": start,
                    "end": cumulative,
                    "color": STATUS_COLORS[status],
                }
            )
        return segments

    def build_low_stock_materials(limit=5):
        materials = (
            Material.query.filter(Material.current_stock < Material.min_stock)
            .order_by((Material.current_stock / Material.min_stock).asc(), Material.current_stock.asc())
            .limit(limit)
            .all()
        )
        enriched = []
        max_shortage_ratio = 0

        for material in materials:
            stock_ratio = (material.current_stock / material.min_stock) if material.min_stock else 1
            deficit = max(material.min_stock - material.current_stock, 0)
            shortage_ratio = (deficit / material.min_stock) if material.min_stock else 0
            max_shortage_ratio = max(max_shortage_ratio, shortage_ratio)

            if material.current_stock <= 0 or stock_ratio <= 0.25:
                criticality = "Критично"
                criticality_class = "critical"
            elif stock_ratio <= 0.6:
                criticality = "Высокий риск"
                criticality_class = "high"
            else:
                criticality = "Требует пополнения"
                criticality_class = "medium"

            enriched.append(
                {
                    "item": material,
                    "deficit": deficit,
                    "deficit_percent": round(shortage_ratio * 100),
                    "criticality": criticality,
                    "criticality_class": criticality_class,
                }
            )

        for item in enriched:
            shortage_ratio = item["deficit_percent"] / 100
            if max_shortage_ratio > 0:
                item["ratio_percent"] = max(round((shortage_ratio / max_shortage_ratio) * 100), 14)
            else:
                item["ratio_percent"] = 0

        return enriched

    def build_recommendations(pending_requests, in_transit_count, low_stock_count):
        recommendations = []

        if pending_requests:
            recommendations.append(
                {
                    "title": "Есть заявки на согласовании",
                    "text": f"Сейчас ожидают решения {pending_requests} заявок. Согласуйте приоритетные позиции.",
                    "link": url_for("dashboard", request_status="на согласовании"),
                    "link_text": "Открыть заявки",
                    "tone": "warning",
                    "icon": "bi-hourglass-split",
                }
            )

        if low_stock_count:
            recommendations.append(
                {
                    "title": "Нужно пополнить дефицитные материалы",
                    "text": f"Ниже минимального уровня находится {low_stock_count} позиций склада.",
                    "link": url_for("stock_list", stock_filter="low"),
                    "link_text": "Перейти на склад",
                    "tone": "danger",
                    "icon": "bi-exclamation-triangle",
                }
            )

        if in_transit_count:
            recommendations.append(
                {
                    "title": "Проверить поставки в пути",
                    "text": f"В процессе доставки находятся {in_transit_count} поставок. Уточните сроки у поставщиков.",
                    "link": url_for("deliveries_list", status="В пути"),
                    "link_text": "Открыть поставки",
                    "tone": "info",
                    "icon": "bi-truck",
                }
            )

        if not recommendations:
            recommendations.append(
                {
                    "title": "Критичных задач сейчас нет",
                    "text": "Система не видит срочных отклонений. Можно заняться плановыми закупками и анализом остатков.",
                    "link": url_for("reports"),
                    "link_text": "Открыть отчеты",
                    "tone": "success",
                    "icon": "bi-check2-circle",
                }
            )

        return recommendations

    @app.route("/")
    def index():
        if "user_id" in session:
            return redirect(url_for("dashboard"))
        return redirect(url_for("login"))

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "").strip()

            user = User.query.filter_by(username=username, password=password, is_active=True).first()

            if user:
                session["user_id"] = user.id
                flash("Вход выполнен успешно.", "success")
                return redirect(url_for("dashboard"))

            flash("Неверный логин или пароль.", "danger")

        return render_template("login.html")

    @app.route("/logout")
    def logout():
        session.clear()
        flash("Вы вышли из системы.", "info")
        return redirect(url_for("login"))

    @app.route("/dashboard")
    @login_required
    @permission_required("dashboard.view")
    def dashboard():
        request_search = request.args.get("request_search", "").strip()
        request_status = request.args.get("request_status", "").strip()

        total_requests = SupplyRequest.query.count()
        pending_requests = SupplyRequest.query.filter_by(status="на согласовании").count()
        completed_requests = SupplyRequest.query.filter_by(status="выполнена").count()
        total_materials = Material.query.count()
        total_suppliers = Supplier.query.count()
        low_stock_count = Material.query.filter(Material.current_stock < Material.min_stock).count()

        request_query = SupplyRequest.query.join(Material)
        if request_search:
            request_query = request_query.filter(
                db.or_(
                    SupplyRequest.request_number.ilike(f"%{request_search}%"),
                    SupplyRequest.department.ilike(f"%{request_search}%"),
                    SupplyRequest.initiator.ilike(f"%{request_search}%"),
                    Material.name.ilike(f"%{request_search}%"),
                )
            )
        if request_status:
            request_query = request_query.filter(SupplyRequest.status == request_status)
        latest_requests = request_query.order_by(SupplyRequest.created_at.desc()).limit(8).all()

        latest_deliveries = Delivery.query.order_by(Delivery.delivery_date.desc()).limit(6).all()
        status_data = status_segments(total_requests)
        low_stock_materials = build_low_stock_materials()

        recent_request_series = weekly_counts(SupplyRequest, SupplyRequest.created_at)
        pending_series = weekly_counts(
            SupplyRequest,
            SupplyRequest.created_at,
            SupplyRequest.status == "на согласовании",
        )
        completed_series = weekly_counts(
            SupplyRequest,
            SupplyRequest.created_at,
            SupplyRequest.status == "выполнена",
        )
        deliveries_series = weekly_counts(Delivery, Delivery.delivery_date)

        current_requests_period = sum(recent_request_series[-2:])
        previous_requests_period = sum(recent_request_series[-4:-2])
        current_pending_period = sum(pending_series[-2:])
        previous_pending_period = sum(pending_series[-4:-2])
        current_completed_period = sum(completed_series[-2:])
        previous_completed_period = sum(completed_series[-4:-2])
        current_deliveries_period = sum(deliveries_series[-2:])
        previous_deliveries_period = sum(deliveries_series[-4:-2])

        in_transit_count = Delivery.query.filter_by(status="В пути").count()

        kpis = [
            {
                "title": "Всего заявок",
                "value": total_requests,
                "subtitle": "За весь период работы системы",
                "icon": "bi-file-earmark-text",
                "icon_class": "bg-primary-subtle text-primary",
                "trend": build_trend(current_requests_period, previous_requests_period),
                "sparkline": build_sparkline(recent_request_series),
            },
            {
                "title": "На согласовании",
                "value": pending_requests,
                "subtitle": "Требуют управленческого решения",
                "icon": "bi-hourglass-split",
                "icon_class": "bg-warning-subtle text-warning",
                "trend": build_trend(current_pending_period, previous_pending_period),
                "sparkline": build_sparkline(pending_series),
            },
            {
                "title": "Выполнено",
                "value": completed_requests,
                "subtitle": "Закрытые заявки за период",
                "icon": "bi-check2-circle",
                "icon_class": "bg-success-subtle text-success",
                "trend": build_trend(current_completed_period, previous_completed_period),
                "sparkline": build_sparkline(completed_series),
            },
            {
                "title": "Поставки в работе",
                "value": in_transit_count,
                "subtitle": f"Всего поставщиков в базе: {total_suppliers}",
                "icon": "bi-truck",
                "icon_class": "bg-secondary-subtle text-secondary",
                "trend": build_trend(current_deliveries_period, previous_deliveries_period),
                "sparkline": build_sparkline(deliveries_series),
            },
            {
                "title": "Материалы",
                "value": total_materials,
                "subtitle": "Номенклатурные позиции склада",
                "icon": "bi-box",
                "icon_class": "bg-info-subtle text-info",
                "trend": {
                    "delta": low_stock_count,
                    "percent": round((low_stock_count / total_materials) * 100) if total_materials else 0,
                    "prefix": "",
                    "direction": "flat",
                    "icon": "bi-box-seam",
                    "tone": "neutral",
                },
                "sparkline": build_sparkline([total_materials - 4, total_materials - 3, total_materials - 2, total_materials - 1, total_materials, total_materials]),
            },
            {
                "title": "Дефицит",
                "value": low_stock_count,
                "subtitle": "Материалы ниже минимального уровня",
                "icon": "bi-exclamation-triangle",
                "icon_class": "bg-danger-subtle text-danger",
                "trend": {
                    "delta": low_stock_count,
                    "percent": round((low_stock_count / total_materials) * 100) if total_materials else 0,
                    "prefix": "",
                    "direction": "up" if low_stock_count else "flat",
                    "icon": "bi-activity",
                    "tone": "negative" if low_stock_count else "positive",
                },
                "sparkline": build_sparkline(
                    [item["deficit"] for item in low_stock_materials] + [0] * max(0, 6 - len(low_stock_materials))
                ),
            },
        ]

        recommendations = build_recommendations(pending_requests, in_transit_count, low_stock_count)

        return render_template(
            "dashboard.html",
            kpis=kpis,
            latest_requests=latest_requests,
            latest_deliveries=latest_deliveries,
            low_stock_materials=low_stock_materials,
            status_data=status_data,
            total_requests=total_requests,
            request_search=request_search,
            request_status=request_status,
            request_statuses=REQUEST_STATUSES,
            recommendations=recommendations,
        )

    @app.route("/requests")
    @login_required
    @permission_required("requests.view")
    def requests_list():
        search = request.args.get("search", "").strip()
        status = request.args.get("status", "").strip()

        query = SupplyRequest.query.join(Material)

        if search:
            query = query.filter(
                db.or_(
                    SupplyRequest.request_number.ilike(f"%{search}%"),
                    SupplyRequest.department.ilike(f"%{search}%"),
                    SupplyRequest.initiator.ilike(f"%{search}%"),
                    Material.name.ilike(f"%{search}%"),
                )
            )

        if status:
            query = query.filter(SupplyRequest.status == status)

        requests_items = query.order_by(SupplyRequest.created_at.desc()).all()

        return render_template(
            "requests/list.html",
            requests_items=requests_items,
            statuses=REQUEST_STATUSES,
            search=search,
            selected_status=status,
        )

    @app.route("/requests/create", methods=["GET", "POST"])
    @login_required
    @permission_required("requests.create")
    def request_create():
        current_user = get_current_user()
        materials = Material.query.order_by(Material.name.asc()).all()
        allowed_statuses = request_status_options(current_user)

        if request.method == "POST":
            last_request = SupplyRequest.query.order_by(SupplyRequest.id.desc()).first()
            next_id = 1 if not last_request else last_request.id + 1
            selected_status = request.form.get("status")
            if selected_status not in allowed_statuses:
                selected_status = allowed_statuses[0]

            new_request = SupplyRequest(
                request_number=f"REQ-2026-{next_id:03d}",
                initiator=request.form.get("initiator"),
                department=request.form.get("department"),
                material_id=int(request.form.get("material_id")),
                quantity=float(request.form.get("quantity")),
                priority=request.form.get("priority"),
                comment=request.form.get("comment"),
                status=selected_status,
            )

            db.session.add(new_request)
            db.session.commit()

            flash("Заявка успешно создана.", "success")
            return redirect(url_for("requests_list"))

        return render_template(
            "requests/form.html",
            request_item=None,
            materials=materials,
            statuses=allowed_statuses,
            form_title="Создание заявки",
        )

    @app.route("/requests/<int:request_id>")
    @login_required
    @permission_required("requests.view")
    def request_detail(request_id):
        request_item = SupplyRequest.query.get_or_404(request_id)
        return render_template("requests/detail.html", request_item=request_item)

    @app.route("/requests/<int:request_id>/edit", methods=["GET", "POST"])
    @login_required
    @permission_required("requests.edit")
    def request_edit(request_id):
        current_user = get_current_user()
        request_item = SupplyRequest.query.get_or_404(request_id)
        materials = Material.query.order_by(Material.name.asc()).all()
        allowed_statuses = request_status_options(current_user)

        if request.method == "POST":
            selected_status = request.form.get("status")
            if selected_status not in allowed_statuses:
                selected_status = request_item.status
            request_item.initiator = request.form.get("initiator")
            request_item.department = request.form.get("department")
            request_item.material_id = int(request.form.get("material_id"))
            request_item.quantity = float(request.form.get("quantity"))
            request_item.priority = request.form.get("priority")
            request_item.comment = request.form.get("comment")
            request_item.status = selected_status

            db.session.commit()

            flash("Изменения по заявке сохранены.", "success")
            return redirect(url_for("requests_list"))

        return render_template(
            "requests/form.html",
            request_item=request_item,
            materials=materials,
            statuses=allowed_statuses,
            form_title="Редактирование заявки",
        )

    @app.route("/requests/<int:request_id>/approve", methods=["POST"])
    @login_required
    @permission_required("requests.approve")
    def request_approve(request_id):
        request_item = SupplyRequest.query.get_or_404(request_id)
        next_url = request.form.get("next") or url_for("dashboard")

        if request_item.status != "на согласовании":
            flash("Согласование доступно только для заявок со статусом 'на согласовании'.", "warning")
            return redirect(next_url)

        request_item.status = "одобрена"
        db.session.commit()

        flash(f"Заявка {request_item.request_number} согласована.", "success")
        return redirect(next_url)

    @app.route("/requests/<int:request_id>/delete", methods=["POST"])
    @login_required
    @permission_required("requests.delete")
    def request_delete(request_id):
        request_item = SupplyRequest.query.get_or_404(request_id)
        db.session.delete(request_item)
        db.session.commit()

        flash("Заявка удалена.", "success")
        return redirect(url_for("requests_list"))

    @app.route("/materials")
    @login_required
    @permission_required("materials.view")
    def materials_list():
        search = request.args.get("search", "").strip()

        query = Material.query
        if search:
            query = query.filter(
                db.or_(
                    Material.name.ilike(f"%{search}%"),
                    Material.category.ilike(f"%{search}%"),
                    Material.code.ilike(f"%{search}%"),
                )
            )

        materials = query.order_by(Material.name.asc()).all()

        return render_template("materials/list.html", materials=materials, search=search)

    @app.route("/materials/create", methods=["GET", "POST"])
    @login_required
    @permission_required("materials.manage")
    def material_create():
        if request.method == "POST":
            material = Material(
                code=request.form.get("code"),
                name=request.form.get("name"),
                category=request.form.get("category"),
                unit=request.form.get("unit"),
                min_stock=float(request.form.get("min_stock")),
                current_stock=float(request.form.get("current_stock")),
                description=request.form.get("description"),
            )

            db.session.add(material)
            db.session.commit()

            flash("Материал успешно добавлен.", "success")
            return redirect(url_for("materials_list"))

        return render_template("materials/form.html", material=None, form_title="Добавление материала")

    @app.route("/materials/<int:material_id>")
    @login_required
    @permission_required("materials.view")
    def material_detail(material_id):
        material = Material.query.get_or_404(material_id)
        return render_template("materials/detail.html", material=material)

    @app.route("/materials/<int:material_id>/edit", methods=["GET", "POST"])
    @login_required
    @permission_required("materials.manage")
    def material_edit(material_id):
        material = Material.query.get_or_404(material_id)

        if request.method == "POST":
            material.code = request.form.get("code")
            material.name = request.form.get("name")
            material.category = request.form.get("category")
            material.unit = request.form.get("unit")
            material.min_stock = float(request.form.get("min_stock"))
            material.current_stock = float(request.form.get("current_stock"))
            material.description = request.form.get("description")

            db.session.commit()

            flash("Изменения по материалу сохранены.", "success")
            return redirect(url_for("materials_list"))

        return render_template("materials/form.html", material=material, form_title="Редактирование материала")

    @app.route("/materials/<int:material_id>/delete", methods=["POST"])
    @login_required
    @permission_required("materials.manage")
    def material_delete(material_id):
        material = Material.query.get_or_404(material_id)
        related_requests = SupplyRequest.query.filter_by(material_id=material.id).count()
        related_deliveries = Delivery.query.filter_by(material_id=material.id).count()

        if related_requests > 0 or related_deliveries > 0:
            flash("Материал нельзя удалить, так как он используется в заявках или поставках.", "danger")
            return redirect(url_for("materials_list"))

        db.session.delete(material)
        db.session.commit()

        flash("Материал удалён.", "success")
        return redirect(url_for("materials_list"))

    @app.route("/suppliers")
    @login_required
    @permission_required("suppliers.view")
    def suppliers_list():
        search = request.args.get("search", "").strip()

        query = Supplier.query
        if search:
            query = query.filter(
                db.or_(
                    Supplier.company_name.ilike(f"%{search}%"),
                    Supplier.contact_person.ilike(f"%{search}%"),
                    Supplier.email.ilike(f"%{search}%"),
                    Supplier.phone.ilike(f"%{search}%"),
                )
            )

        suppliers = query.order_by(Supplier.company_name.asc()).all()

        return render_template("suppliers/list.html", suppliers=suppliers, search=search)

    @app.route("/suppliers/create", methods=["GET", "POST"])
    @login_required
    @permission_required("suppliers.manage")
    def supplier_create():
        if request.method == "POST":
            supplier = Supplier(
                company_name=request.form.get("company_name"),
                contact_person=request.form.get("contact_person"),
                phone=request.form.get("phone"),
                email=request.form.get("email"),
                address=request.form.get("address"),
                notes=request.form.get("notes"),
            )

            db.session.add(supplier)
            db.session.commit()

            flash("Поставщик успешно добавлен.", "success")
            return redirect(url_for("suppliers_list"))

        return render_template("suppliers/form.html", supplier=None, form_title="Добавление поставщика")

    @app.route("/suppliers/<int:supplier_id>")
    @login_required
    @permission_required("suppliers.view")
    def supplier_detail(supplier_id):
        supplier = Supplier.query.get_or_404(supplier_id)
        deliveries_count = Delivery.query.filter_by(supplier_id=supplier.id).count()
        return render_template("suppliers/detail.html", supplier=supplier, deliveries_count=deliveries_count)

    @app.route("/suppliers/<int:supplier_id>/edit", methods=["GET", "POST"])
    @login_required
    @permission_required("suppliers.manage")
    def supplier_edit(supplier_id):
        supplier = Supplier.query.get_or_404(supplier_id)

        if request.method == "POST":
            supplier.company_name = request.form.get("company_name")
            supplier.contact_person = request.form.get("contact_person")
            supplier.phone = request.form.get("phone")
            supplier.email = request.form.get("email")
            supplier.address = request.form.get("address")
            supplier.notes = request.form.get("notes")

            db.session.commit()

            flash("Изменения по поставщику сохранены.", "success")
            return redirect(url_for("suppliers_list"))

        return render_template("suppliers/form.html", supplier=supplier, form_title="Редактирование поставщика")

    @app.route("/suppliers/<int:supplier_id>/delete", methods=["POST"])
    @login_required
    @permission_required("suppliers.manage")
    def supplier_delete(supplier_id):
        supplier = Supplier.query.get_or_404(supplier_id)
        related_deliveries = Delivery.query.filter_by(supplier_id=supplier.id).count()

        if related_deliveries > 0:
            flash("Поставщика нельзя удалить, так как он используется в поставках.", "danger")
            return redirect(url_for("suppliers_list"))

        db.session.delete(supplier)
        db.session.commit()

        flash("Поставщик удалён.", "success")
        return redirect(url_for("suppliers_list"))

    @app.route("/deliveries")
    @login_required
    @permission_required("deliveries.view")
    def deliveries_list():
        search = request.args.get("search", "").strip()
        status = request.args.get("status", "").strip()

        query = Delivery.query.join(Supplier).join(Material)
        if search:
            query = query.filter(
                db.or_(
                    Delivery.delivery_number.ilike(f"%{search}%"),
                    Supplier.company_name.ilike(f"%{search}%"),
                    Material.name.ilike(f"%{search}%"),
                )
            )
        if status:
            query = query.filter(Delivery.status == status)

        deliveries = query.order_by(Delivery.delivery_date.desc()).all()

        return render_template(
            "deliveries/list.html",
            deliveries=deliveries,
            statuses=DELIVERY_STATUSES,
            selected_status=status,
            search=search,
            total_deliveries_amount=sum(item.total_price for item in deliveries),
            in_transit_count=sum(1 for item in deliveries if item.status == "В пути"),
        )

    @app.route("/stock")
    @login_required
    @permission_required("stock.view")
    def stock_list():
        search = request.args.get("search", "").strip()
        stock_filter = request.args.get("stock_filter", "").strip()

        query = Material.query
        if search:
            query = query.filter(
                db.or_(
                    Material.code.ilike(f"%{search}%"),
                    Material.name.ilike(f"%{search}%"),
                    Material.category.ilike(f"%{search}%"),
                )
            )

        materials = query.order_by(Material.category.asc(), Material.name.asc()).all()
        if stock_filter == "low":
            materials = [item for item in materials if item.current_stock < item.min_stock]
        elif stock_filter == "ok":
            materials = [item for item in materials if item.current_stock >= item.min_stock]

        return render_template(
            "stock/list.html",
            materials=materials,
            search=search,
            selected_filter=stock_filter,
            total_positions=len(materials),
            low_stock_count=sum(1 for item in materials if item.current_stock < item.min_stock),
            zero_stock_count=sum(1 for item in materials if item.current_stock <= 0),
            categories_count=len({item.category for item in materials}),
        )

    @app.route("/reports")
    @login_required
    @permission_required("reports.view")
    def reports():
        date_from = request.args.get("date_from", "").strip()
        date_to = request.args.get("date_to", "").strip()

        delivery_filters = []
        parsed_date_from = None
        parsed_date_to = None

        def parse_report_date(value):
            for date_format in ("%d.%m.%Y", "%Y-%m-%d"):
                try:
                    return datetime.strptime(value, date_format)
                except ValueError:
                    continue
            raise ValueError

        if date_from:
            try:
                parsed_date_from = parse_report_date(date_from)
                delivery_filters.append(Delivery.delivery_date >= parsed_date_from)
            except ValueError:
                flash("Дата начала периода указана неверно.", "warning")
                date_from = ""

        if date_to:
            try:
                parsed_date_to = parse_report_date(date_to)
                delivery_filters.append(Delivery.delivery_date < parsed_date_to + timedelta(days=1))
            except ValueError:
                flash("Дата окончания периода указана неверно.", "warning")
                date_to = ""

        if parsed_date_from and parsed_date_to and parsed_date_from > parsed_date_to:
            flash("Дата начала периода не может быть позже даты окончания.", "warning")
            return redirect(url_for("reports", date_from=date_to, date_to=date_from))

        deliveries_query = Delivery.query
        if delivery_filters:
            deliveries_query = deliveries_query.filter(*delivery_filters)

        total_deliveries = deliveries_query.count()
        total_spend = deliveries_query.with_entities(
            db.func.coalesce(db.func.sum(Delivery.total_price), 0)
        ).scalar() or 0
        avg_delivery = deliveries_query.with_entities(
            db.func.coalesce(db.func.avg(Delivery.total_price), 0)
        ).scalar() or 0
        suppliers_count = deliveries_query.with_entities(
            db.func.count(db.distinct(Delivery.supplier_id))
        ).scalar() or 0

        top_materials_query = (
            db.session.query(
                Material.name.label("name"),
                Material.unit.label("unit"),
                db.func.sum(Delivery.quantity).label("total_quantity"),
                db.func.sum(Delivery.total_price).label("total_amount"),
            )
            .join(Delivery, Delivery.material_id == Material.id)
        )
        if delivery_filters:
            top_materials_query = top_materials_query.filter(*delivery_filters)
        top_materials = (
            top_materials_query.group_by(Material.id, Material.name, Material.unit)
            .order_by(db.func.sum(Delivery.quantity).desc())
            .limit(5)
            .all()
        )

        supplier_stats_query = (
            db.session.query(
                Supplier.company_name.label("company_name"),
                db.func.count(Delivery.id).label("deliveries_count"),
                db.func.sum(Delivery.quantity).label("total_quantity"),
                db.func.sum(Delivery.total_price).label("total_amount"),
            )
            .join(Delivery, Delivery.supplier_id == Supplier.id)
        )
        if delivery_filters:
            supplier_stats_query = supplier_stats_query.filter(*delivery_filters)
        supplier_stats = (
            supplier_stats_query.group_by(Supplier.id, Supplier.company_name)
            .order_by(db.func.sum(Delivery.total_price).desc())
            .limit(5)
            .all()
        )

        return render_template(
            "reports/index.html",
            date_from=date_from,
            date_to=date_to,
            total_deliveries=total_deliveries,
            total_spend=total_spend,
            avg_delivery=avg_delivery,
            suppliers_count=suppliers_count,
            top_materials=top_materials,
            supplier_stats=supplier_stats,
        )

    @app.route("/users")
    @login_required
    @permission_required("users.view")
    def users_list():
        search = request.args.get("search", "").strip()
        role = request.args.get("role", "").strip()

        query = User.query
        if search:
            query = query.filter(
                db.or_(
                    User.full_name.ilike(f"%{search}%"),
                    User.username.ilike(f"%{search}%"),
                    User.email.ilike(f"%{search}%"),
                )
            )
        if role:
            query = query.filter(User.role == role)

        users = query.order_by(User.full_name.asc()).all()

        return render_template(
            "users/list.html",
            users=users,
            roles=USER_ROLES,
            selected_role=role,
            search=search,
            active_users=sum(1 for item in users if item.is_active),
        )

    @app.route("/users/create", methods=["GET", "POST"])
    @login_required
    @permission_required("users.create")
    def user_create():
        if request.method == "POST":
            full_name = request.form.get("full_name", "").strip()
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "").strip()
            email = request.form.get("email", "").strip()
            role = request.form.get("role", "").strip()
            is_active = request.form.get("is_active") == "on"

            if role not in USER_ROLES:
                flash("Выберите корректную роль пользователя.", "warning")
                return render_template(
                    "users/form.html",
                    user=None,
                    roles=USER_ROLES,
                    form_title="Добавление пользователя",
                    form_data=request.form,
                )

            if User.query.filter_by(username=username).first():
                flash("Пользователь с таким логином уже существует.", "warning")
                return render_template(
                    "users/form.html",
                    user=None,
                    roles=USER_ROLES,
                    form_title="Добавление пользователя",
                    form_data=request.form,
                )

            if User.query.filter_by(email=email).first():
                flash("Пользователь с таким email уже существует.", "warning")
                return render_template(
                    "users/form.html",
                    user=None,
                    roles=USER_ROLES,
                    form_title="Добавление пользователя",
                    form_data=request.form,
                )

            user = User(
                full_name=full_name,
                username=username,
                password=password,
                email=email,
                role=role,
                is_active=is_active,
            )

            db.session.add(user)
            db.session.commit()

            flash("Пользователь успешно добавлен.", "success")
            return redirect(url_for("users_list"))

        return render_template(
            "users/form.html",
            user=None,
            roles=USER_ROLES,
            form_title="Добавление пользователя",
            form_data={},
        )

    @app.route("/users/<int:user_id>/edit", methods=["GET", "POST"])
    @login_required
    @permission_required("users.edit")
    def user_edit(user_id):
        user = User.query.get_or_404(user_id)

        if request.method == "POST":
            full_name = request.form.get("full_name", "").strip()
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "").strip()
            email = request.form.get("email", "").strip()
            role = request.form.get("role", "").strip()
            is_active = request.form.get("is_active") == "on"

            if role not in USER_ROLES:
                flash("Выберите корректную роль пользователя.", "warning")
                return render_template(
                    "users/form.html",
                    user=user,
                    roles=USER_ROLES,
                    form_title="Редактирование пользователя",
                    form_data=request.form,
                    is_edit=True,
                )

            username_owner = User.query.filter(User.username == username, User.id != user.id).first()
            if username_owner:
                flash("Пользователь с таким логином уже существует.", "warning")
                return render_template(
                    "users/form.html",
                    user=user,
                    roles=USER_ROLES,
                    form_title="Редактирование пользователя",
                    form_data=request.form,
                    is_edit=True,
                )

            email_owner = User.query.filter(User.email == email, User.id != user.id).first()
            if email_owner:
                flash("Пользователь с таким email уже существует.", "warning")
                return render_template(
                    "users/form.html",
                    user=user,
                    roles=USER_ROLES,
                    form_title="Редактирование пользователя",
                    form_data=request.form,
                    is_edit=True,
                )

            user.full_name = full_name
            user.username = username
            user.email = email
            user.role = role
            user.is_active = is_active
            if password:
                user.password = password

            db.session.commit()

            flash("Данные пользователя сохранены.", "success")
            return redirect(url_for("users_list"))

        return render_template(
            "users/form.html",
            user=user,
            roles=USER_ROLES,
            form_title="Редактирование пользователя",
            form_data={},
            is_edit=True,
        )

    @app.route("/users/<int:user_id>/delete", methods=["POST"])
    @login_required
    @permission_required("users.delete")
    def user_delete(user_id):
        current_user = get_current_user()
        user = User.query.get_or_404(user_id)

        if current_user and current_user.id == user.id:
            flash("Нельзя удалить собственную учетную запись.", "warning")
            return redirect(url_for("users_list"))

        db.session.delete(user)
        db.session.commit()

        flash("Пользователь удален.", "success")
        return redirect(url_for("users_list"))

    @app.errorhandler(404)
    def page_not_found(error):
        return render_template("404.html"), 404

    return app


app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "true").lower() in ("1", "true", "yes")
    app.run(host="0.0.0.0", port=port, debug=debug)
