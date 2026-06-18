from datetime import datetime, timedelta
import random

from models import db, User, Material, Supplier, SupplyRequest, Delivery


def seed_if_empty():
    if User.query.count() > 0:
        return
    _populate_database()


def seed_database():
    db.drop_all()
    db.create_all()
    _populate_database()


def _populate_database():
    # ---------------- ПОЛЬЗОВАТЕЛИ ----------------
    users = [
        User(
            full_name="Иванов Сергей Петрович",
            username="admin",
            password="admin123",
            email="admin@enterprise.ru",
            role="Администратор",
            is_active=True,
        ),
        User(
            full_name="Смирнова Анна Викторовна",
            username="manager",
            password="manager123",
            email="manager@enterprise.ru",
            role="Менеджер снабжения",
            is_active=True,
        ),
        User(
            full_name="Кузнецов Дмитрий Олегович",
            username="storekeeper",
            password="store123",
            email="storekeeper@enterprise.ru",
            role="Кладовщик",
            is_active=True,
        ),
    ]
    db.session.add_all(users)

    # ---------------- МАТЕРИАЛЫ ----------------
    materials = [
        Material(
            code="MAT-001",
            name="Бумага офисная А4, 500 листов",
            category="Канцелярия",
            unit="упак.",
            min_stock=10,
            current_stock=28,
            description="Офисная бумага для принтеров и копировальной техники.",
        ),
        Material(
            code="MAT-002",
            name="Картридж HP 85A (CE285A)",
            category="Оргтехника",
            unit="шт.",
            min_stock=5,
            current_stock=3,
            description="Расходный материал для лазерных принтеров HP.",
        ),
        Material(
            code="MAT-003",
            name="Принтер лазерный HP LaserJet Pro",
            category="Оргтехника",
            unit="шт.",
            min_stock=1,
            current_stock=2,
            description="Лазерный принтер для офисных подразделений.",
        ),
        Material(
            code="MAT-004",
            name="Стол офисный 1400x700 мм",
            category="Мебель",
            unit="шт.",
            min_stock=2,
            current_stock=4,
            description="Рабочий офисный стол для сотрудников.",
        ),
        Material(
            code="MAT-005",
            name="Кресло офисное эргономичное",
            category="Мебель",
            unit="шт.",
            min_stock=2,
            current_stock=1,
            description="Офисное кресло для оснащения рабочих мест.",
        ),
        Material(
            code="MAT-006",
            name="Шкаф архивный металлический",
            category="Мебель",
            unit="шт.",
            min_stock=1,
            current_stock=2,
            description="Металлический шкаф для хранения документации.",
        ),
        Material(
            code="MAT-007",
            name="Кабель ВВГнг 3x2.5",
            category="Электротехнические материалы",
            unit="м",
            min_stock=100,
            current_stock=65,
            description="Кабель для электромонтажных работ и эксплуатации помещений.",
        ),
        Material(
            code="MAT-008",
            name="Сетевой фильтр 5 розеток",
            category="Электротехнические материалы",
            unit="шт.",
            min_stock=5,
            current_stock=7,
            description="Сетевой фильтр для подключения офисной техники.",
        ),
        Material(
            code="MAT-009",
            name="Лампа светодиодная 36 Вт",
            category="Электротехнические материалы",
            unit="шт.",
            min_stock=10,
            current_stock=6,
            description="Осветительное оборудование для административных помещений.",
        ),
        Material(
            code="MAT-010",
            name="Болт М12 оцинкованный",
            category="Крепеж",
            unit="шт.",
            min_stock=200,
            current_stock=160,
            description="Крепежный элемент для монтажных и ремонтных работ.",
        ),
        Material(
            code="MAT-011",
            name="Папка-регистратор А4",
            category="Канцелярия",
            unit="шт.",
            min_stock=20,
            current_stock=35,
            description="Папка для хранения договоров и внутренних документов.",
        ),
        Material(
            code="MAT-012",
            name="Ручка шариковая синяя",
            category="Канцелярия",
            unit="шт.",
            min_stock=50,
            current_stock=80,
            description="Канцелярская продукция для сотрудников предприятия.",
        ),
        Material(
            code="MAT-013",
            name="Бутыль для кулера 19 л",
            category="Хозяйственные товары",
            unit="шт.",
            min_stock=6,
            current_stock=4,
            description="Питьевая вода для офисных и производственных подразделений.",
        ),
        Material(
            code="MAT-014",
            name="Моющее средство универсальное",
            category="Хозяйственные товары",
            unit="шт.",
            min_stock=12,
            current_stock=9,
            description="Средство для уборки служебных помещений.",
        ),
        Material(
            code="MAT-015",
            name="Перчатки хозяйственные",
            category="Хозяйственные товары",
            unit="пар",
            min_stock=20,
            current_stock=14,
            description="Средства для уборки и хозяйственного обслуживания.",
        ),
    ]
    db.session.add_all(materials)

    # ---------------- ПОСТАВЩИКИ ----------------
    suppliers = [
        Supplier(
            company_name='ООО "ОфисСнаб"',
            contact_person="Петрова Мария Андреевна",
            phone="+7 (495) 111-22-33",
            email="sales@office-snab.ru",
            address="г. Москва, ул. Складочная, д. 12",
            notes="Поставка канцелярии и офисной мебели.",
        ),
        Supplier(
            company_name='ООО "ТехРесурс"',
            contact_person="Алексеев Игорь Сергеевич",
            phone="+7 (495) 222-33-44",
            email="info@techresource.ru",
            address="г. Москва, пр-т Мира, д. 88",
            notes="Поставка оргтехники и расходных материалов.",
        ),
        Supplier(
            company_name='ООО "ЭнергоКомплект"',
            contact_person="Николаев Павел Олегович",
            phone="+7 (812) 345-67-89",
            email="zakaz@energokomplekt.ru",
            address="г. Санкт-Петербург, ул. Электриков, д. 7",
            notes="Электротехнические материалы и кабельная продукция.",
        ),
        Supplier(
            company_name='ООО "ХозМаркет"',
            contact_person="Соколова Елена Викторовна",
            phone="+7 (495) 444-55-66",
            email="market@hozmarket.ru",
            address="г. Москва, ул. Бытовая, д. 3",
            notes="Хозяйственные товары и расходные материалы.",
        ),
        Supplier(
            company_name='ООО "ПромСервис Логистика"',
            contact_person="Кузьмин Артём Валерьевич",
            phone="+7 (343) 555-66-77",
            email="supply@promservice-log.ru",
            address="г. Екатеринбург, ул. Индустриальная, д. 25",
            notes="Комплексные поставки для предприятий.",
        ),
        Supplier(
            company_name='ООО "МебельКорп"',
            contact_person="Воробьёва Ирина Павловна",
            phone="+7 (499) 777-88-99",
            email="corp@mebelcorp.ru",
            address="г. Москва, ул. Деловая, д. 19",
            notes="Корпоративная мебель для офисов и архивов.",
        ),
    ]
    db.session.add_all(suppliers)

    db.session.commit()

    # ---------------- ЗАЯВКИ ----------------
    departments = [
        "Административный отдел",
        "Отдел кадров",
        "Бухгалтерия",
        "ИТ-отдел",
        "Хозяйственная служба",
        "Склад",
        "Отдел эксплуатации",
        "Служба закупок",
    ]
    initiators = [
        "Смирнова Анна Викторовна",
        "Кузнецов Дмитрий Олегович",
        "Васильева Ольга Сергеевна",
        "Павлов Андрей Николаевич",
        "Морозова Ирина Игоревна",
    ]

    requests_data = [
        ("REQ-2026-001", 2, 4, "Высокий", "на согласовании", "Необходимо пополнить запас картриджей для бухгалтерии."),
        ("REQ-2026-002", 1, 12, "Средний", "выполнена", "Закупка бумаги для ежемесячной печати отчётности."),
        ("REQ-2026-003", 5, 3, "Высокий", "одобрена", "Оснащение нового рабочего места."),
        ("REQ-2026-004", 7, 80, "Высокий", "в закупке", "Кабель для ремонта линии питания."),
        ("REQ-2026-005", 9, 12, "Средний", "новая", "Замена ламп в административном корпусе."),
        ("REQ-2026-006", 13, 4, "Средний", "на согласовании", "Пополнение питьевой воды для офиса."),
        ("REQ-2026-007", 14, 6, "Низкий", "одобрена", "Хозяйственные товары для уборки помещений."),
        ("REQ-2026-008", 4, 2, "Средний", "выполнена", "Мебель для отдела кадров."),
        ("REQ-2026-009", 11, 15, "Низкий", "выполнена", "Папки для архивного хранения документов."),
        ("REQ-2026-010", 8, 5, "Средний", "одобрена", "Сетевые фильтры для новых рабочих мест."),
        ("REQ-2026-011", 3, 1, "Высокий", "на согласовании", "Принтер для канцелярии."),
        ("REQ-2026-012", 15, 10, "Низкий", "новая", "Перчатки для хозяйственной службы."),
        ("REQ-2026-013", 6, 1, "Средний", "отклонена", "Архивный шкаф, перенос на следующий квартал."),
        ("REQ-2026-014", 10, 40, "Средний", "в закупке", "Крепеж для монтажных работ."),
        ("REQ-2026-015", 12, 25, "Низкий", "выполнена", "Канцелярские принадлежности для подразделений."),
    ]

    supply_requests = []
    for item in requests_data:
        material_id, qty, priority, status, comment = item[1], item[2], item[3], item[4], item[5]

        supply_request = SupplyRequest(
            request_number=item[0],
            created_at=datetime.now() - timedelta(days=random.randint(1, 40), hours=random.randint(1, 12)),
            initiator=random.choice(initiators),
            department=random.choice(departments),
            material_id=material_id,
            quantity=qty,
            priority=priority,
            comment=comment,
            status=status,
        )
        supply_requests.append(supply_request)

    db.session.add_all(supply_requests)
    db.session.commit()

    # ---------------- ПОСТАВКИ ----------------
    deliveries_data = [
        ("DEL-2026-001", 1, 1, 20, 420.00, 2, "Доставлена"),
        ("DEL-2026-002", 2, 2, 5, 2890.00, 1, "Доставлена"),
        ("DEL-2026-003", 6, 4, 3, 15800.00, 8, "Доставлена"),
        ("DEL-2026-004", 3, 7, 120, 145.00, 4, "В пути"),
        ("DEL-2026-005", 4, 14, 10, 230.00, 7, "Доставлена"),
        ("DEL-2026-006", 1, 11, 25, 260.00, 9, "Доставлена"),
        ("DEL-2026-007", 5, 8, 8, 890.00, 10, "Запланирована"),
        ("DEL-2026-008", 2, 3, 1, 21900.00, 11, "Запланирована"),
        ("DEL-2026-009", 4, 13, 6, 380.00, 6, "Доставлена"),
        ("DEL-2026-010", 3, 9, 15, 780.00, 5, "В пути"),
        ("DEL-2026-011", 6, 5, 4, 14250.00, 3, "Доставлена"),
        ("DEL-2026-012", 5, 10, 100, 24.00, 14, "Доставлена"),
    ]

    deliveries = []
    for item in deliveries_data:
        supplier_id = item[1]
        material_id = item[2]
        quantity = item[3]
        unit_price = item[4]
        request_id = item[5]
        status = item[6]

        total_price = quantity * unit_price

        delivery = Delivery(
            delivery_number=item[0],
            delivery_date=datetime.now() - timedelta(days=random.randint(1, 30)),
            supplier_id=supplier_id,
            material_id=material_id,
            quantity=quantity,
            unit_price=unit_price,
            total_price=total_price,
            request_id=request_id,
            status=status,
        )
        deliveries.append(delivery)

    db.session.add_all(deliveries)
    db.session.commit()

    print("Тестовые данные успешно добавлены.")


if __name__ == "__main__":
    from app import create_app

    application = create_app()
    with application.app_context():
        seed_database()
