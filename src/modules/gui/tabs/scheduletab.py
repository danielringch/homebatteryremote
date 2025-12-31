from functools import partial
from nicegui import ui, events
from nicegui.binding import bind_from

from ...core import OperationMode
from ..models.schedulemodel import ScheduleModel, ScheduleRow
from ..customelements import colorful_toggle

_TABLE_HEADER_CELL_CLASS = 'place-content-center text-center px-2 font-bold'
_TABLE_CELL_CLASS = 'place-content-center text-center px-1'

_AVAILABLE_MODES = {
    None: '(no change)',
    OperationMode.CHARGE.value: 'charge',
    OperationMode.IDLE.value: 'idle',
    OperationMode.DISCHARGE.value: 'discharge'}

def create_schedule_tab(data: ScheduleModel):
    with ui.card():
        with ui.grid(columns=2):
            ui.label('Remaining capacity')
            ui.label().bind_text_from(data.capacity, 'value')

            ui.label('Average charged price')
            ui.label().bind_text_from(data.avg_price, 'value')

    with ui.grid(columns='auto auto auto auto auto auto').classes('gap-0'):

        ui.label('Timestamp').classes(_TABLE_HEADER_CELL_CLASS)
        ui.label('Mode').classes(_TABLE_HEADER_CELL_CLASS)
        ui.label('Charge Price').classes(_TABLE_HEADER_CELL_CLASS)
        ui.label('Discharge Price').classes(_TABLE_HEADER_CELL_CLASS)
        ui.label('Charge Margin').classes(_TABLE_HEADER_CELL_CLASS)
        ui.label('Battery Margin').classes(_TABLE_HEADER_CELL_CLASS)

        for row in data.schedule:
            ui.label().bind_text_from(row.timestamp, 'value').classes(_TABLE_CELL_CLASS)

            toggle = colorful_toggle(_AVAILABLE_MODES, on_change=partial(mode_changed_handler, data, row)) \
                .bind_value_from(row.mode, 'value')
            bind_from(self_obj=toggle, self_name='background', other_obj=row.color, other_name='value')

            ui.label().bind_text_from(row.charge_price, 'value').classes(_TABLE_CELL_CLASS).style('font-weight: bold')
            ui.label().bind_text_from(row.discharge_price, 'value').classes(_TABLE_CELL_CLASS).style('font-weight: bold')
            ui.label().bind_text_from(row.charge_margin, 'value').classes(_TABLE_CELL_CLASS)
            ui.label().bind_text_from(row.battery_margin, 'value').classes(_TABLE_CELL_CLASS)

    with ui.row():
        ui.button('Save', on_click=partial(save_click_handler, data)).bind_enabled_from(data.is_dirty, 'value')
        ui.button('Cancel', on_click=partial(cancel_click_handler, data)).bind_enabled_from(data.is_dirty, 'value').classes('ml-10')

def mode_changed_handler(data: ScheduleModel, row: ScheduleRow, args: events.ValueChangeEventArguments):
    value = args.value
    if value == row.mode.value:
        # this should trigger server side writes, too
        return
    data.is_dirty.set(True)
    row.mode.set(value)

def color_changed_handler(toggle: ui.toggle, value: str):
    toggle.style(f'background-color: {value}')

def save_click_handler(data: ScheduleModel):
    data.write_schedule()

def cancel_click_handler(data: ScheduleModel):
    # reset dirty flag first; otherwise, refresh would not run
    data.is_dirty.set(False)
    data.refresh()
