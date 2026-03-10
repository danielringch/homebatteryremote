import logging
from fastapi import Request
from functools import partial
from nicegui import app, ui, Client
from typing import Any

from ..core import get_config_key, WEB_CONFIG_KEY, app_state
from .login import create_login_page, logout, HOME_PATH, LOGIN_PATH, get_session_id, get_current_user
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

models_by_instance_id: dict[str, Any] = {}

class Gui:
    def __init__(self, config: dict):
        self.__host = get_config_key(config, str, _LISTEN_ENV_NAME, WEB_CONFIG_KEY, _LISTEN_CONFIG_KEY)
        self.__port = get_config_key(config, int, _PORT_ENV_NAME, WEB_CONFIG_KEY, _PORT_CONFIG_KEY)

        @ui.page(LOGIN_PATH)
        def login_page(request: Request):
            instance_id = ui.context.client.id
            logging.debug(f'instance_id={instance_id} created as login page.')
            models_by_instance_id[instance_id] = FakeModel()
            create_login_page(request)
        
        @ui.page(HOME_PATH)
        def home_page(request: Request):
            create_page(_HOME_NAME, request)

        @ui.page(_SCHEDULE_PATH)
        def schedule_page(request: Request):
            create_page(_SCHEDULE_NAME, request)

        @ui.page(_TEMPLATE_PATH)
        def template_page(request: Request):
            create_page(_TEMPLATE_NAME, request)

        @ui.page(_SETTINGS_PATH)
        def settings_page(request: Request):
            create_page(_SETTINGS_NAME, request)

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
        
def create_page(tab_name: str, request: Request):
    user_name = get_current_user(request)
    if not user_name:
        ui.navigate.to(LOGIN_PATH)
        return
    try:
        is_admin = user_name == app_state.data.admin_user.value
    except:
        is_admin = False

    instance_id = ui.context.client.id
    if (old_model := models_by_instance_id.get(instance_id)):
        logging.warning(f'instance_id={instance_id} was reused.')
        old_model.destroy()
    logging.debug(f'Create page "{tab_name}" for instance_id={instance_id}')

    with ui.header().classes(replace='row items-center justify-center gap-2'):
        create_navigation_button(_HOME_NAME, HOME_PATH, tab_name)
        create_navigation_button(_SCHEDULE_NAME, _SCHEDULE_PATH, tab_name)
        create_navigation_button(_TEMPLATE_NAME, _TEMPLATE_PATH, tab_name)
        if is_admin:
            create_navigation_button(_SETTINGS_NAME, _SETTINGS_PATH, tab_name)
        ui.button(_LOGOUT_NAME, on_click=partial(logout, get_session_id(request))).props('flat').classes('text-white')

    # Route to the appropriate content based on the tab_name
    with ui.column().classes('w-full p-4'):
        if tab_name == _HOME_NAME:
            model = HomeModel(instance_id)
            create_home_tab(model)
        elif tab_name == _SCHEDULE_NAME:
            model = ScheduleModel(instance_id)
            create_schedule_tab(model)
        elif tab_name == _TEMPLATE_NAME:
            model = TemplateModel(instance_id)
            create_template_tab(model)
        elif tab_name == _SETTINGS_NAME and is_admin:
            model = SettingsModel(instance_id)
            create_settings_tab(model)
        else:
            model = FakeModel()
            ui.label('Access denied or invalid page.')
    models_by_instance_id[instance_id] = model

def destroy_cliend(client: Client):
    instance_id = client.id
    old_model = models_by_instance_id.pop(instance_id, None)
    if not old_model:
        logging.warning(f'instance_id={instance_id} was double deleted.')
        return
    old_model.destroy()
    logging.debug(f'instance_id={instance_id} deleted.')

def on_exception(e: Exception):
    logging.error(f'Exception from gui: {e}')

def create_navigation_button(text: str, path: str, active_tab_text: str):
    color_class = 'text-yellow' if text == active_tab_text else 'text-white'
    return ui.button(text, on_click=lambda: ui.navigate.to(path)).props('flat').classes(color_class)
