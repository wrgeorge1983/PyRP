from src.cli.pyrp_monitor_app import PyrpMonitor

# route_entries = [
#     ("prefix", "next_hop", "route_source", "admin_distance", "status", "last_updated"),
#     ("192.168.0.0/16", "192.168.1.1", "STATIC", 1, "up", "N/A"),
#     # Add more entries as needed...
# ]


if __name__ == "__main__":
    app = PyrpMonitor()
    app.run()
