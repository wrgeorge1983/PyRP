from typing import Callable

from textual.app import ComposeResult
from textual.reactive import Reactive
from textual.widgets import Static, Label, DataTable


class TitledTable(Static):
    label = Reactive("None")

    def compose(self) -> ComposeResult:
        label = Label()
        label.update(self.label)
        yield label

        yield DataTable(id=f"{self.id}_table", classes="richtable")

    def watch_label(self, label):
        try:
            self.query_one("Label").update(label)
        except:
            pass


class LiveTitledTable(TitledTable):

    title = Reactive("NO TITLE")
    data: Reactive[list[dict]] = Reactive([])
    callback: Reactive[Callable[[], list[dict]]] = Reactive(lambda: [])  # default do-nothing callback

    def on_mount(self):
        self.update_timer = self.set_interval(1, self.update_data, pause=True)

    def update_data(self):
        self.data = self.callback()

    def watch_data(self, data):
        table = self.query_one(f"#{self.id}_table")
        table.clear(True)

        if len(data) == 0:
            return

        header = data[0].keys()
        table.add_columns(*header)
        table.add_rows(data)

    def start_timer(self):
        self.update_timer.resume()

    def stop_timer(self):
        self.update_timer.pause()

    def compose(self) -> ComposeResult:
        label = Label()
        label.update(self.title)
        yield label
        yield DataTable(id=f"{self.id}_table", classes="richtable")

    def watch_label(self, label):
        try:
            self.query_one("Label").update(label)
        except:
            pass

