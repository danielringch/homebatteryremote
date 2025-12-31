from collections.abc import Collection
from ...core import OperationMode, app_state, SCHEDULE_TEMPLATE_LENGTH
from .modeltypes import BindableValue

class TemplateRow:
    def __init__(self):
        self.hour = BindableValue('')
        self.mode = BindableValue('')

class TemplateModel:
    def __init__(self, id: str):
        self.__id = id

        self.is_dirty = BindableValue(False)

        self.template = [TemplateRow() for _ in range(SCHEDULE_TEMPLATE_LENGTH)]

        app_state.data.template.on_change.subscribe(self.refresh, id=id)
        self.refresh()

    def destroy(self):
        app_state.data.template.on_change.unsubscribe_by_id(self.__id)

    def refresh(self, _ = None):
        if self.is_dirty.value:
            return
        
        raw_template: Collection[OperationMode] = app_state.data.template.value
        assert len(raw_template) == SCHEDULE_TEMPLATE_LENGTH
        previous_mode = None

        for i in range(SCHEDULE_TEMPLATE_LENGTH):
            self.template[i].hour.set(f'{(i / 4):.2f}')

            mode = raw_template[i].value
            self.template[i].mode.set(None if (mode == previous_mode) else mode)
            previous_mode = mode

    def write_template(self):
        template: list[OperationMode] = []

        previous_mode = None
        for row in self.template:
            mode = OperationMode(row.mode.value or previous_mode or OperationMode.IDLE.value)
            previous_mode = mode.value
            template.append(mode)

        app_state.data.template.set(template)
        app_state.save()
        self.is_dirty.set(False)
        # a manual refresh call sanitizes the toggles
        self.refresh()
