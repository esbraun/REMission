"""Rebind executable historical commands; historical JSON itself is immutable."""
from pathlib import Path, PurePosixPath, PureWindowsPath
import sys


def normalized(value):
    path=PureWindowsPath(value)
    return path.as_posix() if path.drive else PurePosixPath(value).as_posix()


def absolute(value):return PureWindowsPath(value).is_absolute() or PurePosixPath(value).is_absolute()


def assert_own_cwd(root, cwd=None):
    if Path(cwd or Path.cwd()).resolve()!=Path(root).resolve():raise ValueError('verification cwd must be the executing source checkout')


def owned_path(value, root):
    root=Path(root).resolve();candidate=Path(value)
    if absolute(str(value)) and not candidate.is_absolute():raise ValueError('unmapped foreign absolute path syntax')
    if not candidate.is_absolute():candidate=root/candidate
    candidate=candidate.resolve()
    if not candidate.is_relative_to(root):raise ValueError('resolved verification source/input/output escapes executing checkout: '+str(candidate))
    return candidate


def rebind_commands(commands, root, python_executable=None):
    """Dependency interpreter is explicit; every other host source is owned.

    Recorded workspace bind roots identify historical checkout prefixes. They
    are parsed lexically, never resolved/read in the other checkout. Unknown
    absolute host inputs fail rather than silently reading another directory.
    """
    root=Path(root).resolve();python_executable=python_executable or sys.executable
    roots=set()
    for command in commands:
        for value in command:
            if value.startswith('type=bind,'):
                parts=dict(part.split('=',1) for part in value.split(',') if '=' in part)
                roots.add(normalized(parts['source']).rstrip('/'))
    roots=sorted(roots,key=len,reverse=True)
    rebound=[]
    for original in commands:
        command=list(original)
        container=command[0]=='docker'
        if Path(command[0].replace('\\','/')).name.lower() in ('python','python3','python.exe'):
            command[0]=python_executable
        elif command[0] not in ('git','docker'):raise ValueError('unapproved verification executable: '+command[0])
        for index,value in enumerate(command[1:],1):
            previous=command[index-1]
            if value.startswith('type=bind,'):
                parts=dict(part.split('=',1) for part in value.split(',') if '=' in part)
                if parts.get('target')!='/workspace' or 'readonly' not in value.split(','):raise ValueError('imported source mounts must be read-only workspace mounts')
                command[index]=f'type=bind,source={root.as_posix()},target=/workspace,readonly'
                continue
            if previous in ('--tmpfs','--workdir','--env'):continue # container namespace, not host sources
            if previous=='-c':
                collapsed=value.replace('\\','/').replace('//','/')
                if any(old.casefold()!=root.as_posix().casefold() and old.casefold() in collapsed.casefold() for old in roots):raise ValueError('embedded historical source path in executable code')
                continue
            if container and (value=='/workspace' or value.startswith('/workspace/')):
                resolved=owned_path(value.removeprefix('/workspace').lstrip('/'),root)
                command[index]='/workspace/'+resolved.relative_to(root).as_posix()
            elif absolute(value):
                norm=normalized(value);relative=None
                for old in roots:
                    if norm.casefold()==old.casefold():relative='';break
                    if norm.casefold().startswith(old.casefold()+'/'):relative=norm[len(old)+1:];break
                if relative is None:
                    # Already-owned paths may occur in a newly recorded run.
                    own=normalized(str(root)).rstrip('/')
                    if norm.casefold()!=own.casefold() and not norm.casefold().startswith(own.casefold()+'/'):raise ValueError('unrecognized absolute verification input: '+value)
                    resolved=owned_path(value,root)
                else:resolved=owned_path(relative,root)
                command[index]='/workspace/'+resolved.relative_to(root).as_posix() if container else str(resolved)
            elif value.endswith('.py') or previous=='-s':
                resolved=owned_path(value,root)
                command[index]=resolved.relative_to(root).as_posix() if container else str(resolved)
        # Check every actual script after rewriting, including symlink targets.
        for index,value in enumerate(command[1:],1):
            if value.endswith('.py') and command[index-1]!='-c':
                script=owned_path(value.removeprefix('/workspace/') if container else value,root)
                if not script.is_file():raise ValueError('verification script missing in executing checkout: '+str(script))
        rebound.append(command)
    return rebound
