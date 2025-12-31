from functools import partial
from nicegui import ui, events

from ...core import OperationMode
from ..models.templatemodel import TemplateModel, TemplateRow

_TABLE_HEADER_CELL_CLASS = 'place-content-center text-center px-2 font-bold'
_TABLE_CELL_CLASS = 'place-content-center text-center px-1'

_AVAILABLE_MODES = {
    None: '(no change)',
    OperationMode.CHARGE.value: 'charge',
    OperationMode.IDLE.value: 'idle',
    OperationMode.DISCHARGE.value: 'discharge'}

def create_template_tab(data: TemplateModel):
    with ui.grid(columns='auto auto').classes('gap-0'):

        ui.label('Hour').classes(_TABLE_HEADER_CELL_CLASS)
        ui.label('Mode').classes(_TABLE_HEADER_CELL_CLASS)

        for row in data.template:
            ui.label().bind_text_from(row.hour, 'value').classes(_TABLE_CELL_CLASS)

            ui.toggle(_AVAILABLE_MODES, on_change=partial(mode_changed_handler, data, row)) \
                .bind_value_from(row.mode, 'value')

    with ui.row():
        ui.button('Save', on_click=partial(save_click_handler, data)).bind_enabled_from(data.is_dirty, 'value')
        ui.button('Cancel', on_click=partial(cancel_click_handler, data)).bind_enabled_from(data.is_dirty, 'value').classes('ml-10')

def mode_changed_handler(data: TemplateModel, row: TemplateRow, args: events.ValueChangeEventArguments):
    value = args.value
    if value == row.mode.value:
        # this should trigger server side writes, too
        return
    data.is_dirty.set(True)
    row.mode.set(value)

def save_click_handler(data: TemplateModel):
    data.write_template()

def cancel_click_handler(data: TemplateModel):
    # reset dirty flag first; otherwise, refresh would not run
    data.is_dirty.set(False)
    data.refresh()
