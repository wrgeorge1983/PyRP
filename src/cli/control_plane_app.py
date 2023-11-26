from functools import partial

from textual.app import App, ComposeResult
from textual.command import Provider, Hits, Hit
from textual.containers import Container
from textual.widgets import Header, Footer, RichLog, DataTable

from .cli import (
    state,
    sla_rib_table_fields,
    http_errors,
    rip_rib_table_fields,
    cp_rib_table_fields,
)
from .TitledTable import TitledTable



commands = {}


def rip_rib_refresh(app: "ControlPlaneApp"):
    app.user_log("Refreshing RIP RIB")
    # state.rip_client.refresh_rib("latest")
    app.populate_rip_rib()


def watch_tables(app: "ControlPlaneApp"):
    app.user_log("Watching Tables")
    app.start_watch_tables()
    
def stop_watch_tables(app: "ControlPlaneApp"):
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


class ControlPlaneApp(App):
    CSS_PATH = "layout.tcss"
    BINDINGS = [
        ("d", "toggle_dark", "Toggle Dark Mode"),
        ("q", "quit", "Quit"),
        ("ctrl+r", "redistribute", "Trigger Redistribution"),
        ("r", "refresh", "Refresh"),
        ("e", "sla_evaluate", "Evaluate SLA Routes"),
        ("p", "next_proto", "Next Protocol"),
        ("n", "new_instance", "New Instance"),
    ]
    COMMANDS = App.COMMANDS | {CPCommandPalette}

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()
        with Container(id="app-grid"):
            t = TitledTable(id="CP_RIB", classes="table")
            t.label = "CP RIB"
            yield t
            t = TitledTable(id="PROTO_RIB", classes="table")
            t.label = "PROTO RIB"
            yield t
            # yield DataTable(id="CP_RIB", classes="table")
            # yield DataTable(id="PROTO_RIB", classes="table")
            yield RichLog(id="UserLog")

    def action_toggle_dark(self) -> None:
        self.dark = not self.dark

    async def populate_proto_rib(self):
        if state.proto_table == "sla_rib":
            await self.populate_sla_rib()
        elif state.proto_table == "rip_rib":
            await self.populate_rip_rib()

    async def populate_sla_rib(self):
        self.user_log("Fetching SLA RIB")
        container = self.query_one("#PROTO_RIB")
        container.label = "SLA RIB"
        data_table: DataTable = self.query_one("#PROTO_RIB_table")
        data_table.clear(True)
        data_table.add_columns(*sla_rib_table_fields)
        try:
            data_table.add_rows(await state.get_sla_rib_entries())
        except http_errors as e:
            self.user_log(f"Error fetching SLA RIB: {e}")

    async def populate_rip_rib(self):
        self.user_log("Fetching RIP RIB")
        container = self.query_one("#PROTO_RIB")
        container.label = "RIP RIB"
        data_table: DataTable = self.query_one("#PROTO_RIB_table")
        data_table.clear(True)
        data_table.add_columns(*rip_rib_table_fields)
        try:
            data_table.add_rows(await state.get_rip_rib_entries())
        except http_errors as e:
            self.user_log(f"Error fetching RIP RIB: {e}")

    async def populate_cp_rib(self):
        table: DataTable = self.query_one("#CP_RIB_table")
        table.clear(True)
        table.add_columns(*cp_rib_table_fields)
        try:
            table.add_rows(await state.get_cp_rib_entries())
        except http_errors as e:
            self.user_log(f"Error fetching CP RIB: {e}")

    async def on_mount(self) -> None:
        await self.populate_cp_rib()
        await self.populate_proto_rib()

    async def action_redistribute(self):
        try:
            await state.cp_client.redistribute("latest")
        except http_errors as e:
            self.user_log(f"Error redistributing: {e}")

        await self.populate_cp_rib()
        await self.populate_proto_rib()

    async def action_sla_evaluate(self):
        try:
            await state.sla_client.evaluate_routes("latest")
        except http_errors as e:
            self.user_log(f"Error evaluating routes: {e}")

        await self.populate_proto_rib()

    def clear_all(self):
        self.query_one("#UserLog").clear()
        self.query_one("#CP_RIB_table").clear()
        self.query_one("#PROTO_RIB_table").clear()

    async def refresh_tables(self):
        await self.populate_cp_rib()
        await self.populate_proto_rib()

    async def action_refresh(self):
        self.clear_all()
        await self.populate_cp_rib()
        await self.populate_proto_rib()

    async def action_next_proto(self):
        state.next_proto()
        await self.populate_proto_rib()
        # self.refresh()

    async def action_new_instance(self):
        try:
            await state.cp_client.create_instance_from_config(
                "tests/files/configs/main.toml"
            )
        except http_errors as e:
            self.user_log(f"Error creating new instance: {e}")

    def user_log(self, message: str) -> None:
        self.query_one("RichLog").write(message)
