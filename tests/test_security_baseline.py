import hashlib
import json
from pathlib import Path
import shutil
import ssl
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import security_baseline as security

NSS='usr/lib/x86_64-linux-gnu/libnssckbi.so'
KNOWN={'d7a7a0fb5d7e2731d771e9484ebcdef71d5f0c3e0a2948782bc83ee0ea699ef4',  # AAA Certificate Services
       '86a1ecba089c4a8d3bbe2734c612ba341d813e043cf9e8a862cd5c57a36bbe6b',  # emSign ECC Root CA - G3
       '7dd78d5f4f13459a83dff9abbba62edbaf6f2d102bf257fd712f4d9f2746ed8d',  # emSign Root TLS CA - G3
       'f2edaaff3d9b701fb4d14c9f285f8c0bad90fc3bcc1fa07d47f4718edaba34a5'}  # emSign Root CS CA - G3

def minimum(name):
    return next(r['version'] for r in security.policy()['packages'] if r['package']==name)

def status(root,versions):
    (root/'var/lib/dpkg').mkdir(parents=True,exist_ok=True)
    (root/'var/lib/dpkg/status').write_text(''.join(f'Package: {name}\nStatus: install ok installed\nVersion: {version}\n\n'
                                                    for name,version in versions.items()))

class SecurityBaselineTests(unittest.TestCase):
    def fixture(self, directory, ca=None, nss=None):
        root=Path(directory)
        status(root,{'ca-certificates':ca or minimum('ca-certificates'),'libnss3':nss or minimum('libnss3')})
        (root/'etc/ssl/certs').mkdir(parents=True)
        shutil.copy2('/etc/ssl/certs/ca-certificates.crt',root/'etc/ssl/certs/ca-certificates.crt')
        (root/NSS).parent.mkdir(parents=True)
        (root/NSS).write_bytes(b'\x7fELF builtins without denied roots')
        return root

    def test_reviewed_roots_cover_all_compromise_anchors(self):
        self.assertEqual(set(security.policy()['denied_root_sha256']),KNOWN)
        self.assertEqual(set(security.denied_roots()),KNOWN)

    def test_denied_pem_must_match_reviewed_fingerprints(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo=Path(tmp);(repo/'config').mkdir()
            baseline=security.policy();baseline['denied_root_sha256']=sorted(KNOWN)[1:]
            (repo/'config/security-baseline.json').write_text(json.dumps(baseline))
            shutil.copy2(ROOT/baseline['denied_roots_pem'],repo/baseline['denied_roots_pem'])
            with self.assertRaisesRegex(ValueError,'differ'):security.denied_roots(repo)

    def test_patched_fixture_is_accepted(self):
        with tempfile.TemporaryDirectory() as tmp:
            evidence=security.verify(self.fixture(tmp))
            self.assertEqual(evidence['packages'],{'ca-certificates':minimum('ca-certificates'),'libnss3':minimum('libnss3')})

    def test_old_installed_package_is_rejected_even_with_new_bundle(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=self.fixture(tmp,ca='20260601~26.04.1')
            with self.assertRaisesRegex(ValueError,'ca-certificates predates'):security.verify(root)

    def test_old_nss_package_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=self.fixture(tmp,nss='2:3.120-1ubuntu2.1')
            with self.assertRaisesRegex(ValueError,'libnss3 predates'):security.verify(root)

    def test_missing_nss_package_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=self.fixture(tmp);status(root,{'ca-certificates':minimum('ca-certificates')})
            with self.assertRaisesRegex(ValueError,'missing: libnss3'):security.verify(root)

    def test_each_denied_root_in_bundle_is_rejected(self):
        for digest,der in security.denied_roots().items():
            with self.subTest(digest[:8]),tempfile.TemporaryDirectory() as tmp:
                root=self.fixture(tmp)
                with open(root/'etc/ssl/certs/ca-certificates.crt','a') as bundle:bundle.write(ssl.DER_cert_to_PEM_cert(der))
                with self.assertRaisesRegex(ValueError,'CA bundle'):security.verify(root)

    def test_each_denied_root_in_nss_builtins_is_rejected(self):
        # NSS compiles the certificate DER into libnssckbi.so (as in libnss3 2:3.120-1ubuntu2.1).
        for digest,der in security.denied_roots().items():
            with self.subTest(digest[:8]),tempfile.TemporaryDirectory() as tmp:
                root=self.fixture(tmp);(root/NSS).write_bytes(b'\x7fELF prefix'+der+b'suffix')
                with self.assertRaisesRegex(ValueError,'NSS builtins'):security.verify(root)

    def test_missing_or_linked_nss_builtins_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=self.fixture(tmp);(root/NSS).unlink()
            with self.assertRaisesRegex(ValueError,'NSS builtins library'):security.verify(root)
            (root/NSS).symlink_to('/usr/lib/x86_64-linux-gnu/libnssckbi.so')
            with self.assertRaisesRegex(ValueError,'NSS builtins library'):security.verify(root)

    def test_live_overlay_uses_lower_target_files_it_does_not_carry(self):
        with tempfile.TemporaryDirectory() as tmp:
            target=self.fixture(Path(tmp)/'target');live=self.fixture(Path(tmp)/'live');(live/NSS).unlink()
            security.verify(live,lower=target)
            (target/NSS).write_bytes(next(iter(security.denied_roots().values())))
            with self.assertRaisesRegex(ValueError,'NSS builtins'):security.verify(live,lower=target)

    def test_live_overlay_copy_shadows_patched_target(self):
        with tempfile.TemporaryDirectory() as tmp:
            target=self.fixture(Path(tmp)/'target');live=self.fixture(Path(tmp)/'live')
            (live/NSS).write_bytes(next(iter(security.denied_roots().values())))
            with self.assertRaisesRegex(ValueError,'NSS builtins'):security.verify(live,lower=target)

    def test_sync_live_replaces_record_metadata_and_shadowed_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            target=self.fixture(Path(tmp)/'target');live=self.fixture(Path(tmp)/'live',nss='2:3.120-1ubuntu2.1')
            (target/NSS).write_bytes(b'patched');(live/NSS).write_bytes(b'stale')
            info=target/'var/lib/dpkg/info';info.mkdir(parents=True)
            (info/'libnss3:amd64.list').write_text('/.\n/usr\n/'+NSS+'\n')
            (info/'libnss3:amd64.md5sums').write_text('x  '+NSS+'\n')
            security.sync_live(target,live,'libnss3')
            self.assertEqual(security.package_status(live,'libnss3')[0],minimum('libnss3'))
            self.assertEqual(security.package_status(live,'ca-certificates')[0],minimum('ca-certificates'))
            self.assertEqual((live/'var/lib/dpkg/status').read_text().count('Package: libnss3\n'),1)
            self.assertEqual((live/NSS).read_bytes(),b'patched')
            self.assertTrue((live/'var/lib/dpkg/info/libnss3:amd64.md5sums').is_file())

    def test_missing_or_empty_bundle_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=self.fixture(tmp)
            (root/'etc/ssl/certs/ca-certificates.crt').write_text('')
            with self.assertRaisesRegex(ValueError,'Empty'):security.verify(root)
