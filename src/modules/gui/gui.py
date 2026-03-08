import logging
from nicegui import app, ui, Client
from typing import Any

from ..core import get_config_key, WEB_CONFIG_KEY, app_state
from .login import auth_required, create_login_page, logout, HOME_PATH, LOGIN_PATH
from .models.homemodel import HomeModel
from .models.schedulemodel import ScheduleModel
from .models.settingsmodel import SettingsModel
from .models.templatemodel import TemplateModel
from .tabs.hometab import create_home_tab
from .tabs.scheduletab import create_schedule_tab
from .tabs.settingstab import create_settings_tab
from .tabs.templatetab import create_template_tab

_LISTEN_CONFIG_KEY = 'listen'
_PORT_CONFIG_KEY = 'port'

_LISTEN_ENV_NAME = 'HBRE_WEB_LISTEN'
_PORT_ENV_NAME = 'HBRE_WEB_PORT'

_HOME_NAME = 'Home'
_SCHEDULE_NAME = 'Schedule'
_TEMPLATE_NAME = 'Template'
_SETTINGS_NAME = 'Settings'
_LOGOUT_NAME = 'Logout'

_SCHEDULE_PATH = '/schedule'
_TEMPLATE_PATH = '/template'
_SETTINGS_PATH = '/settings'

# used for login pages, since they do not have a real model
class FakeModel:
    def destroy(self):
        pass

models_by_client_id: dict[str, Any] = {}

class Gui:
    def __init__(self, config: dict):
        self.__host = get_config_key(config, str, _LISTEN_ENV_NAME, WEB_CONFIG_KEY, _LISTEN_CONFIG_KEY)
        self.__port = get_config_key(config, int, _PORT_ENV_NAME, WEB_CONFIG_KEY, _PORT_CONFIG_KEY)

        @ui.page(LOGIN_PATH)
        def login_page():
            client_id = ui.context.client.id
            logging.debug(f'Client {client_id} created as login page.')
            models_by_client_id[client_id] = FakeModel()
            create_login_page()
        
        @ui.page(HOME_PATH)
        @auth_required
        def home_page():
            create_page(_HOME_NAME)

        @ui.page(_SCHEDULE_PATH)
        @auth_required
        def schedule_page():
            create_page(_SCHEDULE_NAME)

        @ui.page(_TEMPLATE_PATH)
        @auth_required
        def template_page():
            create_page(_TEMPLATE_NAME)

        @ui.page(_SETTINGS_PATH)
        @auth_required
        def settings_page():
            create_page(_SETTINGS_NAME)

    def run(self, storage_secret: str, startup_callback):
        app.on_startup(startup_callback)
        app.on_delete(destroy_cliend)
        app.on_exception(on_exception)
        ui.run(
            storage_secret=storage_secret,
            host=self.__host,
            port=self.__port,
            reload=False,
            title='Homebattery Remote',
            favicon=chr(0x1F50B),
            binding_refresh_interval=None,
            show=False)
        
def create_page(tab_name: str):
    client_id = ui.context.client.id
    
    if (old_model := models_by_client_id.get(client_id)):
        logging.warning(f'Client {client_id} was reused.')
        old_model.destroy()
    logging.debug(f'Create page "{tab_name}" for client {client_id}')

    try:
        is_admin = app.storage.user.get('username') == app_state.data.admin_user.value
    except:
        is_admin = False

    with ui.header().classes(replace='row items-center justify-center gap-2'):
        create_navigation_button(_HOME_NAME, HOME_PATH, tab_name)
        create_navigation_button(_SCHEDULE_NAME, _SCHEDULE_PATH, tab_name)
        create_navigation_button(_TEMPLATE_NAME, _TEMPLATE_PATH, tab_name)
        if is_admin:
            create_navigation_button(_SETTINGS_NAME, _SETTINGS_PATH, tab_name)
        ui.button(_LOGOUT_NAME, on_click=logout).props('flat').classes('text-white')

    # Route to the appropriate content based on the tab_name
    with ui.column().classes('w-full p-4'):
        if tab_name == _HOME_NAME:
            model = HomeModel(client_id)
            create_home_tab(model)
        elif tab_name == _SCHEDULE_NAME:
            model = ScheduleModel(client_id)
            create_schedule_tab(model)
        elif tab_name == _TEMPLATE_NAME:
            model = TemplateModel(client_id)
            create_template_tab(model)
        elif tab_name == _SETTINGS_NAME and is_admin:
            model = SettingsModel(client_id)
            create_settings_tab(model)
        else:
            model = FakeModel()
            ui.label('Access denied or invalid page.')
    models_by_client_id[client_id] = model

def destroy_cliend(client: Client):
    old_model = models_by_client_id.pop(client.id, None)
    if not old_model:
        logging.warning(f'Client {client.id} was double deleted.')
        return
    old_model.destroy()
    logging.debug(f'Client {client.id} deleted.')

def on_exception(e: Exception):
    logging.error(f'Exception from gui: {e}')

def create_navigation_button(text: str, path: str, active_tab_text: str):
    color_class = 'text-yellow' if text == active_tab_text else 'text-white'
    return ui.button(text, on_click=lambda: ui.navigate.to(path)).props('flat').classes(color_class)
