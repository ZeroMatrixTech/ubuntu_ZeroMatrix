import importlib.util
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import security_baseline as security

class SecurityBaselineTests(unittest.TestCase):
    def fixture(self, directory, version):
        root=Path(directory)
        (root/'var/lib/dpkg').mkdir(parents=True)
        (root/'var/lib/dpkg/status').write_text('Package: ca-certificates\nStatus: install ok installed\nVersion: '+version+'\n')
        (root/'etc/ssl/certs').mkdir(parents=True)
        shutil.copy2('/etc/ssl/certs/ca-certificates.crt',root/'etc/ssl/certs/ca-certificates.crt')
        return root

    def test_old_installed_package_is_rejected_even_with_new_bundle(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=self.fixture(tmp,'20260601~26.04.1')
            with self.assertRaisesRegex(ValueError,'predates'):security.verify(root)

    def test_actual_bundle_is_checked_independently_of_package_version(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=self.fixture(tmp,security.policy()['minimum_ca_version'])
            security.verify(root)
            # Explicitly blacklist a real certificate from the otherwise accepted bundle.
            import hashlib,re,ssl,json
            bundle=(root/'etc/ssl/certs/ca-certificates.crt').read_text()
            cert=re.search(r'-----BEGIN CERTIFICATE-----.*?-----END CERTIFICATE-----',bundle,re.S)[0]
            repo=root/'repo';(repo/'config').mkdir(parents=True)
            baseline=security.policy();baseline['denied_root_sha256']=[hashlib.sha256(ssl.PEM_cert_to_DER_cert(cert)).hexdigest()]
            (repo/'config/security-baseline.json').write_text(json.dumps(baseline))
            with self.assertRaisesRegex(ValueError,'Distrusted'):security.verify(root,repo)

    def test_missing_or_empty_bundle_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=self.fixture(tmp,security.policy()['minimum_ca_version'])
            (root/'etc/ssl/certs/ca-certificates.crt').write_text('')
            with self.assertRaisesRegex(ValueError,'Empty'):security.verify(root)
