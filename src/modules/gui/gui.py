import logging
from dataclasses import dataclass
from nicegui import app, ui, Client

from ..core import get_config_key, WEB_CONFIG_KEY, app_state
from .login import create_login_page, logout, HOME_PATH, LOGIN_PATH
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

# used for login pages, since they do not have real instance data
class FakeInstanceData:
    def destroy(self):
        pass

@dataclass
class InstanceData:
    home: HomeModel
    schedule: ScheduleModel
    settings: SettingsModel
    template: TemplateModel

    def destroy(self):
        self.home.destroy()
        self.schedule.destroy()
        self.settings.destroy()
        self.template.destroy()

instances: dict[str, InstanceData] = {}

class Gui:
    def __init__(self, config: dict):
        self.__host = get_config_key(config, str, _LISTEN_ENV_NAME, WEB_CONFIG_KEY, _LISTEN_CONFIG_KEY)
        self.__port = get_config_key(config, int, _PORT_ENV_NAME, WEB_CONFIG_KEY, _PORT_CONFIG_KEY)

        @ui.page(LOGIN_PATH)
        def login_page():
            client_id = ui.context.client.id
            logging.debug(f'Client {client_id} created as login page.')
            instances[client_id] = FakeInstanceData()
            create_login_page()
        
        @ui.page(HOME_PATH)
        def home_page():
            create_page(_HOME_NAME)

        @ui.page(_SCHEDULE_PATH)
        def schedule_page():
            create_page(_SCHEDULE_NAME)

        @ui.page(_TEMPLATE_PATH)
        def template_page():
            create_page(_TEMPLATE_NAME)

        @ui.page(_SETTINGS_PATH)
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

    data = InstanceData(
        home=HomeModel(client_id),
        schedule=ScheduleModel(client_id),
        settings=SettingsModel(client_id),
        template=TemplateModel(client_id))
    
    if (old_instance := instances.get(client_id)):
        logging.error(f'Double creation of client {client_id}')
        old_instance.destroy()
    instances[client_id] = data
    logging.debug(f'Client {client_id} created.')

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
            create_home_tab(data.home)
        elif tab_name == _SCHEDULE_NAME:
            create_schedule_tab(data.schedule)
        elif tab_name == _TEMPLATE_NAME:
            create_template_tab(data.template)
        elif tab_name == _SETTINGS_NAME and is_admin:
            create_settings_tab(data.settings)
        else:
            ui.label('Access denied or invalid page.')

def destroy_cliend(client: Client):
    old_instance = instances.pop(client.id, None)
    if not old_instance:
        logging.warning(f'Client {client.id} was double deleted.')
        return
    old_instance.destroy()
    logging.debug(f'Client {client.id} deleted.')

def on_exception(e: Exception):
    logging.error(f'Exception from gui: {e}')

def create_navigation_button(text: str, path: str, active_tab_text: str):
    color_class = 'text-yellow' if text == active_tab_text else 'text-white'
    return ui.button(text, on_click=lambda: ui.navigate.to(path)).props('flat').classes(color_class)
