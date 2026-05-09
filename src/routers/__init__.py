# Import all routers to make them available when importing from this package
from . import auth, users, products, customers, vendors, salesman, stock, expenses, refunds, admin, pos, customer_category, warehouse_stock, warehouse_customers, warehouse_vendors

# Import specific routers to make them available
from .auth import router as auth_router
from .users import router as users_router
from .products import router as products_router
from .customers import router as customers_router
from .vendors import router as vendors_router
from .salesman import router as salesman_router
from .stock import router as stock_router
from .expenses import router as expenses_router
from .refunds import router as refunds_router
from .admin import router as admin_router
from .pos import router as pos_router
from .customer_category import router as customer_category_router
from .warehouse_stock import router as warehouse_stock_router
from .warehouse_customers import router as warehouse_customers_router
from .warehouse_vendors import router as warehouse_vendors_router