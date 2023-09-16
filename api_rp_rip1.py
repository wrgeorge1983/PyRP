import toml
from fastapi import FastAPI, HTTPException
from starlette.responses import JSONResponse, Response

from src.config import Config
from src.rp_rip1.main import RP_RIP1, RIP1_RPSpec
from src.system import generate_id

BASE_CONFIG = toml.load("config.toml")
RP_RIP1_CONFIG = BASE_CONFIG["api_rp_rip1"]

protocol_instances: dict[str, RP_RIP1] = dict()

# def _render_output(output: object):
#     if isinstance(output, dict):
#         return {k: _render_output(v) for k, v in output.items()}
#     if isinstance(output, (list, tuple, set)):
#         return [_render_output(v) for v in output]
#
#     if hasattr(output, "json_render"):
#         return output.json_render()
#
#     return str(output)

app = FastAPI()

@app.get("/")
def read_root():
    return {"Service": "RP_RIP1"}


@app.get("/instances")
def get_instances() -> dict[str, RIP1_RPSpec]:
    return {k: v.as_json for k, v in protocol_instances.items()}

@app.get("/instances/{instance_id}")
def get_instance(instance_id: str) -> RIP1_RPSpec:
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
    protocol_instances[instance_id] = RP_RIP1.from_config(config)
    return {"instance_id": instance_id}


@app.delete("/instances/{instance_id}")
def delete_instance(instance_id: str):
    protocol_instances.pop(instance_id, None)
    return {"instance_id": instance_id}


@app.get("/instances/{instance_id}/routes/rib")
def get_rib_routes(instance_id: str):
    instance = protocol_instances.get(instance_id, None)
    if instance is None:
        raise HTTPException(status_code=404, detail="instance not found")
    rslt = [route.as_json for route in instance.rib_routes]
    return rslt


@app.get("/instances/{instance_id}/best_routes")
def get_best_routes(instance_id: str):
    instance = protocol_instances.get(instance_id, None)
    if instance is None:
        raise HTTPException(status_code=404, detail="instance not found")
    rslt = [route.as_json for route in instance.export_routes()]
    return rslt

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=RP_RIP1_CONFIG["listen_address"], port=RP_RIP1_CONFIG["listen_port"])