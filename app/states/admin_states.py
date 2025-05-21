from aiogram.fsm.state import StatesGroup, State


class AdminStates(StatesGroup):
    """Главные разделы админ-панели"""
    in_service_management = State()
    in_master_management = State()
    in_data_export = State()
    in_cancel_booking = State()
    in_manage_user = State()

    class Services(StatesGroup):
        """Управление услугами"""
        add_service = State()
        delete_service = State()
        edit_service = State()
        edit_service_name = State()

    class Masters(StatesGroup):
        """Управление мастерами"""
        # Добавление мастера
        add_name = State()
        add_about = State()
        add_interview = State()
        add_photo = State()

        # Редактирование мастера
        edit_select_master = State()
        edit_select_field = State()
        edit_name = State()
        edit_about = State()
        edit_interview = State()
        edit_photo = State()

        # Меню управления услугами
        edit_services_menu = State()

        # Добавление услуги мастеру
        add_service_select = State()
        add_service_name = State()
        add_service_price = State()
        add_service_duration = State()
        add_service_description = State()
        add_service_photo = State()

        # Удаление услуги мастера
        remove_service_select = State()

        # Удаление мастера
        delete_master = State()

        # Конфигурирование графика
        configure_schedule_select_master = State()  # выбор мастера
        configure_schedule_action = State()  # выбор «ред./просмотр»
        configure_schedule_edit = State()  # inline-редактирование

    class Broadcast(StatesGroup):
        """Управление рассылкой"""
        start_broadcast = State()
