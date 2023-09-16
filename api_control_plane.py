import json
from typing import List, Optional, Union, Any

import toml
import uvicorn
from fastapi import FastAPI, HTTPException
from starlette.responses import JSONResponse


from src.control_plane.main import ControlPlane, CP_Spec
from src.config import Config
from src.fp_interface import ForwardingPlane
from src.system import generate_id
from src.generic.rib import Route

BASE_CONFIG = toml.load("config.toml")
CONTROL_PLANE_CONFIG = BASE_CONFIG["control_plane"]

protocol_instances: dict[str, ControlPlane] = dict()


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
    return {"Service": "ControlPlane"}


@app.get("/instances")
def get_instances() -> dict[str, CP_Spec]:
    return {k: v.as_json for k, v in protocol_instances.items()}


@app.get("/instances/{instance_id}")
def get_instance(instance_id: str) -> CP_Spec:
    rslt = protocol_instances.get(instance_id, None)
    if rslt is None:
        raise HTTPException(status_code=404, detail="instance not found")
    return rslt.as_json


@app.post("/instances/new_from_config")
def create_instance_from_config(filename: str):
    config = Config()
    try:
        config.load(filename)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="config file not found")

    instance_id = generate_id()
    protocol_instances[instance_id] = ControlPlane.from_config(config)
    return {"instance_id": instance_id}


@app.delete("/instances/{instance_id}")
def delete_instance(instance_id: str):
    protocol_instances.pop(instance_id, None)
    return {"instance_id": instance_id}


@app.get("/instances/{instance_id}/routes")
def get_routes(instance_id: str):
    instance = protocol_instances.get(instance_id, None)
    if instance is None:
        raise HTTPException(status_code=404, detail="instance not found")
    rslt = [route.as_json for route in instance.rib_routes]
    return rslt


@app.get("/instances/{instance_id}/routes/static")
def get_routes(instance_id: str):
    instance = protocol_instances.get(instance_id, None)
    if instance is None:
        raise HTTPException(status_code=404, detail="instance not found")
    rslt = [route.as_json for route in instance.static_routes]
    return rslt

@app.post("/instances/{instance_id}/routes/rib/refresh")
def refresh_rib(instance_id: str):
    instance = protocol_instances.get(instance_id, None)
    if instance is None:
        raise HTTPException(status_code=404, detail="instance not found")
    instance.refresh_rib()
    return [route.as_json for route in instance.rib_routes]


@app.post("/instances/{instance_id}/rp_sla/evaluate_routes")
def evaluate_routes(instance_id: str):
    instance: ControlPlane = protocol_instances.get(instance_id, None)
    if instance is None:
        raise HTTPException(status_code=404, detail="instance not found")
    instance.rp_sla_evaluate_routes()
    return instance.as_json


@app.get("/instances/{instance_id}/best_routes")
def get_best_routes(instance_id: str):
    instance: ControlPlane = protocol_instances.get(instance_id, None)
    if instance is None:
        raise HTTPException(status_code=404, detail="instance not found")
    rslt = instance.export_routes()
    return [route.as_json for route in rslt]


if __name__ == "__main__":
    uvicorn.run(
        app,
        host=CONTROL_PLANE_CONFIG["listen_address"],
        port=CONTROL_PLANE_CONFIG["listen_port"],
    )
