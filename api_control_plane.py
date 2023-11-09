import json
import logging
import os
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

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    handlers=[
        logging.StreamHandler(),
    ],
)

log = logging.getLogger(__name__)

log.info("starting api_control_plane")
log.debug(f"CONTROL_PLANE_CONFIG: {CONTROL_PLANE_CONFIG}")


def _render_output(output: object):
    if isinstance(output, dict):
        return {k: _render_output(v) for k, v in output.items()}
    if isinstance(output, (list, tuple, set)):
        return [_render_output(v) for v in output]

    if hasattr(output, "json_render"):
        return output.json_render()

    return str(output)


LATEST_INSTANCE_ID: Optional[str] = None


def get_protocol_instance(instance_id: str) -> ControlPlane:
    if instance_id == "latest":
        if LATEST_INSTANCE_ID is None:
            raise HTTPException(
                status_code=404, detail="instance not found, 'latest' not set"
            )
        instance_id = LATEST_INSTANCE_ID

    rslt = protocol_instances.get(instance_id, None)
    if rslt is None:
        raise HTTPException(status_code=404, detail=f"instance {instance_id} not found")
    return rslt


app = FastAPI()


@app.get("/")
def read_root():
    return {"Service": "ControlPlane"}


@app.get("/instances")
def get_instances() -> dict[str, CP_Spec]:
    return {k: v.as_json for k, v in protocol_instances.items()}


@app.get("/instances/{instance_id}")
def get_protocol(instance_id: str) -> CP_Spec:
    rslt = get_protocol_instance(instance_id)
    return rslt.as_json


@app.post("/instances/new_from_config")
def create_instance_from_config(filename: str):
    config = Config()
    try:
        config.load(filename)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="config file not found")

    instance_id = generate_id()
    protocol_instances[instance_id] = ControlPlane.from_config(config, instance_id=instance_id)
    global LATEST_INSTANCE_ID
    LATEST_INSTANCE_ID = instance_id
    return {instance_id: protocol_instances[instance_id].as_json}


@app.delete("/instances/{instance_id}")
def delete_instance(instance_id: str):
    global LATEST_INSTANCE_ID
    if instance_id == "latest":
        instance_id = LATEST_INSTANCE_ID
        LATEST_INSTANCE_ID = None

    elif LATEST_INSTANCE_ID == instance_id:
        LATEST_INSTANCE_ID = None

    protocol_instances.pop(instance_id, None)
    return {"instance_id": instance_id}


@app.get("/instances/{instance_id}/routes")
def get_routes(instance_id: str):
    instance = get_protocol_instance(instance_id)
    rslt = [route.as_json for route in instance.rib_routes]
    return rslt


@app.get("/instances/{instance_id}/routes/static")
def get_static_routes(instance_id: str):
    instance = get_protocol_instance(instance_id)
    rslt = [route.as_json for route in instance.static_routes]
    return rslt


@app.post("/instances/{instance_id}/redistribute")
def redistribute(instance_id: str):
    instance = get_protocol_instance(instance_id)
    instance.redistribute()
    return instance.as_json


@app.post("/instances/{instance_id}/routes/rib/refresh")
def refresh_rib(instance_id: str):
    instance = get_protocol_instance(instance_id)
    instance.refresh_rib()
    return [route.as_json for route in instance.rib_routes]


@app.post("/instances/{instance_id}/rp_sla/evaluate_routes")
def evaluate_routes(instance_id: str):
    instance = get_protocol_instance(instance_id)
    instance.rp_sla_evaluate_routes()
    return instance.as_json


@app.get("/instances/{instance_id}/best_routes")
def get_best_routes(instance_id: str):
    instance = get_protocol_instance(instance_id)
    rslt = instance.export_routes()
    return [route.as_json for route in rslt]


if __name__ == "__main__":
    uvicorn.run(
        app,
        host=CONTROL_PLANE_CONFIG["listen_address"],
        port=CONTROL_PLANE_CONFIG["listen_port"],
    )
