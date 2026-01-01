import logging
from dataclasses import dataclass
from nicegui import app, ui, Client

from ..core import get_config_key, WEB_CONFIG_KEY, app_state
from .login import AuthMiddleware, create_login_page, logout, MAIN_PATH, LOGIN_PATH
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

        @ui.page(MAIN_PATH)
        def main_page():
            create_main_page()

        @ui.page(LOGIN_PATH)
        def login():
            client_id = ui.context.client.id
            logging.debug(f'Client {client_id} created as login page.')
            instances[client_id] = FakeInstanceData()
            create_login_page()

    def run(self, storage_secret: str, startup_callback):
        app.on_startup(startup_callback)
        app.on_delete(destroy_cliend)
        ui.run(
            storage_secret=storage_secret,
            host=self.__host,
            port=self.__port,
            reload=False,
            title='Homebattery Remote',
            favicon=None,
            binding_refresh_interval=None,
            show=False)
        
def destroy_cliend(client: Client):
    old_instance = instances.pop(client.id, None)
    if not old_instance:
        logging.warning(f'Client {client.id} was double deleted.')
        return
    old_instance.destroy()
    logging.debug(f'Client {client.id} deleted.')
    
def create_main_page():
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

    with ui.header().classes(replace='row items-center') as header:
        with ui.tabs() as tabs:
            ui.tab(_HOME_NAME)
            ui.tab(_SCHEDULE_NAME)
            ui.tab(_TEMPLATE_NAME)
            if is_admin:
                ui.tab(_SETTINGS_NAME)
            ui.button(on_click=logout, text=_LOGOUT_NAME)

    with ui.tab_panels(tabs, value=_HOME_NAME).classes('w-full'):
        with ui.tab_panel(_HOME_NAME):
            create_home_tab(data.home)
        with ui.tab_panel(_SCHEDULE_NAME):
            create_schedule_tab(data.schedule)
        with ui.tab_panel(_TEMPLATE_NAME):
            create_template_tab(data.template)
        if is_admin:
            with ui.tab_panel(_SETTINGS_NAME):
                create_settings_tab(data.settings)

