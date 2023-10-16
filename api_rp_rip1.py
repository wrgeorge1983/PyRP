import logging
import os
from typing import Optional

import toml
from fastapi import FastAPI, HTTPException, BackgroundTasks

from src.fp_interface import ForwardingPlane
from src.generic.rib import RedistributeInRouteSpec, RedistributeOutRouteSpec
from src.config import Config
from src.rp_rip1.main import RP_RIP1_Interface, RIP1_RPSpec, RIP1_FullRPSpec
from src.system import generate_id

BASE_CONFIG = toml.load("config.toml")
RP_RIP1_CONFIG = BASE_CONFIG["api_rp_rip1"]

protocol_instances: dict[str, RP_RIP1_Interface] = dict()

LATEST_INSTANCE_ID: Optional[str] = None

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    handlers=[
        logging.StreamHandler(),
    ],
)

log = logging.getLogger(__name__)

log.info("starting api_rp_rip1")
log.debug(f"RP_RIP1_CONFIG: {RP_RIP1_CONFIG}")


def get_protocol_instance(instance_id: str) -> RP_RIP1_Interface:
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
    return {"Service": "RP_RIP1"}


@app.get("/instances")
def get_instances() -> dict[str, RIP1_RPSpec]:
    return {k: v.as_json for k, v in protocol_instances.items()}


@app.get("/instances/{instance_id}")
def get_protocol(instance_id: str) -> RIP1_RPSpec:
    rslt = get_protocol_instance(instance_id)
    return rslt.as_json


@app.get("/instances/{instance_id}/full")
def get_instance_full(instance_id: str) -> RIP1_FullRPSpec:
    rslt = get_protocol_instance(instance_id)
    return rslt.full_as_json


@app.post("/instances/new_from_config")
def create_instance_from_config(filename: str):
    config = Config()
    try:
        config.load(filename)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="config file not found")

    instance_id = generate_id()
    fp = ForwardingPlane()
    protocol_instances[instance_id] = RP_RIP1_Interface.from_config(config, fp)
    global LATEST_INSTANCE_ID
    LATEST_INSTANCE_ID = instance_id
    return {"instance_id": instance_id}


@app.delete("/instances/{instance_id}")
def delete_instance(instance_id: str):
    protocol_instances.pop(instance_id, None)
    global LATEST_INSTANCE_ID
    if LATEST_INSTANCE_ID == instance_id:
        LATEST_INSTANCE_ID = None
    return {"instance_id": instance_id}


@app.get("/instances/{instance_id}/routes/rib")
def get_rib_routes(instance_id: str):
    instance = get_protocol_instance(instance_id)
    rslt = [route.as_json for route in instance.rib_routes]
    return rslt


@app.post("/instances/{instance_id}/redistribute_in")
def redistribute_in(instance_id: str, routes: list[RedistributeInRouteSpec]):
    instance = get_protocol_instance(instance_id)
    instance.redistribute_in(routes)
    return {}


@app.post("/instances/{instance_id}/redistribute_out")
def redistribute_out(instance_id: str) -> list[RedistributeOutRouteSpec]:
    instance = get_protocol_instance(instance_id)

    return list(
        RedistributeOutRouteSpec(**route.as_json)
        for route in instance.redistribute_out()
    )


@app.post("/instances/{instance_id}/routes/rib/refresh")
def refresh_rib(instance_id: str):
    instance = get_protocol_instance(instance_id)
    instance.refresh_rib()
    return [route.as_json for route in instance.rib_routes]


@app.post("/instances/{instance_id}/sendResponse")
def send_response(instance_id: str):
    instance = get_protocol_instance(instance_id)
    instance.send_response()
    return {"instance_id": instance_id}


@app.post("/instances/{instance_id}/listen")
async def listen(instance_id: str, background_tasks: BackgroundTasks):
    # def callback(data, addr):
    #     print(f"callback: received {data} from {addr}")

    instance = get_protocol_instance(instance_id)
    background_tasks.add_task(instance.listen_udp, instance.handle_udp_bytes)
    return {"instance_id": instance_id}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app, host=RP_RIP1_CONFIG["listen_address"], port=RP_RIP1_CONFIG["listen_port"]
    )
