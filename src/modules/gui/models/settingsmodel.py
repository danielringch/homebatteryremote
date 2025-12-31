from argon2.exceptions import VerifyMismatchError
from decimal import Decimal
from ...core import app_state, password_hasher
from .modeltypes import BridgedValue

_TIBBER_TOKEN_REPLACEMENTS = ('<No token set>', '<Token set>')
_PASS_REPLACEMENT = '<Password hidden>'

class SettingsModel:
    def __init__(self, id: str):
        self.charger_eta = BridgedValue(id, app_state.data.charger_efficiency, self.__print_eta)
        self.is_charger_eta_enabled = not app_state.data.charger_efficiency.is_readonly

        self.inverter_eta = BridgedValue(id, app_state.data.inverter_efficiency, self.__print_eta)
        self.is_inverter_eta_enabled = not app_state.data.inverter_efficiency.is_readonly

        self.min_margin = BridgedValue(id, app_state.data.minimum_margin, self.__print_price)
        self.is_min_margin_enabled = not app_state.data.minimum_margin.is_readonly

        self.avg_charged_price = BridgedValue(id, app_state.data.avg_charged_price, self.__print_price)

        self.tibber_token = BridgedValue(id, app_state.data.tibber_token, self.__print_tibber_token)
        self.is_tibber_token_enabled = not app_state.data.tibber_token.is_readonly

        self.user_user = BridgedValue(id, app_state.data.user_user, self.__print_user)
        self.is_user_user_enabled = not app_state.data.user_user.is_readonly

        self.user_pass = BridgedValue(id, app_state.data.user_pass, self.__print_password)
        self.is_user_pass_enabled = not app_state.data.user_pass.is_readonly

        self.user_pass_confirm = BridgedValue(id, app_state.data.user_pass, self.__print_password)

        self.admin_user = BridgedValue(id, app_state.data.admin_user, self.__print_user)
        self.is_admin_user_enabled = not app_state.data.admin_user.is_readonly

        self.admin_pass_old = BridgedValue(id, app_state.data.admin_pass, self.__print_old_password)

        self.admin_pass = BridgedValue(id, app_state.data.admin_pass, self.__print_password)
        self.is_admin_pass_enabled = not app_state.data.admin_pass.is_readonly

        self.admin_pass_confirm = BridgedValue(id, app_state.data.admin_pass, self.__print_password)

    def destroy(self):
        self.charger_eta.destroy()
        self.inverter_eta.destroy()
        self.min_margin.destroy()
        self.avg_charged_price.destroy()
        self.tibber_token.destroy()
        self.user_user.destroy()
        self.user_pass.destroy()
        self.admin_user.destroy()
        self.admin_pass.destroy()

    def write_eta(self):
        app_state.data.charger_efficiency.set(round(Decimal(self.charger_eta.value / 100), 3))
        app_state.data.inverter_efficiency.set(round(Decimal(self.inverter_eta.value / 100), 3))
        app_state.save()

    def write_financials(self):
        app_state.data.minimum_margin.set(round(Decimal(self.min_margin.value / 100), 4))
        app_state.save()

    def write_avg_charged_price(self):
        app_state.data.avg_charged_price.set(round(Decimal(self.avg_charged_price.value / 100), 10))
        app_state.save()

    def write_tibber_token(self):
        value = self.tibber_token.value
        if value in _TIBBER_TOKEN_REPLACEMENTS:
            raise ValueError()
        app_state.data.tibber_token.set(value or None)
        app_state.save()

    def write_user_credentials(self):
        user = self.user_user.value
        if user == self.admin_user.value:
            raise ValueError('Admin and non-admin user must not have the same user name.')

        app_state.data.user_user.set(self.user_user.value)
        if (password := self.user_pass.value) != _PASS_REPLACEMENT:
            if len(password) < 8:
                raise ValueError('Password must have at least 8 characters.')
            if password != self.user_pass_confirm.value:
                raise ValueError('Password confirmation does not match.')
            hash = password_hasher.hash(password)
            app_state.data.user_pass.set(hash)
        app_state.save()

    def write_admin_credentials(self):
        user = self.admin_user.value
        if user == self.user_user.value:
            raise ValueError('Admin and non-admin user must not have the same user name.')

        app_state.data.admin_user.set(self.admin_user.value)
        if (password := self.admin_pass.value) != _PASS_REPLACEMENT:
            if len(password) < 8:
                raise ValueError('Password must have at least 8 characters.')
            if (old_hash := app_state.data.admin_pass.value):
                try:
                    password_hasher.verify(old_hash, self.admin_pass_old.value)
                except VerifyMismatchError:
                    raise ValueError('Invalid old password.')
            if password != self.admin_pass_confirm.value:
                raise ValueError('Password confirmation does not match.')
            hash = password_hasher.hash(password)
            app_state.data.admin_pass.set(hash)
        app_state.save()
    
    @staticmethod
    def __print_eta(value: Decimal):
        return float(value * 100)
    
    @staticmethod
    def __print_price(value: Decimal):
        return float(value * 100)
    
    @staticmethod
    def __print_tibber_token(value: str):
        return _TIBBER_TOKEN_REPLACEMENTS[int(bool(value))]
    
    @staticmethod
    def __print_user(value: str):
        return value
    
    @staticmethod
    def __print_password(value: str):
        return _PASS_REPLACEMENT
    
    @staticmethod
    def __print_old_password(value: str):
        return ''
    
    