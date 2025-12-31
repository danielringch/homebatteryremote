from nicegui import ui
from nicegui.binding import BindableProperty
from nicegui.events import Handler, ValueChangeEventArguments
from typing import Optional, cast
from typing_extensions import Self

class colorful_toggle(ui.toggle):
    background = BindableProperty(
        on_change=lambda sender, value: cast(Self, sender)._handle_background_change(value))

    def __init__(self, text: str = '', on_change: Handler[ValueChangeEventArguments] | None = None):
        super().__init__(text, on_change=on_change)
        self.background: Optional[str] = None

    def _handle_background_change(self, rgb_code: str):
        self.style(f'background-color: {rgb_code}')
