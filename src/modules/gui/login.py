import inspect, logging
from argon2.exceptions import VerifyMismatchError
from fastapi.responses import RedirectResponse
from functools import wraps

from nicegui import app, ui

from ..core import app_state, password_hasher

HOME_PATH = '/'
LOGIN_PATH = '/login'

def auth_required(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        if not app.storage.user.get('authenticated', False):
            ui.navigate.to(LOGIN_PATH)
            return

        if inspect.iscoroutinefunction(func):
            return await func(*args, **kwargs)
        else:
            return func(*args, **kwargs)

    return wrapper

def create_login_page():
    def try_login() -> None:  # local function to avoid passing username and password as arguments
        try:
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

        app.storage.user.update({'username': username.value, 'authenticated': True})
        ui.navigate.to(HOME_PATH)

    if app.storage.user.get('authenticated', False):
        return RedirectResponse(HOME_PATH)
    with ui.card().classes('absolute-center'):
        ui.label(app_state.data.instance_name.value)
        username = ui.input('Username').on('keydown.enter', try_login)
        password = ui.input('Password', password=True, password_toggle_button=True).on('keydown.enter', try_login)
        ui.button('Log in', on_click=try_login)
    return None

def logout():
    app.storage.user.clear()
    ui.navigate.to(LOGIN_PATH)

def logout_all():
    app.storage.clear()
    ui.navigate.to(LOGIN_PATH)
