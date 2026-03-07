from functools import partial
from nicegui import ui, events

from ...core import OperationMode, app_state
from ..helper.cardwidth import SYNC_WIDTH_CARD_CLASS, sync_card_widths
from ..models.homemodel import HomeModel
from ..singletons import singletons

_AVAILABLE_MODES = {
    None: '(deactivated)',
    OperationMode.PROTECT: 'protect',
    OperationMode.IDLE: 'idle',
    OperationMode.CHARGE:  'charge',
    OperationMode.DISCHARGE: 'discharge'}

def create_home_tab(data: HomeModel):
    system = singletons.virtual_controller

    ui.add_css('''
        .full-width-expansion .q-expansion-item__content[style*="display: none"] {
            display: block !important;
            height: 0 !important;
            overflow: hidden !important;
            visibility: hidden !important;
        }''')

    with ui.column().classes('items-center w-full gap-4'):
        ui.label(app_state.data.instance_name.value).classes('text-h6')

        with ui.card().classes(SYNC_WIDTH_CARD_CLASS):
            ui.label('Requested mode')
            ui.label().bind_text_from(data.requested_mode, 'value')

        for name in system.controllers:
            controller_state = data.controller_states[name]

            with ui.card().classes(SYNC_WIDTH_CARD_CLASS):
                ui.label(f'Controller {name}')
                with ui.grid(columns=2):
                    ui.label('Mode control type')
                    ui.label().bind_text_from(controller_state.mode_control_type, 'value')

                    ui.label('Actual mode')
                    ui.label().bind_text_from(controller_state.mode_actual, 'value')

                    ui.label('Locks')
                    ui.label().bind_text_from(controller_state.locks, 'value')

        if system.mode_settable_controllers:
            with ui.card().classes(SYNC_WIDTH_CARD_CLASS):
                with ui.expansion('Manual mode control').classes('full-width-expansion'):
                    ui.toggle(_AVAILABLE_MODES, on_change=manual_mode_changed_handler).bind_value_from(data.manual_mode, 'value')
    
        if system.resettable_controllers:
            with ui.card().classes(SYNC_WIDTH_CARD_CLASS):
                with ui.expansion('Reset', icon='refresh').classes('full-width-expansion'):
                    for name in sorted(system.resettable_controllers):
                        ui.button(f'Reset {name}', on_click=partial(reset_clicked_handler, name))
                    if len(system.resettable_controllers) > 1:
                        ui.button('Reset all controllers', on_click=reset_clicked_handler)

    sync_card_widths()

def manual_mode_changed_handler(args: events.ValueChangeEventArguments):
    app_state.data.manual_mode.set(args.value)
    app_state.save()

def reset_clicked_handler(controller_name: str | None = None):
    singletons.virtual_controller.send_reset(controller_name)
    ui.notify('Reset command sent.', position='top')
