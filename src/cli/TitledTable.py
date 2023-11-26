from datetime import datetime
from typing import Callable, Optional

from textual.app import ComposeResult
from textual.reactive import Reactive
from textual.widgets import Static, Label, DataTable

from .state import http_errors


class LiveTable(Static):
    title = Reactive("NO TITLE")
    data: Reactive[list[dict]] = Reactive([])
    callback: Reactive[Optional[Callable[[], list[dict]]]] = Reactive(
        None
    )  # default do-nothing callback
    paused = Reactive(True)

    def on_mount(self):
        self.update_timer = self.set_interval(1, self.update_data, pause=True)

    async def update_data(self):
        self.app.user_log(f"Updating {self.title} data", "DEBUG")
        if self.callback is None:
            return
        try:
            self.data = await self.callback()
        except http_errors as e:
            self.app.user_log(f"HTTP Error updating {self.title} data: {e}", "ERROR")

    def watch_data(self, data):
        table = self.query_one(f"#{self.id}_table")
        table.clear(True)
        if len(data) == 0:
            return

        def fix_timestamps(item):
            """Converts timestamps (floats) to human-readable strings"""
            ts = item["last_updated"]
            if isinstance(ts, float):
                item["last_updated"] = datetime.fromtimestamp(ts).strftime(
                    "%H:%M:%S"
                )
            return item

        for item in data:
            fix_timestamps(item)

        header = data[0].keys()
        table.add_columns(*header)
        table.add_rows(item.values() for item in data)

    def watch_paused(self, paused):
        if paused:
            self.app.user_log(f"Pausing {self.title} data", "DEBUG")
            self.update_timer.pause()
        else:
            self.app.user_log(f"Resuming {self.title} data", "DEBUG")
            self.update_timer.resume()

    def compose(self) -> ComposeResult:
        yield DataTable(id=f"{self.id}_table", classes="richtable")

    def watch_title(self, title: str):
        self.border_title = title
