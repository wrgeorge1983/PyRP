import json
from typing import List, Optional, Union, Any

import uvicorn
from fastapi import FastAPI
from starlette.responses import JSONResponse

from src.config import Config
from src.fp_interface import ForwardingPlane
from src.pbasic import RoutingProtocolBasic
from src.system import generate_id, Route

protocol_instances: dict[str, RoutingProtocolBasic] = dict()


def _render_output(output: object):
    if isinstance(output, dict):
        return {k: _render_output(v) for k, v in output.items()}
    if isinstance(output, (list, tuple, set)):
        return [_render_output(v) for v in output]

    if hasattr(output, "json_render"):
        return output.json_render()

    return str(output)


app = FastAPI()


@app.get("/")
def read_root():
    return {"Service": "PBasic"}


@app.get("/instances")
def get_instances():
    return {k: v.as_json for k, v in protocol_instances.items()}


@app.get("/instances/{instance_id}")
def get_instance(instance_id: str):
    rslt = protocol_instances.get(instance_id, None)
    if rslt is None:
        return JSONResponse(status_code=404, content={"error": "instance not found"})
    return rslt.as_json


@app.post("/instances/new")
def create_instance(admin_distance: int = 1, threshold_measure_interval: int = 60):
    instance_id = generate_id()
    fp = ForwardingPlane()
    protocol_instances[instance_id] = RoutingProtocolBasic(
        fp, admin_distance, threshold_measure_interval
    )
    return {"instance_id": instance_id}

@app.post("/instances/new_from_config")
def create_instance_from_config(filename: str):
    config = Config()
    try:
        config.load(filename)
    except FileNotFoundError:
        return JSONResponse(status_code=404, content={"error": "config file not found"})

    instance_id = generate_id()
    fp = ForwardingPlane()
    protocol_instances[instance_id] = RoutingProtocolBasic.from_config(config, fp)
    return {"instance_id": instance_id}


@app.delete("/instances/{instance_id}")
def delete_instance(instance_id: str):
    protocol_instances.pop(instance_id, None)
    return {"instance_id": instance_id}


@app.get("/instances/{instance_id}/routes")
def get_routes(instance_id: str):
    instance = protocol_instances.get(instance_id, None)
    if instance is None:
        return JSONResponse(status_code=404, content={"error": "instance not found"})
    rslt = [route.as_json for route in instance.configured_routes]
    return rslt


@app.post("/instance/{instance_id}/routes/new")
def create_route(
    instance_id: str,
    prefix: str,
    next_hop: str,
    priority: int,
    threshold_ms: int,
):
    instance: RoutingProtocolBasic = protocol_instances.get(instance_id, None)
    if instance is None:
        return JSONResponse(status_code=404, content={"error": "instance not found"})
    basic_route = Route(prefix, next_hop)
    instance.add_configured_route(basic_route, priority, threshold_ms)
    return {prefix: (next_hop, priority, threshold_ms)}


@app.post("/instance/{instance_id}/routes/delete")
def delete_route(
    instance_id: str,
    prefix: str,
    next_hop: str,
):
    instance: RoutingProtocolBasic = protocol_instances.get(instance_id, None)
    if instance is None:
        return JSONResponse(status_code=404, content={"error": "instance not found"})
    basic_route = Route(prefix, next_hop)

    instance.remove_configured_route(basic_route)
    return {prefix: next_hop}


@app.post("/instance/{instance_id}/evaluate_routes")
def evaluate_routes(instance_id: str):
    instance: RoutingProtocolBasic = protocol_instances.get(instance_id, None)
    if instance is None:
        return JSONResponse(status_code=404, content={"error": "instance not found"})
    instance.evaluate_routes()
    return instance.as_json

@app.get("/instance/{instance_id}/best_routes")
def get_best_routes(instance_id: str):
    instance: RoutingProtocolBasic = protocol_instances.get(instance_id, None)
    if instance is None:
        return JSONResponse(status_code=404, content={"error": "instance not found"})
    rslt = instance.export_routes()
    return [route.as_json for route in rslt]


if __name__ == "__main__":
    uvicorn.run(app, host="localhost", port=8000)
