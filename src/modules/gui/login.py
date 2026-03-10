import logging, secrets
from argon2.exceptions import VerifyMismatchError
from fastapi import Request
from fastapi.responses import RedirectResponse

from nicegui import app, ui

from ..core import app_state, password_hasher

HOME_PATH = '/'
LOGIN_PATH = '/login'

SESSION_ID_KEY = 'hbre_session_id'
COOKIE_MAX_AGE = 3600 * 24 * 30

logins_by_session_id: dict[str, str] = {}
pending_logins: dict[str, str] = {} # otp: session_id

def get_current_user(request: Request):
    session_id = request.cookies.get(SESSION_ID_KEY)
    return logins_by_session_id.get(session_id)

def get_session_id(request: Request):
    return request.cookies.get(SESSION_ID_KEY)

@app.get('/do-login')
def do_login(token: str):
    session_id = pending_logins.pop(token, None)
    if not session_id:
        return RedirectResponse(LOGIN_PATH)
    response = RedirectResponse(HOME_PATH)
    response.set_cookie(
        key=SESSION_ID_KEY, 
        value=session_id,
        max_age=COOKIE_MAX_AGE,
        httponly=True,
        #secure=True,
        samesite='lax'
    )
    return response

def create_login_page(request: Request):
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

        otp = secrets.token_urlsafe(24)
        new_session_id = secrets.token_urlsafe(32)
        logins_by_session_id[new_session_id] = username.value
        pending_logins[otp] = new_session_id

        ui.navigate.to(f'/do-login?token={otp}')

    if get_current_user(request):
        return RedirectResponse(HOME_PATH)

    with ui.card().classes('absolute-center'):
        ui.label(app_state.data.instance_name.value)
        username = ui.input('Username').on('keydown.enter', try_login)
        password = ui.input('Password', password=True, password_toggle_button=True).on('keydown.enter', try_login)
        ui.button('Log in', on_click=try_login)

def logout(session_id: str):
    logging.debug(f'session_id={session_id} logged out')
    logins_by_session_id.pop(session_id, None)
    ui.navigate.to(LOGIN_PATH)

def logout_all():
    logging.debug('All users logged out.')
    logins_by_session_id.clear()
    ui.navigate.to(LOGIN_PATH)
