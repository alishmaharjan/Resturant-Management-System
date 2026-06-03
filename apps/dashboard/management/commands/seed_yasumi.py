"""
Seed command — complete Yasumi menu from accountant spreadsheets.

Usage:
  python manage.py seed_yasumi
  python manage.py seed_yasumi --clear   # wipe and re-seed
"""
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()

# ── TABLES ────────────────────────────────────────────────────────────────────
TABLES = [
    ('T1', 4), ('T2', 4), ('T3', 4), ('T4', 4),
    ('T5', 4), ('T6', 4), ('T7', 2), ('T8', 2),
    ('T9', 6), ('T10', 6), ('T11', 8), ('T12', 8),
    ('BAR-1', 2), ('BAR-2', 2), ('BAR-3', 2),
    ('GARDEN-1', 4), ('GARDEN-2', 4), ('GARDEN-3', 4),
]

# ── MENU  { category: [(name, price_Rs), ...] } ───────────────────────────────
# All categories in English only. Prices from accountant spreadsheet.
MENU = {

    # ─── FOOD ────────────────────────────────────────────────────────────────

    'Side Dishes': [
        ('Miso Soup',                          200),
        ('Seaweed Salad',                      250),
        ('Edamame',                            300),
        ('Spicy Edamame',                      350),
        ('Pickled Vegetables',                 350),
        ('Tofu Steak (3pcs)',                  300),
        ('Miso Aubergine (3pcs)',              300),
    ],

    'Starters': [
        ('Veg Gyoza (5pcs)',                   350),
        ('Agedashi Tofu (4pcs)',               390),
        ('Prawn Tempura (4pcs)',               390),
        ('Croquette (3pcs)',                   300),
        ('Chicken Gyoza (5pcs)',               390),
        ('Prawn Gyoza (5pcs)',                 490),
        ('Deep Fried Prawn (2pcs)',            390),
        ('Chicken Yakitori (3 Skewers)',       590),
        ('Chicken Wings (3pcs)',               690),
        ('Spicy Chicken Wings (3pcs)',         750),
        ('Chicken Karaage (8pcs)',             690),
        ('Spicy Chicken Karaage (8pcs)',       750),
        ('Chili Squid (8pcs)',                 750),
    ],

    'Salads': [
        ('Mixed Tempura (5pcs)',              1400),
        ('Garden Salad',                       590),
        ('Chicken Salad',                      640),
        ('Salmon Sashimi Salad',               900),
        ('Tuna Sashimi Salad',                 900),
        ('Squid Salad (4pcs)',                1210),
    ],

    'Sashimi Special': [
        ('Octopus Sashimi (4pcs)',            1350),
        ('Eel Sashimi (3pcs)',               1450),
        ('Salmon Sashimi (3pcs)',            1500),
        ('Tuna Sashimi (3pcs)',              1550),
        ('Tamago Sashimi (5pcs)',              640),
        ('Mix Sushi Platter',                1810),
    ],

    'Platters': [
        ('Salmon Sushi Platter',             5590),
        ('Tamago Sashimi Raw (5pcs)',        1500),
        ('Sashimi Platter Raw',             14990),
    ],

    'Carpaccio': [
        ('Salmon Carpaccio (7pcs)',           2490),
        ('Tuna Carpaccio (7pcs)',             2490),
    ],

    'Special Rolls': [
        ('Futomaki Thick Roll (8pcs)',        1710),
        ('Mouth on Fire Roll (5pcs)',         1710),
        ('Fire Roll (6pcs)',                  1710),
        ('Rainbow Roll',                      1650),
        ('Caterpillar Roll',                  2100),
        ('Tiger Roll (8pcs)',                 2810),
        ('King Dragon Roll (8pcs)',           2970),
        ('Tempura Vegetable Roll',            1210),
        ('Tempura Chicken Avocado Roll',      1710),
        ('Tempura Thick Roll',               1650),
        ('Tempura Salmon Avocado Roll',       1950),
    ],

    'Hand Rolls': [
        ('Salmon Hand Roll (2pcs)',           1450),
        ('Salmon Avocado Hand Roll (2pcs)',   1550),
        ('Spicy Tuna Hand Roll (2pcs)',       1550),
        ('California Hand Roll (2pcs)',       1450),
        ('Salmon Roe Hand Roll (2pcs)',       1910),
        ('Avocado Veg Hand Roll',              600),
        ('Cucumber Veg Hand Roll',             600),
    ],

    'Nigiri Sushi': [
        ('Egg Nigiri (3pcs)',                  900),
        ('Squid Nigiri (3pcs)',              1210),
        ('Tuna Nigiri (3pcs)',               1350),
        ('Prawn Nigiri (3pcs)',              1300),
        ('Octopus Nigiri (3pcs)',            1350),
        ('Eel Nigiri (3pcs)',               1450),
        ('Salmon Nigiri (3pcs)',             1350),
        ('Salmon Roe Nigiri (3pcs)',         1910),
    ],

    'Sushi Rolls': [
        ('Vegetable Roll (6pcs)',              910),
        ('Chicken Avocado Roll (6pcs)',       1710),
        ('California Roll (6pcs)',            1550),
        ('Salmon Avocado Roll (6pcs)',        1650),
        ('Tuna Avocado Roll (6pcs)',          1710),
        ('Tempura Avocado Roll (6pcs)',       1710),
        ('Tuna Roll (6pcs)',                  1450),
        ('Salmon Roll (6pcs)',               1450),
        ('Spicy Tuna Roll (6pcs)',            1450),
        ('Salmon & Avocado Roll (6pcs)',      1650),
        ('Avocado Veg Roll (6pcs)',            600),
        ('Cucumber Veg Roll (6pcs)',           600),
        ('Egg Veg Roll (6pcs)',                600),
    ],

    'Hot Pot': [
        ('Yasumi Special Hot Pot',           2200),
        ('Seafood Hot Pot',                    950),
    ],

    'Udon': [
        ('Veg Tempura Udon',                   590),
        ('Wakame Udon',                        550),
        ('Prawn Tempura Udon',                 790),
    ],

    'Hot Pot Add-ons': [
        ('Extra Egg',                           80),
        ('Extra Noodle (100gm)',               300),
        ('Extra Pork (100gm)',                 450),
        ('Extra Chicken (100gm)',              450),
        ('Extra Udon',                         350),
        ('Seafood Upgrade',                    950),
    ],

    'Sizzlers': [
        ('Chicken Katsu Sizzler',              790),
        ('Tonkatsu Sizzler (Pork)',            790),
        ('Deep Fried Prawn Sizzler',          1300),
        ('Salmon Teriyaki Sizzler',           1890),
    ],

    'Curry Rice': [
        ('Veg Curry',                          790),
        ('Chicken Curry',                      890),
        ('Pork Katsu Curry',                   890),
        ('Chicken Katsu Curry',                990),
        ('Prawn Curry',                       1050),
    ],

    'Rice Dishes': [
        ('Chicken Teriyaki Rice Bowl',         790),
        ('Spicy Chicken Teriyaki Bowl',        890),
        ('Chicken Katsu Rice Bowl',            990),
        ('Pork Katsu Rice Bowl',               990),
        ('Salmon Tempura Rice Bowl',          1380),
        ('Tofu Steak Rice Bowl',               650),
        ('Shogayaki Rice Bowl',                690),
        ('Eel Rice Bowl (Unaju)',             2500),
        ('Whole Eel Rice Bowl',              5000),
    ],

    'Bento Boxes': [
        ('Salmon Sushi Box',                  1100),
        ('Vegetarian Sushi Box',               900),
        ('Vegetarian Bento Box',              1300),
        ('Chicken Katsu Bento Box',           1250),
        ('Salmon Bento Box',                  1250),
        ('Pork Teriyaki Bento Box',           1250),
        ('Shogayaki Bento Box',               1350),
        ('Prawn Tempura Bento Box',           2400),
        ('Large Salmon Bento Box',            2800),
        ('Vegetarian Sushi Bento',            1600),
    ],

    'Fried Noodles': [
        ('Vegetable Fried Noodles',            790),
        ('Spicy Vegetable Fried Noodles',      810),
        ('Chicken Fried Noodles',              890),
        ('Spicy Chicken Fried Noodles',        950),
        ('Salmon Fried Noodles',              1800),
    ],

    'Ramen': [
        ('Miso Ramen (Veg / Vegan)',            750),
        ('Special Vegetable Ramen',             800),
        ('Chicken Shoyu Ramen',                 800),
        ('Tokyo Ramen',                         850),
        ('Tonkotsu Ramen',                      870),
        ('Spicy Chicken Ramen',                 870),
        ('Yasumi Spicy Ramen',                  900),
        ('Yasumi Spicy Pork Ramen',             900),
        ('Yasumi Special TanTan Ramen',         950),
    ],

    'Extras': [
        ('Boiled Rice',                         150),
        ('Teriyaki Sauce',                      250),
        ('Spicy Mayo',                          250),
        ('Chicken Chashu (5pcs)',               400),
    ],

    # ─── BEVERAGES ───────────────────────────────────────────────────────────

    'Japanese Sake': [
        ('Nama Chozo (300ml)',                2825),
        ('Nama Junmai Ginjo (200ml)',         1900),
        ('Nama Honjozo (200ml)',              1900),
        ('Yokaichi Imo PET (220ml)',          2715),
        ('One Cup Ozeki (200ml)',             1695),
        ('Dewazakura Ginjo (200ml)',          2150),
        ('Sayuri (300ml)',                    2825),
        ('Karatamba (300ml)',                 2715),
        ('Yokaichi Mugi PET (220ml)',         2715),
        ('Hana Awa Ka (250ml)',               2150),
        ('Niagara White (720ml)',             4825),
        ('Kerner White (720ml)',              7345),
        ('Josen Sake (30ml)',                  875),
        ('Josen Sake Bottle',               20355),
    ],

    'Spirits & Whiskey': [
        ('Pure Malt Whiskey (30ml)',          1525),
        ('Pure Malt Whiskey (700ml)',        32835),
        ('Blended Whiskey (30ml)',            1475),
        ('Blended Whiskey (700ml)',          32835),
        ('Haku Vodka (30ml)',                  975),
        ('Haku Vodka (700ml)',               18000),
        ('Craft Gin (30ml)',                   925),
        ('Craft Gin (700ml)',                21570),
        ('Roku Gin (30ml)',                    975),
        ('Roku Gin (700ml)',                 21600),
        ('Kinpyo Gold Leaf (720ml)',         29370),
        ('Nomo Nomo (30ml)',                   350),
        ('Nomo Nomo Bottle',                11750),
        ('Kumano Umeshu (100ml)',             1250),
    ],

    'Beer': [
        ('Somersby',                           490),
        ('Gorkha Pilsner (650ml)',             750),
        ('Gorkha Premium (650ml)',             750),
        ('Tuborg (650ml)',                     800),
        ('Carlsberg (650ml)',                  850),
        ('Barahsinghe Pilsner (330ml)',        490),
        ('Barahsinghe Belgian (330ml)',        490),
        ('Barahsinghe Pale Ale (330ml)',       490),
        ('Barahsinghe Red Fruit (330ml)',      490),
        ('Barahsinghe Hazy IPA (330ml)',       540),
        ('Barahsinghe Craft Lager (330ml)',    490),
    ],

    'Wine': [
        ('Amatia Red (Glass)',                3300),
        ('Amatia White (Glass)',              3300),
        ('Bottega Chianti',                   4500),
        ('Bottega Cabernet Sauvignon',        4500),
        ('Bottega Moscato',                   4500),
        ('Bottega Prosecco Brut',             4500),
        ('Bottega Chardonnay',                4500),
    ],

    'Cocktails': [
        ('Whisky Sour',                       1350),
        ('Negroni',                           1450),
    ],

    'New Drinks': [
        ('Crunchy Parley G Shake',             390),
        ('Cheese Cake Latte',                  390),
        ('Red Velvet Latte',                   450),
        ('Red Velvet Cake Shake',              390),
        ('Death By Chocolate',                 390),
        ('Belgian Hot Chocolate',              390),
        ('Blue Ocean Mojito',                  420),
        ('Virgin Mojito',                      420),
        ('Mint Mojito',                        420),
        ('Lemon Iced Tea',                     350),
        ('Peach Iced Tea',                     350),
        ('Watermelon Fizz',                    420),
        ('Black Kobra',                        350),
        ('Honey Hot Lemon',                    250),
    ],

    'Hot Coffee': [
        ('Espresso Single',                    170),
        ('Espresso Double',                    210),
        ('Americano',                          230),
        ('Cappuccino',                         280),
        ('Cafe Latte',                         350),
        ('Cafe Mocha',                         390),
        ('Hazelnut & Caramel Latte',           390),
        ('Hot Chocolate',                      310),
    ],

    'Cold Coffee': [
        ('Iced Americano',                     180),
        ('Iced Latte',                         320),
        ('Iced Mocha',                         390),
        ('Caramel Frappe',                     390),
        ('Coffee Frappe',                      390),
        ('Mocha Frappe',                       390),
        ('Cold Coffee',                        390),
    ],

    'Cold Drinks': [
        ('Fresh Lemon Soda',                   250),
        ('Lemonade',                           250),
        ('Mint Lemonade',                      260),
        ('Watermelon Juice',                   400),
    ],

    'Soft Drinks': [
        ('Coke (250ml)',                       150),
        ('Sprite (250ml)',                     150),
        ('Fanta (250ml)',                      150),
        ('Mineral Water',                       50),
    ],
}


# ─────────────────────────────────────────────────────────────────────────────
class Command(BaseCommand):
    help = 'Seed Yasumi with complete restaurant menu (food + beverages).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear', action='store_true',
            help='Delete ALL existing menu and table data before seeding.'
        )

    def handle(self, *args, **options):
        from apps.tables.models import Table
        from apps.menu.models import Category, MenuItem

        self.stdout.write('\n⛩  Seeding Yasumi Restaurant…\n' + '─' * 48)

        if options['clear']:
            from apps.billing.models import Payment, CreditRecord, CreditAccount
            from apps.orders.models import OrderItem, Order
            from apps.reports.models import AuditLog
            Payment.objects.all().delete()
            CreditRecord.objects.all().delete()
            CreditAccount.objects.all().delete()
            AuditLog.objects.all().delete()
            OrderItem.objects.all().delete()
            Order.objects.all().delete()
            MenuItem.objects.all().delete()
            Category.objects.all().delete()
            Table.objects.all().delete()
            self.stdout.write(self.style.WARNING('  ✓ Cleared all existing data'))

        # ── Tables ──────────────────────────────────────────
        t_new = 0
        for name, cap in TABLES:
            _, created = Table.objects.get_or_create(
                name=name, defaults={'capacity': cap, 'is_active': True}
            )
            if created:
                t_new += 1
        self.stdout.write(
            f'  ✓ Tables    : {t_new} created  '
            f'({len(TABLES) - t_new} already existed)'
        )

        # ── Categories + Items ──────────────────────────────
        c_new = m_new = 0
        for cat_name, items in MENU.items():
            cat, created = Category.objects.get_or_create(
                name=cat_name, defaults={'is_active': True}
            )
            if created:
                c_new += 1
            for item_name, price in items:
                _, i_created = MenuItem.objects.get_or_create(
                    name=item_name,
                    defaults={
                        'category':     cat,
                        'price':        Decimal(str(price)),
                        'tax_percent':  Decimal('0.00'),
                        'is_available': True,
                    }
                )
                if i_created:
                    m_new += 1

        total_items = sum(len(v) for v in MENU.values())
        self.stdout.write(
            f'  ✓ Categories: {c_new} created  '
            f'({len(MENU) - c_new} already existed)'
        )
        self.stdout.write(
            f'  ✓ Menu Items: {m_new} created  '
            f'({total_items - m_new} already existed)'
        )

        # ── Superuser ────────────────────────────────────────
        if not User.objects.filter(is_superuser=True).exists():
            User.objects.create_superuser('admin', 'admin@yasumi.local', 'admin')
            self.stdout.write(self.style.SUCCESS('  ✓ Superuser → admin / admin'))
        else:
            self.stdout.write('  ✓ Superuser already exists')

        self.stdout.write('─' * 48)
        self.stdout.write(self.style.SUCCESS(
            f'  ✅  Done — {len(TABLES)} tables · '
            f'{len(MENU)} categories · {total_items} items\n'
        ))
