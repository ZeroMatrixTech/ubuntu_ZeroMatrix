#!/usr/bin/env python3
"""Build installable online profiles without bundling Code, VSIX or company sources."""
import json
import importlib.util
import subprocess
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
import media

ROOT = Path(__file__).resolve().parents[1]


def boot(original, profile, layer=None):
    if '/casper/vmlinuz' not in original or '/casper/initrd' not in original:
        raise ValueError('Unexpected base boot configuration')
    modes = [('safe graphics', 'nomodeset'), ('normal graphics', '')]
    if profile == 'physical':
        modes.reverse()
    entries = 'set default=0\n'
    for label, flags in modes:
        entries += (f'menuentry "Install ZeroMatrix {profile} ({label}, online)" {{\n'
                    ' set gfxpayload=keep\n'
                    ' linux /casper/vmlinuz autoinstall '
                    'subiquity.autoinstallpath=cdrom/zeromatrix/autoinstall.yaml '
                    f'{flags} --- quiet splash\n initrd /casper/initrd\n}}\n')
    combined=entries+original
    if layer:
        combined=re.sub(r"(linux\s+/casper/vmlinuz)(\s)",lambda m:m[1]+" layerfs-path="+layer+m[2],combined)
    return combined


def configuration():
    profile = os.environ.get('PROFILE', 'vm')
    if profile not in ('vm', 'physical'):
        raise ValueError('PROFILE must be vm or physical')
    version = os.environ.get('VERSION', '').strip() or (ROOT / 'VERSION').read_text().strip()
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9.+-]*', version):
        raise ValueError('Invalid VERSION')
    base = ROOT / 'base/media'
    checksum = json.loads((ROOT / 'config/base-iso.json').read_text())['sha256']
    output = ROOT / 'dist' / f'zeromatrix-{version}-{profile}-amd64.iso'
    return profile, version, base, checksum, output


def check():
    missing = [t for t in ('xorriso', 'git', 'bash', 'unsquashfs', 'mksquashfs', 'unshare', 'newuidmap', 'newgidmap', 'chroot', 'mount', 'umount', 'dpkg-deb', 'dpkg-scanpackages') if not shutil.which(t)]
    if missing:
        raise ValueError('Missing tools: ' + ', '.join(missing))
    config = configuration()
    if not config[2].is_dir():
        raise ValueError('Missing base/media file tree; run git lfs pull or make base-import')
    if config[4].exists() or Path(str(config[4]) + '.partial').exists():
        raise ValueError('Output exists; choose a new VERSION')
    print(f'Profile={config[0]}, version={config[1]}, base={config[2]}', flush=True)
    return config


def build():
    profile, version, base, checksum, output = check()
    spec=importlib.util.spec_from_file_location('media_tree',ROOT/'scripts/media-tree.py')
    tree_module=importlib.util.module_from_spec(spec); spec.loader.exec_module(tree_module)
    tree_manifest=tree_module.verify()
    cache=Path(os.environ.get('ROOTFS_BUILD') or f'build/rootfs-{version}')
    if not cache.is_absolute(): cache=ROOT/cache
    cache_manifest=json.loads((cache/'complete.json').read_text())
    for name,key in [('zeromatrix.squashfs','target_sha256'),('zeromatrix.live.squashfs','live_sha256')]:
        if media.digest(cache/name)!=cache_manifest[key]: raise ValueError('Repacked rootfs checksum mismatch')
    policy = json.loads((ROOT / f'config/profiles/{profile}.json').read_text())
    output.parent.mkdir(exist_ok=True)
    partial = Path(str(output) + '.partial')
    with tempfile.TemporaryDirectory(prefix='zeromatrix-online-') as temp:
        directory = Path(temp)
        payload = directory / 'zeromatrix'
        payload.mkdir()
        for folder in ('scripts', 'config', 'templates'):
            shutil.copytree(ROOT / folder, payload / folder, ignore=shutil.ignore_patterns('__pycache__'))
        # No ACLt history/docs or proprietary editor binaries enter this image.
        for name in ('LICENSE', 'LICENSE.zh-CN.md'):
            shutil.copy2(ROOT / name, payload / name)
        shutil.copy2(ROOT / 'scripts/verify.sh', payload / 'verify.sh')
        (payload / 'project').mkdir()
        shutil.copy2(ROOT / 'config/project-online.json', payload / 'project/manifest.json')
        (payload / 'editor').mkdir()
        lock = json.loads((ROOT / 'config/editor-acquisition.json').read_text())
        if isinstance(lock, dict):
            lock = lock.get('extensions', lock.get('packages'))
        records = [dict(id=r['id'], version=r['version'], online=True) for r in lock]
        (payload / 'editor/manifest.json').write_text(json.dumps(records, indent=2)+'\n')
        packages = [s.strip() for s in (ROOT / 'config/packages.txt').read_text().splitlines()
                    if s.strip() and not s.startswith('#') and s.strip() != 'code']
        packages += ['curl', 'ca-certificates', 'gnupg', 'network-manager', 'language-pack-en', 'language-pack-zh-hans', 'language-pack-gnome-zh-hans', 'fonts-noto-cjk', 'ibus-libpinyin'] + policy['packages']
        (payload / 'install-specs.txt').write_text('\n'.join(sorted(set(packages)))+'\n')
        baseline = json.loads((ROOT / 'config/baseline.json').read_text())
        baseline.update(profile=profile, status='online candidate; actual versions recorded on target')
        (payload / 'baseline.json').write_text(json.dumps(baseline,indent=2)+'\n')
        autoinstall = (ROOT / 'config/autoinstall.yaml').read_text().replace('search_drivers: false', 'search_drivers: '+str(policy['search_drivers']).lower()).replace('/offline/provision.sh', '/offline/scripts/provision-online.sh')
        (payload / 'autoinstall.yaml').write_text(autoinstall)
        manifest = dict(version=version, profile=profile, base_sha256=checksum,
                        media_format='expanded ISO tree and package-pruned SquashFS',
                        rootfs=cache_manifest,
                        tree_manifest_sha256=media.digest(ROOT/'base/tree-manifest.json'),
                        source_commit=media.run('git','-C',str(ROOT),'rev-parse','HEAD').strip(),
                        source_status=media.run('git','-C',str(ROOT),'status','--porcelain'),
                        editor_delivery='target downloads from Microsoft and Marketplace',
                        extensions=records, requested_packages=sorted(set(packages)),
                        acceptance='pending installation test', license='Apache-2.0 for original build sources only')
        (payload / 'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
        files=sorted(p for p in payload.rglob('*') if p.is_file())
        (payload/'SHA256SUMS').write_text(''.join(f'{media.digest(p)}  {p.relative_to(payload)}\n' for p in files))
        stage=directory/'iso'
        def link_or_copy(a,b):
            try: os.link(a,b)
            except OSError: shutil.copy2(a,b)
            return b
        shutil.copytree(base,stage,symlinks=True,copy_function=link_or_copy,
                        ignore=lambda path,names: ['casper'] if Path(path)==base else [])
        for path in [stage,*stage.rglob('*')]:
            if path.is_dir() and not path.is_symlink(): path.chmod(0o755)
        casper=stage/'casper'; casper.mkdir()
        for name in ('vmlinuz','initrd'): link_or_copy(base/'casper'/name,casper/name)
        for name in ('zeromatrix.squashfs','zeromatrix.live.squashfs'): link_or_copy(cache/name,casper/name)
        source=dict(version=2,kernel=dict(default='linux-generic'),sources=[dict(
            default=True,id='ubuntu-desktop',name=dict(en='ZeroMatrix Development Desktop'),
            description=dict(en='Ubuntu GNOME desktop with development workflow; leisure/office apps removed.'),
            path='zeromatrix.squashfs',size=8270364672,type='fsimage-layered',variant='desktop',
            locale_support='langpack',preinstalled_langs=[],variations={'standard':dict(path='zeromatrix.squashfs',size=8270364672)})])
        minimal_alias=dict(source['sources'][0],id='ubuntu-desktop-minimal',default=False)
        source['sources'].append(minimal_alias)
        (casper/'install-sources.yaml').write_text(json.dumps(source,indent=2)+'\n')
        shutil.copy2(cache/'packages.tsv',casper/'zeromatrix.manifest')
        shutil.copy2(cache/'packages.tsv',casper/'zeromatrix.manifest.full')
        (casper/'zeromatrix.size').write_text('8270364672\n')
        shutil.copytree(payload,stage/'zeromatrix')
        grub=stage/'boot/grub/grub.cfg'
        media.replace_extracted_text(grub,boot(grub.read_text(),profile,'zeromatrix.live.squashfs'))
        md5=stage/'md5sum.txt'
        if md5.exists(): md5.unlink()
        # El Torito BIOS image is patched by xorriso at mastering time.
        excluded={'boot.catalog','boot/grub/i386-pc/eltorito.img','md5sum.txt'}
        sums=[]
        for path in sorted(stage.rglob('*')):
            name=path.relative_to(stage).as_posix()
            if path.is_file() and not path.is_symlink() and name not in excluded:
                sums.append(f'{media.digest(path,"md5")}  ./{name}\n')
        md5.write_text(''.join(sums))
        system=ROOT/'base/boot/systemarea.img'
        efi=ROOT/'base/boot/gpt_part2_efi.img'
        media.run('xorriso','-as','mkisofs','-r','-V','ZEROMATRIX_'+profile.upper(),
                  '--grub2-mbr',f'--interval:local_fs:0s-15s:zero_mbrpt,zero_gpt:{system}',
                  '--protective-msdos-label','-partition_cyl_align','off','-partition_offset','16',
                  '--mbr-force-bootable','-append_partition','2','28732ac11ff8d211ba4b00a0c93ec93b',str(efi),
                  '-appended_part_as_gpt','-iso_mbr_part_type','a2a0d0ebe5b9334487c068b6b72699c7',
                  '-c','/boot.catalog','-b','/boot/grub/i386-pc/eltorito.img','-no-emul-boot',
                  '-boot-load-size','4','-boot-info-table','--grub2-boot-info',
                  '-eltorito-alt-boot','-e','--interval:appended_partition_2:all::','-no-emul-boot',
                  '-o',str(partial),str(stage))
    Path(str(output)+'.sha256').write_text(f'{media.digest(partial)}  {output.name}\n')
    output.with_suffix('.manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    partial.rename(output)
    print(output)


if __name__ == '__main__':
    try:
        if len(sys.argv)>1 and sys.argv[1]=='check': check()
        else: build()
    except (ValueError, OSError) as error:
        sys.exit(str(error))
