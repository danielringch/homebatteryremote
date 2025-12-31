import logging
from argon2.exceptions import VerifyMismatchError
from fastapi import Request
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware

from nicegui import app, ui

from ..core import app_state, password_hasher

UNRESTRICTED_PAGE_ROUTES = {'/login'}


@app.add_middleware
class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if not app.storage.user.get('authenticated', False):
            if not request.url.path.startswith('/_nicegui') and request.url.path not in UNRESTRICTED_PAGE_ROUTES:
                return RedirectResponse(f'/login?redirect_to={request.url.path}')
        return await call_next(request)

def create_login_page(redirect_to: str = '/'):
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
        ui.navigate.to(redirect_to)

    if app.storage.user.get('authenticated', False):
        return RedirectResponse('/')
    with ui.card().classes('absolute-center'):
        ui.label(app_state.data.instance_name.value)
        username = ui.input('Username').on('keydown.enter', try_login)
        password = ui.input('Password', password=True, password_toggle_button=True).on('keydown.enter', try_login)
        ui.button('Log in', on_click=try_login)
    return None

def logout():
    app.storage.user.clear()
    ui.navigate.to('/login')

def logout_all():
    app.storage.clear()
    ui.navigate.to('/login')
