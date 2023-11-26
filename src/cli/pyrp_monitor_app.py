from functools import partial

from textual.app import App, ComposeResult
from textual.command import Provider, Hits, Hit
from textual.containers import Container
from textual.widgets import Header, Footer, RichLog, DataTable

from .state import (
    state,
    sla_rib_table_fields,
    http_errors,
    rip_rib_table_fields,
    cp_rib_table_fields,
)
from .TitledTable import LiveTable

commands = {}


def rip_rib_refresh(app: "PyrpMonitor"):
    app.user_log("Refreshing RIP RIB")
    # state.rip_client.refresh_rib("latest")
    app.populate_rip_rib()


def watch_tables(app: "PyrpMonitor"):
    app.user_log("Watching Tables")
    app.start_watch_tables()
    
def stop_watch_tables(app: "PyrpMonitor"):
    app.user_log("Stopped Watching Tables")
    app.stop_watch_tables()

commands["RIP: Refresh RIB"] = rip_rib_refresh
commands["RIP: Watch Tables"] = watch_tables
commands["RIP: Stop Watching Tables"] = stop_watch_tables


class CPCommandPalette(Provider):
    async def search(self, query: str) -> Hits:
        matcher = self.matcher(query)

        app = self.app

        for command, func in commands.items():
            score = matcher.match(command)
            if score > 0:
                yield Hit(score, matcher.highlight(command), partial(func, app))


class PyrpMonitor(App):
    TITLE = "PyRP Monitor"
    CSS_PATH = "layout.tcss"
    BINDINGS = [
        ("d", "toggle_dark", "Toggle Dark Mode"),
        ("q", "quit", "Quit"),
        ("w", "toggle_watch", "Start/Stop Watching Tables"),
        ("ctrl+r", "redistribute", "Trigger Redistribution"),
        ("r", "refresh_tables", "Refresh"),
        ("e", "sla_evaluate", "Evaluate SLA Routes"),
        ("p", "next_proto", "Next Protocol"),
        ("n", "new_instance", "New Instance"),
        ("ctrl+d", "set_log_debug", "Set log level to DEBUG"),
        ("ctrl+n", "set_log_info", "Set log level to INFO"),
        ("ctrl+w", "set_log_warning", "Set log level to WARNING"),
        ("ctrl+e", "set_log_error", "Set log level to ERROR"),
    ]
    COMMANDS = App.COMMANDS | {CPCommandPalette}

    log_level = "INFO"
    _log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()
        with Container(id="app-grid"):
            t = LiveTable(id="CP_RIB", classes="box")
            t.title = "Control Plane RIB"
            t.callback = partial(state.cp_client.get_rib_routes, "latest")
            yield t
            t = LiveTable(id="PROTO_RIB", classes="box")
            t.title = "Protocol RIB"
            yield t
            yield RichLog(id="UserLog", classes="box box-2")

    async def on_mount(self) -> None:
        await self.run_action("next_proto")
        cp_table = self.query_one("#CP_RIB")
        await cp_table.update_data()

    def on_key(self, event):
        self.user_log(f"Key pressed: {event.key}")

    def action_toggle_dark(self) -> None:
        self.dark = not self.dark

    def action_toggle_watch(self) -> None:
        live_tables = self.query("LiveTable")
        on = "ON" if any(table.paused for table in live_tables) else "OFF"  # opposite of what you expect
        self.user_log(f"Toggling Watch {on}")
        for table in live_tables:
            table.paused = not table.paused

    async def action_redistribute(self):
        self.user_log("Triggering Redistribution")
        try:
            await state.cp_client.redistribute("latest")
        except http_errors as e:
            self.user_log(f"Error redistributing: {e}")
        await self.run_action("refresh_tables")

    async def action_sla_evaluate(self):
        self.user_log("Evaluating SLA Routes")
        try:
            await state.sla_client.evaluate_routes("latest")
        except http_errors as e:
            self.user_log(f"Error evaluating routes: {e}")

    async def action_new_instance(self):
        try:
            await state.cp_client.create_instance_from_config(
                "tests/files/configs/main.toml"
            )
        except http_errors as e:
            self.user_log(f"Error creating new instance: {e}")

    async def action_refresh_tables(self):
        self.user_log("Refreshing Tables")
        for live_table in self.query("LiveTable"):
            await live_table.update_data()


    async def action_next_proto(self):
        proto = state.next_proto()
        live_table: LiveTable = self.query_one("#PROTO_RIB")
        if proto == "sla_rib":
            live_table.title = "SLA RIB"
            live_table.callback = partial(state.sla_client.get_rib_routes, "latest")

        elif proto == "rip_rib":
            live_table.title = "RIP RIB"
            live_table.callback = partial(state.rip_client.get_rib_routes, "latest")

        await live_table.update_data()

    async def action_new_instance(self):
        self.user_log("Creating new instance")
        try:
            await state.cp_client.create_instance_from_config(
                "tests/files/configs/main.toml"
            )
        except http_errors as e:
            self.user_log(f"Error creating new instance: {e}")

        await self.run_action("refresh_tables")

    def action_set_log_debug(self):
        self.user_log("Setting log level to DEBUG", "DEBUG")
        self.log_level = "DEBUG"

    def action_set_log_info(self):
        self.user_log("Setting log level to INFO", "DEBUG")
        self.log_level = "INFO"

    def action_set_log_warning(self):
        self.user_log("Setting log level to WARNING", "DEBUG")
        self.log_level = "WARNING"

    def action_set_log_error(self):
        self.user_log("Setting log level to ERROR", "DEBUG")
        self.log_level = "ERROR"

    def user_log(self, message: str, severity='INFO') -> None:
        severity = severity.upper()
        if severity not in self._log_levels:
            raise ValueError(f"Invalid severity: {severity}")
        if self.log_level not in self._log_levels:
            raise ValueError(f"Invalid log level: {self.log_level}")

        if self._log_levels.index(severity) >= self._log_levels.index(self.log_level):
            self.query_one("RichLog").write(f'{severity}: {message}')
