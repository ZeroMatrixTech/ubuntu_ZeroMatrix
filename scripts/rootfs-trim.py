#!/usr/bin/env python3
"""Repack Ubuntu layers without leisure/office apps, preserving overlay semantics.

Runs inside a private user+mount+PID namespace. No host root or package changes.
"""
import fnmatch
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import media

ROOT=Path(__file__).resolve().parents[1]
INPUT=ROOT/'base/media/casper'
PROTECTED={'ubuntu-desktop-minimal','gnome-shell','gdm3','network-manager','nautilus',
           'gnome-control-center','gnome-terminal','linux-generic','snapd','systemd',
           'sudo','bash','coreutils','python3','apt','dpkg'}
LAYERS=('minimal.squashfs','minimal.standard.squashfs','minimal.standard.live.squashfs')


def run(*args,**kwargs):
    return subprocess.run(args,check=True,**kwargs)


def metadata(image):
    # Export only the pseudo header, never the uncompressed file data stream.
    proc=subprocess.Popen(['unsquashfs','-pf','-',str(image)],stdout=subprocess.PIPE,stderr=subprocess.DEVNULL)
    lines=[]
    try:
        for raw in proc.stdout:
            line=raw.decode('utf-8','surrogateescape').rstrip('\n')
            if line=='# START OF DATA - DO NOT MODIFY': break
            lines.append(line)
        else: raise ValueError('SquashFS pseudo header lacks data marker')
    finally:
        proc.stdout.close()
        proc.terminate()
        proc.wait()
    devices=[]; opaque=[]; semantic=[]; links=[]
    for line in lines:
        match=re.match(r'((?:\\.|[^ ])+) ([A-Za-z])(?: (.*))?$',line)
        if not match: continue
        name=re.sub(r'\\([\\ ])',r'\1',match[1])
        kind=match[2]
        fields=[name,kind,*(match[3] or '').split()]
        if name!='/' and (name.startswith('/') or '..' in Path(name).parts):
            raise ValueError('Unsafe SquashFS path')
        if kind in ('C','B'):
            _,_,mtime,mode,uid,gid,major,minor=fields
            devices.append(dict(path=name,kind=kind.lower(),mode=mode,uid=uid,gid=gid,major=major,minor=minor))
        if kind=='L':
            links.append((name,re.sub(r'\\([\\ ])',r'\1',match[3] or '')))
        if kind=='x' and 'trusted.overlay.opaque=' in line:
            if fields[2]!='trusted.overlay.opaque=y': raise ValueError('Unsupported opaque directory encoding')
            opaque.append(name); semantic.append(line)
        if kind=='x' and any(s in line for s in ('trusted.overlay.redirect=','trusted.overlay.metacopy=')):
            raise ValueError('Unsupported redirected/metacopy input; needs explicit handling')
    by_name={d['path']:d for d in devices}
    for _ in range(len(links)+1):
        added=False
        for name,target in links:
            if target in by_name and name not in by_name:
                item=dict(by_name[target],path=name); devices.append(item); by_name[name]=item; added=True
        if not added: break
    return dict(devices=devices,opaque=opaque,semantic=semantic)


def unlink(path):
    if path.is_dir() and not path.is_symlink(): shutil.rmtree(path)
    elif path.exists() or path.is_symlink(): path.unlink()


def unpack(image,destination,info,merge=False):
    if merge:
        for name in info['opaque']:
            target=destination/name
            if target.is_dir() and not target.is_symlink():
                for child in target.iterdir(): unlink(child)
        for d in info['devices']:
            if d['major']==d['minor']=='0': unlink(destination/d['path'])
    excludes=[d['path'] for d in info['devices']]
    run('unsquashfs','-no-progress','-processors','4','-strict-errors','-xattrs-exclude','^trusted[.]overlay[.]',
        '-f','-d',str(destination),'-excludes',str(image),*excludes)


def restore_snap_assets(root):
    descriptor=ROOT/'base/system-layer.json'
    if not descriptor.exists(): return
    record=json.loads(descriptor.read_text())
    linked={}
    for entry in record['snaps']:
        relative=Path(entry['path'])
        if relative.is_absolute() or '..' in relative.parts:
            raise ValueError('Unsafe snap destination')
        source=ROOT/entry['file']
        destination=root/relative
        destination.parent.mkdir(parents=True,exist_ok=True)
        if entry['file'] in linked:
            os.link(linked[entry['file']],destination)
        else:
            if media.digest(source)!=entry['sha256'] or source.stat().st_size!=entry['bytes']:
                raise ValueError('Snap asset checksum mismatch')
            shutil.copy2(source,destination)
            linked[entry['file']]=destination
        os.chown(destination,entry['uid'],entry['gid'])
        destination.chmod(entry['mode'])
        os.utime(destination,(entry['mtime'],entry['mtime']))


def package_records(text):
    return {line.split('\t')[0]:line.split('\t')[1] for line in text.splitlines() if '\t' in line}


def installed(root):
    text=subprocess.check_output(['chroot',str(root),'dpkg-query','-W','-f=${binary:Package}\t${Version}\t${db:Status-Status}\n'],text=True)
    return {fields[0]:fields[1] for line in text.splitlines() if len(fields:=line.split('\t'))==3 and fields[2]=='installed'}


def pseudo(path,info,overlay=False,source=None):
    lines=[]
    for d in info['devices']:
        if source is not None and os.path.lexists(source/d['path']): continue
        if not overlay and d['major']==d['minor']=='0': continue
        name=d['path'].replace('\\','\\\\').replace(' ','\\ ')
        lines.append(f"{name} {d['kind']} {d['mode']} {d['uid']} {d['gid']} {d['major']} {d['minor']}")
    if overlay: lines+=info['semantic']
    path.write_text('\n'.join(lines)+'\n')


def pack(source,output,pseudo_file):
    if output.exists(): raise ValueError('Refusing to overwrite packed filesystem')
    run('mksquashfs',str(source),str(output),'-noappend','-comp','zstd','-Xcompression-level','15','-b','1048576',
        '-processors','4','-no-progress','-pf',str(pseudo_file))


def fingerprint():
    files=[ROOT/'base/tree-manifest.json',ROOT/'config/remove-packages.txt',ROOT/'scripts/rootfs-trim.py']
    return hashlib.sha256(b''.join(p.read_bytes() for p in files)).hexdigest()


def build(work):
    if os.geteuid()!=0: raise ValueError('Run through make rootfs (private user namespace)')
    if (work/'complete.json').exists():
        if json.loads((work/'complete.json').read_text())['fingerprint']!=fingerprint():
            raise ValueError('Rootfs cache differs from current inputs; use a new ROOTFS_BUILD directory')
        return
    if work.exists() and not (work/'unpacked.json').exists(): raise ValueError('Incomplete rootfs directory exists; preserve log and choose a new ROOTFS_BUILD')
    if (work/'unpacked.json').exists() and json.loads((work/'unpacked.json').read_text()).get('fingerprint')!=fingerprint():
        raise ValueError('Unpacked cache inputs changed; use a new ROOTFS_BUILD directory')
    if (work/'mutation-started').exists() and not (work/'pruned.json').exists():
        raise ValueError('Interrupted package mutation; preserve evidence and use a fresh ROOTFS_BUILD')
    work.mkdir(parents=True,exist_ok=True)
    root=work/'rootfs'; live=work/'live-overlay'
    layers=list(LAYERS)
    if (ROOT/'base/system-layer.json').exists(): layers[0]='minimal.core.squashfs'
    infos={name:metadata(INPUT/name) for name in layers}
    (work/'layer-metadata.json').write_text(json.dumps(infos,indent=2)+'\n')
    if not (work/'unpacked.json').exists():
        unpack(INPUT/layers[0],root,infos[layers[0]])
        restore_snap_assets(root)
        unpack(INPUT/LAYERS[1],root,infos[LAYERS[1]],merge=True)
        unpack(INPUT/LAYERS[2],live,infos[LAYERS[2]])
        (work/'unpacked.json').write_text(json.dumps(dict(fingerprint=fingerprint()))+'\n')
    if not (work/'pruned.json').exists():
        for name in ('dev','proc','run'): (root/name).mkdir(exist_ok=True)
        run('mount','--rbind','/dev',str(root/'dev'))
        run('mount','-t','proc','proc',str(root/'proc'))
        policy=root/'usr/sbin/policy-rc.d'
        saved=policy.read_bytes() if policy.exists() else None
        saved_mode=policy.stat().st_mode&0o777 if policy.exists() else None
        policy.write_text('#!/bin/sh\nexit 101\n'); policy.chmod(0o755)
        try:
            before=installed(root)
            patterns=[s.strip() for s in (ROOT/'config/remove-packages.txt').read_text().splitlines() if s.strip() and not s.startswith('#')]
            requested=sorted(p for p in before if any(fnmatch.fnmatchcase(p.split(':')[0],pattern) for pattern in patterns))
            simulation=subprocess.check_output(['chroot',str(root),'apt-get','-s','purge',*requested],text=True) if requested else ''
            removals={line.split()[1].split(':')[0] for line in simulation.splitlines() if line.startswith(('Remv ','Purg '))}
            if removals&PROTECTED: raise ValueError('Purge would remove protected desktop/system packages: '+str(removals&PROTECTED))
            (work/'purge-plan.txt').write_text(simulation)
            if requested:
                (work/'mutation-started').touch()
                run('chroot',str(root),'env','DEBIAN_FRONTEND=noninteractive','apt-get','--no-download','-y',
                    '-o','APT::Get::AutomaticRemove=false','purge',*requested)
            after=installed(root)
            removed=sorted(set(before)-set(after))
            # dpkg-query also lists config-files records; use the authoritative status.
            status=(root/'var/lib/dpkg/status').read_text()
            installed_names={re.search(r'^Package: (.+)$',p,re.M)[1] for p in status.split('\n\n') if 'Status: install ok installed' in p}
            removed=sorted(p for p in before if p.split(':')[0] not in installed_names)
            if (PROTECTED&{p.split(':')[0] for p in before})-installed_names:
                raise ValueError('Protected package missing after purge')
            # Live overlay has a complete dpkg database. Remove purged records there too.
            live_status=live/'var/lib/dpkg/status'
            removed_names={p.split(':')[0] for p in removed}
            paragraphs=[]
            for paragraph in live_status.read_text().split('\n\n'):
                match=re.search(r'^Package: (.+)$',paragraph,re.M)
                if match and match[1] in removed_names: continue
                paragraphs.append(paragraph)
            live_status.write_text('\n\n'.join(paragraphs))
            live_status_old=live/'var/lib/dpkg/status-old'
            if live_status_old.exists(): live_status_old.unlink()
            report=dict(requested=requested,removed=removed,protected=sorted(PROTECTED),autoremove=False)
            (work/'removal-report.json').write_text(json.dumps(report,indent=2)+'\n')
            (work/'packages.tsv').write_text(''.join(f'{p}\t{before[p]}\n' for p in sorted(before) if p.split(':')[0] in installed_names))
            for tree in (root,live):
                for relative in ('var/lib/apt/lists','var/cache/apt/archives','var/log'):
                    directory=tree/relative
                    if directory.exists():
                        for child in directory.iterdir(): unlink(child)
        finally:
            if saved is None: policy.unlink()
            else: policy.write_bytes(saved); policy.chmod(saved_mode)
            run('umount',str(root/'proc'))
            run('umount','-l',str(root/'dev'))
        (work/'pruned.json').write_text(json.dumps(dict(fingerprint=fingerprint()))+'\n')
    else:
        report=json.loads((work/'removal-report.json').read_text())
    # Pack an actual install source and a Live installer overlay, each with metadata.
    pseudo(work/'target.pseudo',infos[layers[0]],source=root)
    pseudo(work/'live.pseudo',infos[LAYERS[2]],overlay=True,source=live)
    pack(root,work/'zeromatrix.squashfs',work/'target.pseudo')
    pack(live,work/'zeromatrix.live.squashfs',work/'live.pseudo')
    (work/'rootfs-files.txt').write_text(subprocess.check_output(['unsquashfs','-lln',str(work/'zeromatrix.squashfs')],text=True))
    complete=dict(fingerprint=fingerprint(),target_sha256=media.digest(work/'zeromatrix.squashfs'),
                  live_sha256=media.digest(work/'zeromatrix.live.squashfs'),removal_report=report)
    (work/'complete.json').write_text(json.dumps(complete,indent=2)+'\n')


if __name__=='__main__':
    build(Path(sys.argv[1]).resolve())
