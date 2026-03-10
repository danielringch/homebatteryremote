import inspect, logging
from argon2.exceptions import VerifyMismatchError
from fastapi import Request
from fastapi.responses import RedirectResponse

from nicegui import app, ui

from ..core import app_state, password_hasher

HOME_PATH = '/'
LOGIN_PATH = '/login'

logins_by_session_id: dict[str, str] = {}

def auth_required(func):
    async def wrapper(request: Request):
        session_id, _ = get_session_and_instance_id(request)
        if session_id not in logins_by_session_id:
            ui.navigate.to(LOGIN_PATH)
        else:
            if inspect.iscoroutinefunction(func):
                return await func(request)
            else:
                return func(request)

    return wrapper

def create_login_page(session_id: str):
    def try_login() -> None:  # local function to avoid passing username and password as arguments
        try:
            if not session_id:
                raise Exception('no session id')

            if username.value == app_state.data.admin_user.value:
                hash = app_state.data.admin_pass.value
            elif username.value == app_state.data.user_user.value:
                hash = app_state.data.user_pass.value
            else:
                raise VerifyMismatchError()
        
            if hash:
                password_hasher.verify(hash, password.value)
        except VerifyMismatchError:
            logging.warning(f'Failed login attempt for user {username.value}.')
            ui.notify('Wrong username or password.', color='negative')
            return
        except Exception as e:
            logging.error(f'Login failed for user {username.value}: {e}')
            ui.notify('Internal error.', color='negative')
            return

        logins_by_session_id[session_id] = username.value
        ui.navigate.to(HOME_PATH)

    if session_id in logins_by_session_id:
        return RedirectResponse(HOME_PATH)

    with ui.card().classes('absolute-center'):
        ui.label(app_state.data.instance_name.value)
        username = ui.input('Username').on('keydown.enter', try_login)
        password = ui.input('Password', password=True, password_toggle_button=True).on('keydown.enter', try_login)
        ui.button('Log in', on_click=try_login)
    return None

def get_session_and_instance_id(request: Request):
    session_id = str(request.session.get('id', ''))
    if not session_id:
        logging.error('Request did not contain an id.')
    instance_id = ui.context.client.id
    return session_id, instance_id

def logout(session_id: str):
    logging.debug(f'session_id={session_id} logged out')
    logins_by_session_id.pop(session_id, None)
    ui.navigate.to(LOGIN_PATH)

def logout_all():
    logging.debug('All users logged out.')
    logins_by_session_id.clear()
    ui.navigate.to(LOGIN_PATH)
