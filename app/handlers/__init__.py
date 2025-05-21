from aiogram import Router
from .user import start, services, about, support, my_appointments, discounts
from .admin import panel, service_management, master_management, exports, cancel_booking, user_management, broadcast


def setup_routers() -> Router:
    router = Router()
    router.include_routers(
        start.router,
        services.router,
        about.router,
        support.router,
        discounts.router,
        my_appointments.router,
        exports.router,
        cancel_booking.router,
        user_management.router,
        broadcast.router,
        panel.router,
        service_management.router,
        master_management.router,
    )
    return router
