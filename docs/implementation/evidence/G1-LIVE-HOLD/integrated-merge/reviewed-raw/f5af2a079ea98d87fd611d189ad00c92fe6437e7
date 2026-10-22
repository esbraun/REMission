"""Linux separate service processes with bound sockets and explicit readiness."""
from contextlib import contextmanager
import multiprocessing
import socket
import uvicorn
from services.foundation.app import create_app

CONTEXT=multiprocessing.get_context('fork')


def serve(settings,listener,ready):
    class Server(uvicorn.Server):
        async def startup(self,sockets=None):
            await super().startup(sockets=sockets)
            ready.set()
    Server(uvicorn.Config(create_app(settings),log_level='error',access_log=False)).run(sockets=[listener])


@contextmanager
def service_process(settings):
    listener=socket.socket();listener.bind(('127.0.0.1',0));listener.listen(128)
    port=listener.getsockname()[1];ready=CONTEXT.Event()
    process=CONTEXT.Process(target=serve,args=(settings,listener,ready),daemon=True);process.start();listener.close()
    try:
        if not ready.wait(15):
            raise RuntimeError('actual HTTP process did not reach startup barrier')
        yield 'http://127.0.0.1:'+str(port),process
    finally:
        if process.is_alive():process.terminate()
        process.join(15)
        if process.is_alive():process.kill();process.join(5)
