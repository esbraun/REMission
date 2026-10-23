"""Future reviewed one-shot full P2 with public phase progress. Preparation only."""
import argparse,hashlib,importlib.util,json,re,subprocess,sys,time
from pathlib import Path
HERE=Path(__file__).resolve().parent;PREP=HERE.parent
sha=lambda b:hashlib.sha256(b).hexdigest()
def save(path,value):
 with path.open('x',encoding='utf-8') as stream:json.dump(value,stream,indent=2);stream.write('\n')

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--authorized-spec-sha256',required=True);args=parser.parse_args()
 raw=(HERE/'p2-service-spec.json').read_bytes();assert sha(raw)==args.authorized_spec_sha256
 spec=json.loads(raw)
 host=spec['host_python']
 assert Path(sys.executable).as_posix().casefold()==host['executable'].casefold()
 assert Path(sys._base_executable).as_posix().casefold()==host['executable'].casefold()
 assert list(sys.version_info[:3])==host['version'] and sys.flags.isolated==1 and sys.flags.dont_write_bytecode==1
 for item in host['inputs']:
  path=Path(item['path']);data=path.read_bytes()
  assert len(data)==item['bytes'] and sha(data)==item['sha256']
 pwsh=Path(spec['private_auth_powershell']['executable'])
 assert len(pwsh.read_bytes())==spec['private_auth_powershell']['bytes'] and sha(pwsh.read_bytes())==spec['private_auth_powershell']['sha256']
 for item in spec['operator_inputs']:
  path=PREP/item['path'];assert path.resolve().is_relative_to(PREP.resolve())
  for part in (path,*path.parents):assert not part.is_symlink() and not (getattr(part.lstat(),'st_file_attributes',0)&0x400)
  assert sha(path.read_bytes())==item['sha256'] and len(path.read_bytes())==item['bytes']
 public=Path(spec['public_archive']['path'])
 for part in (public,*public.parents):assert not part.is_symlink() and not (getattr(part.lstat(),'st_file_attributes',0)&0x400)
 # Reuse the independently fault-tested regular-file command runner verbatim.
 loader=importlib.util.spec_from_file_location('reviewed_s1_command_runner',PREP/'revision-002/qualify_build_once.py')
 command_module=importlib.util.module_from_spec(loader);loader.loader.exec_module(command_module)
 loader=importlib.util.spec_from_file_location('reviewed_s1_diagnostic_schema',PREP/'operators/support_diagnostics.py')
 diagnostic_module=importlib.util.module_from_spec(loader);loader.loader.exec_module(diagnostic_module)
 sys.path.insert(0,str(PREP/'operators'))
 from analysis_lifecycle import supervise,require_cid,stop_owned,StopUnconfirmed
 output=PREP/spec['output_directory'];output.mkdir(exist_ok=False)
 save(output/'reservation.json',dict(spec_sha256=sha(raw),scope='genuine_full_P2_only_with_public_phase_progress'))
 deadline=time.monotonic()+spec['bounds']['setup_seconds'];owned=[];terminal=set();cleanup=[];unresolved=[];result=None;status='failed';failure=None;intake_attempted=False
 def call(argv,label,cap=15):
  remaining=deadline-time.monotonic()
  if remaining<=0:raise TimeoutError('stage deadline expired')
  record=command_module.command_attempt(argv,output,label,min(cap,remaining),2)
  if record.get('timed_out') or record.get('deadline_rejected') or time.monotonic()>=deadline:
   unresolved.append(dict(operation=label,evidence=label+'.json',cli_pid=record.get('cli_pid'),cli_terminal=record.get('cli_terminal'),daemon_outcome='UNKNOWN'))
   raise StopUnconfirmed('command outcome/deadline unconfirmed: '+label)
  if record.get('exit')!=0 or record.get('error') or record.get('stdout_snapshot_truncated') or record.get('stderr_snapshot_truncated'):
   raise RuntimeError('retained command failure: '+label)
  return record['stdout']
 def create(argv,label,name):
  try:cid=require_cid(call(argv,label).strip())
  except BaseException as error:
   unresolved.append(dict(operation=label,requested_name=name,evidence=label+'.json'))
   raise StopUnconfirmed('container identity unconfirmed: '+label) from error
  owned.append(cid)
  selected='{"Id":{{json .Id}},"Image":{{json .Image}},"RequestedImage":{{json .Config.Image}},"User":{{json .Config.User}},"State":{{json .State}},"Mounts":{{json .Mounts}},"NetworkMode":{{json .HostConfig.NetworkMode}},"ReadonlyRootfs":{{json .HostConfig.ReadonlyRootfs}},"RestartPolicy":{{json .HostConfig.RestartPolicy}},"PortBindings":{{json .HostConfig.PortBindings}}}'
  state=json.loads(call(['docker','inspect','--format',selected,cid],label+'-typed-created'))
  assert state['Id']==cid and state['State']['Status']=='created' and state['State']['Pid']==0
  assert state['RequestedImage'] in spec['images'].values() and state['RequestedImage'] in argv
  assert state['User']==argv[argv.index('--user')+1] and state['ReadonlyRootfs'] and state['RestartPolicy']['Name']=='no'
  assert state['NetworkMode']=='none'
  assert all(m['RW']==(m['Destination']=='/data') for m in state['Mounts'])
  return cid
 def bind(source,target,readonly=True):return ['--mount','type=bind,source='+str(source)+',target='+target+(',readonly' if readonly else '')]
 def volume():return ['--mount','type=volume,source='+spec['volume']+',target=/data']
 def common(memory='1g',tmp='128m',pids='64'):
  return ['--cpus','2','--memory',memory,'--memory-swap',memory,'--pids-limit',pids,'--read-only','--cap-drop','ALL','--security-opt','no-new-privileges','--tmpfs','/tmp:rw,noexec,nosuid,nodev,size='+tmp,'--restart','no','--label','remission.task='+spec['namespace']]
 def public_mounts():return [*bind(HERE,'/operation'),*bind(Path(spec['public_archive']['path']),'/public'),*bind(PREP/'support-archive-authority.proposed.json','/config/authority.json')]
 try:
  # Metadata only on the exact accepted immutable images; no probe/build rerun.
  for role,image in spec['images'].items():assert call(['docker','image','inspect','--format','{{.Id}}',image],role+'-selected-image').strip()==image
  # Successful filtered listings with exact comparisons prove absence; errors
  # never imply absence. No volume/network/create mutation precedes preflight.
  names=call(['docker','volume','ls','--format','{{.Name}}','--filter','name='+spec['volume']],'volume-name-check').splitlines();assert spec['volume'] not in names
  for role,name in spec['containers'].items():assert not call(['docker','ps','-aq','--filter','name=^/'+name+'$'],role+'-name-check').strip()
  call([str(pwsh),'-NoProfile','-NonInteractive','-File',str(HERE/'prepare_private_auth.ps1')],'private-auth-provision',cap=30)
  try:
   assert call(['docker','volume','create','--label','remission.task='+spec['namespace'],spec['volume']],'create-private-volume').strip()==spec['volume']
  except BaseException as error:
   unresolved.append(dict(operation='volume-create',requested_volume=spec['volume'],evidence=['create-private-volume.json']))
   raise StopUnconfirmed('selected volume creation unconfirmed') from error
  ownership_code="import os,json,stat\nfrom pathlib import Path\np=Path('/data')\nassert os.geteuid()==0 and os.getegid()==0\nassert p.is_dir() and not p.is_symlink() and not any(p.iterdir())\ndef metadata():\n s=p.stat()\n return dict(uid=s.st_uid,gid=s.st_gid,mode=stat.S_IMODE(s.st_mode))\nbefore=metadata()\n# CAP_CHOWN permits taking ownership; chmod then uses the caller's own UID.\nos.chown(p,0,0)\ntemporary_owner=metadata()\nassert temporary_owner['uid']==temporary_owner['gid']==0\nos.chmod(p,0o700)\nassert not any(p.iterdir())\n# After this transfer UID0 has no DAC/FOWNER override. Stat remains permitted;\n# do not try to enumerate the now0700 directory as a non-owner.\nos.chown(p,10001,10001)\nafter=metadata()\nassert after==dict(uid=10001,gid=10001,mode=0o700)\nprint(json.dumps(dict(status='fresh_empty_private_volume_owned',before=before,temporary_owner=temporary_owner,after=after,empty_verified_before_final_chown=True)))\n"
  name=spec['containers']['ownership']
  cid=create(['docker','create','--name',name,'--network','none',*common(),'--cap-add','CHOWN','--user','0:0',*volume(),spec['images']['service'],
      'python','-B','-c',ownership_code],'ownership-create',name)
  supervise(cid,output/'ownership-supervision',time.monotonic()+30);terminal.add(cid)
  ownership=json.loads(call(['docker','logs',cid],'ownership-public-result'))
  assert ownership['status']=='fresh_empty_private_volume_owned' and ownership['temporary_owner']['uid']==ownership['temporary_owner']['gid']==0
  assert ownership['after']==dict(uid=10001,gid=10001,mode=0o700) and ownership['empty_verified_before_final_chown'] is True
  save(output/'ownership-result.json',ownership)
  name=spec['containers']['intake'];private=PREP/spec['private_auth_path']
  cid=create(['docker','create','--name',name,'--network','none',*common('2g','512m','64'),'--user','10001:10001',*volume(),*public_mounts(),
      *bind(private,'/private/auth.json'),spec['images']['controls'],'python','-B','/operation/p2_intake.py'],'intake-create',name)
  intake_attempted=True
  supervise(cid,output/'intake-supervision',time.monotonic()+spec['bounds']['p2_seconds']);terminal.add(cid)
  with (output/'intake-supervision/attach.stdout').open('rb') as stream:raw_stdout=stream.read(131073)
  result,progress,diagnostics=diagnostic_module.parse_p2_stdout(raw_stdout)
  assert result['status']=='genuine_p2_intake_idempotence_72_replays_pass'
  save(output/'p2-progress.json',progress)
  save(output/'p2-diagnostics.json',diagnostics)
  save(output/'p2-result.json',result)
  status='genuine_full_P2_only_complete'
 except BaseException as error:
  failure=type(error).__name__;status='STOP UNCONFIRMED' if isinstance(error,StopUnconfirmed) else 'failed'
  for cid in reversed(owned):
   if cid in terminal:continue
   try:cleanup.append(dict(cid=cid,events=stop_owned(cid)))
   except BaseException as stopped:cleanup.append(dict(cid=cid,error_type=type(stopped).__name__));status='STOP UNCONFIRMED'
  raise
 finally:
  save(output/'phase-observation.json',dict(status=status,failure=failure,owned_cids=owned,typed_terminal_cids=sorted(terminal),cleanup=cleanup,unresolved=unresolved,
      Store_created=True if result is not None else 'UNKNOWN' if intake_attempted else False,public_p2_result=result is not None,retained=True,no_worker=True,no_browser=True))
if __name__=='__main__':main()
