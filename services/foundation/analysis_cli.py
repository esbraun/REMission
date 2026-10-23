"""Host dispatcher administration; not exposed through HTTP or Docker socket."""
import argparse
import json
from pathlib import Path
from .analysis import claim, progress, ingest, fail, interrupt, bind_execution, export_queued_request
from .configuration import environment_settings
from .store import Store, canonical


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('command',choices=['claim','progress','ingest','fail','interrupt','bind-execution','queued-request'])
    parser.add_argument('--job');parser.add_argument('--token');parser.add_argument('--value');parser.add_argument('--directory',type=Path)
    parser.add_argument('--accept-before')
    args=parser.parse_args()
    settings=environment_settings()
    store=Store(settings.database,settings.installed)
    if args.command=='claim':
        response=claim(store,expected=json.loads(args.value) if args.value else None,configured=settings.observed_archives)
    elif args.command=='queued-request':
        if not args.value:parser.error('exact owner/job/receipt/submission selection required')
        response=export_queued_request(store,configured=settings.observed_archives,**json.loads(args.value))
    elif args.command=='interrupt':
        response=dict(interrupted=interrupt(store))
    else:
        if not args.job or not args.token:
            parser.error('job and token required')
        if args.command=='progress':
            response=progress(store,args.job,args.token,json.loads(args.value))
        elif args.command=='bind-execution':
            response=bind_execution(store,args.job,args.token,json.loads(args.value),configured=settings.observed_archives)
        elif args.command=='fail':
            response=fail(store,args.job,args.token,args.value or 'dispatcher-failure')
        else:
            root=(settings.live_export_root/'analyses'/args.job).resolve()
            if args.directory is None or args.directory.resolve()!=root:
                parser.error('ingest directory must be the deployment artifact root for this attempt')
            response=ingest(store,args.job,args.token,root,accept_before=args.accept_before,configured=settings.observed_archives)
    print(canonical(response))


if __name__=='__main__':
    main()
