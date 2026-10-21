"""Execute real denied reads/imports/network under each application identity."""
import importlib
import json
import os
from pathlib import Path
import socket


def main():
    denied={}
    attempts={"list_truth":lambda:list(Path("/truth").iterdir()),
              "open_truth":lambda:Path("/truth/canary.json").read_bytes(),
              "import_truth":lambda:importlib.import_module("evaluation.truth"),
              "import_simulation":lambda:importlib.import_module("simulation"),
              "import_dgp_parameters":lambda:importlib.import_module("contracts.dgp.parameters"),
              "evaluator_network":lambda:socket.create_connection(("foundation-evaluator",8766),timeout=2)}
    if os.environ.get("EVALUATOR_TEST_IP"):
        attempts["evaluator_private_ip_network"]=lambda:socket.create_connection((os.environ["EVALUATOR_TEST_IP"],8766),timeout=2)
    for name,attempt in attempts.items():
        try:
            result=attempt()
            if hasattr(result,"close"):result.close()
            denied[name]={"denied":False}
        except (OSError,ImportError) as error:
            denied[name]={"denied":True,"reason":type(error).__name__}
    assert all(item["denied"] for item in denied.values()),denied
    assert os.getuid()!=0
    assert not Path("/var/run/docker.sock").exists()
    assert not Path("/app/contracts/dgp").exists()
    assert not Path("/app/simulation").exists()
    assert not Path("/app/evaluation").exists()
    print(json.dumps({"status":"passed","uid":os.getuid(),"gid":os.getgid(),"denials":denied,"docker_socket_absent":True,"privileged_source_absent":True},indent=2))


if __name__=="__main__":main()
