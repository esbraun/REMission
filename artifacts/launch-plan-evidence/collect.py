import subprocess, os, json, pathlib, hashlib, datetime
out=pathlib.Path(__file__).parent
sdk=pathlib.Path('C:/Users/erics/Documents/Projects/REMission-worktrees/cloud-generator-build-sol-261023/artifacts/cloud-sdk/590.0.0/google-cloud-sdk')
env=os.environ.copy()
env.update(CLOUDSDK_ACTIVE_CONFIG_NAME='remission-poc', CLOUDSDK_CORE_PROJECT='remission-poc-esbraun', CLOUDSDK_CORE_DISABLE_PROMPTS='true', CLOUDSDK_CORE_DISABLE_USAGE_REPORTING='true', CLOUDSDK_CORE_DISABLE_FILE_LOGGING='true', CLOUDSDK_COMPONENT_MANAGER_DISABLE_UPDATE_CHECK='true', CLOUDSDK_CORE_HTTP_TIMEOUT='20', CLOUDSDK_CORE_LOG_HTTP='false', CLOUDSDK_CORE_VERBOSITY='error', CLOUDSDK_CORE_SHOULD_PROMPT_TO_ENABLE_API='false', PYTHONDONTWRITEBYTECODE='1')
prefix=[str(sdk/'platform/bundledpython/python.exe'),'-S','-B',str(sdk/'lib/gcloud.py'),'--quiet','--configuration=remission-poc','--project=remission-poc-esbraun']
calls=[('firewall',prefix+['compute','firewall-rules','list','--filter=network:default','--format=json(name,network,direction,priority,disabled,sourceRanges,sourceTags,targetTags,targetServiceAccounts,allowed,denied)']),('images',['docker','image','inspect','--format','{"Id":{{json .Id}},"Size":{{.Size}},"layer_count":{{len .RootFS.Layers}}}','sha256:a950cdb0dd9b3bbdeb176c6da71903180406a9bf2160ea3d23faf4be3c0f5e72','sha256:d64907d76a2810d2e6cad8acaa012f3df132ced69bfe2636c7eb07f7090b4eee'])]
receipts=[]
for name,argv in calls:
    r=subprocess.run(argv,env=env,capture_output=True,timeout=30)
    for suffix,data in [('stdout',r.stdout),('stderr',r.stderr)]:
        (out/f'{name}.{suffix}.txt').write_bytes(data)
    receipts.append(dict(name=name,argv=argv,returncode=r.returncode))
flags=sdk/'lib/googlecloudsdk/command_lib/compute/instances/flags.py'
receipts.append(dict(sdk_flags=str(flags),sha256=hashlib.sha256(flags.read_bytes()).hexdigest(),lines='2256-2339,2480-2559'))
(out/'receipt.json').write_text(json.dumps(dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),operations=receipts),indent=2)+'\n')
