import logging
from functools import partial
from nicegui import ui
from ..models.settingsmodel import SettingsModel
from ..login import logout_all

def create_settings_tab(data: SettingsModel):

    with ui.card():
        ui.label('Device efficiency')
        charger_eta = ui.number(label='Charger', min=1, max=100, precision=1, step=0.1, suffix='%').bind_value(data.charger_eta, 'value')
        inverter_eta = ui.number(label='Inverter', min=1, max=100, precision=1, step=0.1, suffix='%').bind_value(data.inverter_eta, 'value')
        charger_eta.set_enabled(data.is_charger_eta_enabled)
        inverter_eta.set_enabled(data.is_inverter_eta_enabled)
        ui.button('Save', on_click=partial(save_eta_handler, data)).set_enabled(charger_eta.enabled or inverter_eta.enabled)

    with ui.card():
        ui.label('Financials')
        min_margin = ui.number(label='Minimum margin', min=0, max=10000, precision=2, step=0.01, suffix='ct').bind_value(data.min_margin, 'value')
        min_margin.set_enabled(data.is_min_margin_enabled)
        ui.button('Save', on_click=partial(save_financials_handler, data)).set_enabled(min_margin.enabled)

    with ui.card():
        ui.label('Override average charged price')
        ui.number(label='Average charged price', min=-10000, max=10000, precision=8, step=0.01, suffix='ct').bind_value(data.avg_charged_price, 'value')
        ui.button('Save', on_click=partial(save_avg_charged_price_handler, data))

    with ui.card():
        ui.label('Tibber')
        tibber_token = ui.input(label='Token').bind_value(data.tibber_token, 'value')
        tibber_token.set_enabled(data.is_tibber_token_enabled)
        ui.button('Save', on_click=partial(save_tibber_token_handler, data)).set_enabled(tibber_token.enabled)

    with ui.card():
        ui.label('Non-admin credentials')
        user_user = ui.input(label='User name').bind_value(data.user_user, 'value')
        user_pass = ui.input(label='Password', password=True, password_toggle_button=True).bind_value(data.user_pass, 'value')
        user_pass_confirm = ui.input(label='Confirm password', password=True, password_toggle_button=True).bind_value(data.user_pass_confirm, 'value')
        user_user.set_enabled(data.is_user_user_enabled)
        user_pass.set_enabled(data.is_user_pass_enabled)
        user_pass_confirm.set_enabled(data.is_user_pass_enabled)
        ui.button('Save & Logout', on_click=partial(save_user_credentials, data)).set_enabled(user_user.enabled or user_pass.enabled)

    with ui.card():
        ui.label('Admin credentials')
        admin_user = ui.input(label='User name').bind_value(data.admin_user, 'value')
        admin_pass_old = ui.input(label='Old password', password=True, password_toggle_button=True).bind_value(data.admin_pass_old, 'value')
        admin_pass = ui.input(label='Password', password=True, password_toggle_button=True).bind_value(data.admin_pass, 'value')
        admin_pass_confirm = ui.input(label='Conform password', password=True, password_toggle_button=True).bind_value(data.admin_pass_confirm, 'value')
        admin_user.set_enabled(data.is_admin_user_enabled)
        admin_pass_old.set_enabled(data.is_admin_pass_enabled)
        admin_pass.set_enabled(data.is_admin_pass_enabled)
        admin_pass_confirm.set_enabled(data.is_admin_pass_enabled)
        ui.button('Save & Logout', on_click=partial(save_admin_credentials, data)).set_enabled(admin_user.enabled or admin_pass.enabled)

    with ui.card():
        ui.label('Reset')
        ui.button('Logout all users', on_click=logout_all)

def save_eta_handler(data: SettingsModel):
    data.write_eta()
    ui.notify('Value(s) saved.', position='top')

def save_financials_handler(data: SettingsModel):
    data.write_financials()
    ui.notify('Value(s) saved.', position='top')

def save_avg_charged_price_handler(data: SettingsModel):
    data.write_avg_charged_price()
    ui.notify('Value(s) saved.', position='top')

def save_tibber_token_handler(data: SettingsModel):
    try:
        data.write_tibber_token()
        ui.notify('Value(s) saved.', position='top')
    except Exception as e:
        logging.warning(f'Saving tibber token failed: {e}')
        ui.notify('Invalid value.', color='negative', position='top')

def save_user_credentials(data: SettingsModel):
    try:
        data.write_user_credentials()
        logout_all()
    except Exception as e:
        logging.warning(f'Saving user credentials failed: {e}')
        ui.notify(f'{e}', color='negative', position='top')

def save_admin_credentials(data: SettingsModel):
    try:
        data.write_admin_credentials()
        logout_all()
    except Exception as e:
        logging.warning(f'Saving admin credentials failed: {e}')
        ui.notify(f'{e}', color='negative', position='top')
