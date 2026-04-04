from dataclasses import dataclass
from datetime import datetime, timedelta
import logging, secrets
from argon2.exceptions import VerifyMismatchError
from fastapi import Request
from fastapi.responses import RedirectResponse

from nicegui import app, ui

from ..core import app_state, password_hasher

HOME_PATH = '/'
LOGIN_PATH = '/login'

COOKIE_MAX_AGE = 3600 * 24 * 30

@dataclass
class PendingLogin:
    one_time_password: str
    user: str
    session_id: str
    valid_until: datetime

@dataclass
class DoneLogin:
    user: str
    session_id: str
    valid_until: datetime

session_id_key: str = None
logins_by_session_id: dict[str, DoneLogin] = {}
pending_logins_by_otp: dict[str, PendingLogin] = {}

def init():
    global session_id_key
    session_id_key = 'hbre_session_id_' + app_state.data.instance_name.value

def get_session_id(request: Request):
    return request.cookies.get(session_id_key)

def check_login(request: Request, redirect_on_fail = True):
    session_id = request.cookies.get(session_id_key)
    done_login = logins_by_session_id.get(session_id)

    user_name = None
    if not done_login:
        pass
    elif done_login.valid_until < datetime.now():
        del logins_by_session_id[session_id]
    else:
        user_name = done_login.user

    if (not user_name) and redirect_on_fail:
        ui.navigate.to(LOGIN_PATH)
    return user_name

@app.get('/do-login')
def do_login(token: str):
    now = datetime.now()
    pending_login = pending_logins_by_otp.pop(token, None)
    if (not pending_login) or (pending_login.valid_until < now):
        return RedirectResponse(LOGIN_PATH)

    logins_by_session_id[pending_login.session_id] = DoneLogin(
        user=pending_login.user,
        session_id=pending_login.session_id,
        valid_until=now + timedelta(seconds=COOKIE_MAX_AGE))
    
    response = RedirectResponse(HOME_PATH)
    response.set_cookie(
        key=session_id_key, 
        value=pending_login.session_id,
        max_age=COOKIE_MAX_AGE,
        httponly=True,
        #secure=True,
        samesite='lax')
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

        pending_login = PendingLogin(
            one_time_password=secrets.token_urlsafe(24),
            user=username.value,
            session_id=secrets.token_urlsafe(32),
            valid_until=(datetime.now() + timedelta(minutes=1)))
        pending_logins_by_otp[pending_login.one_time_password] = pending_login

        ui.navigate.to(f'/do-login?token={pending_login.one_time_password}')

    if check_login(request, redirect_on_fail=False):
        ui.navigate.to(HOME_PATH)

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
