# Import all routers to make them available when importing from this package
from . import auth, users, products, customers, vendors, salesman, stock, expenses, invoices, custom_orders, refunds, admin, pos

# Import specific routers to make them available
from .auth import router as auth_router
from .users import router as users_router
from .products import router as products_router
from .customers import router as customers_router
from .vendors import router as vendors_router
from .salesman import router as salesman_router
from .stock import router as stock_router
from .expenses import router as expenses_router
from .invoices import router as invoices_router
from .custom_orders import router as custom_orders_router
from .refunds import router as refunds_router
from .admin import router as admin_router
from .pos import router as pos_router