"""Run after make -C helm dependencies.

Set S4_TEST_ENDPOINT to an empty, disposable S4 instance to also test bucket
initialization. That test creates buckets and writes sample objects.
"""

import ast
import os
from pathlib import Path
import subprocess
import sys
import unittest
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen

import yaml


CHART = Path(__file__).resolve().parents[1] / "billing-workloads"


def render(*overrides):
    return subprocess.run(
        ["helm", "template", "billing-workloads", str(CHART), "-n", "groundx",
         "-f", str(CHART / "secret.example.yaml"), *overrides],
        text=True, capture_output=True,
    )


def resources(*overrides):
    result = render(*overrides)
    if result.returncode:
        raise AssertionError(result.stderr)
    return [item for item in yaml.safe_load_all(result.stdout) if item]


def find(items, kind, name):
    return next(item for item in items
                if item["kind"] == kind and item["metadata"]["name"] == name)


class StorageRenderingTests(unittest.TestCase):
    def test_saved_storage_hostname_reaches_s4_without_proxy(self):
        items = resources()
        service = find(items, "Service", "s4-s3-proxy")
        pod = find(items, "Deployment", "s4")["spec"]["template"]
        for key, value in service["spec"]["selector"].items():
            self.assertEqual(pod["metadata"]["labels"].get(key), value)
        port = service["spec"]["ports"][0]
        self.assertEqual(port["port"], 7480)
        self.assertIn(port["targetPort"],
                      [p["name"] for p in pod["spec"]["containers"][0]["ports"]])
        self.assertFalse(any(item["kind"] == "Deployment" and
                             item["metadata"]["name"].endswith("-s4-s3-proxy")
                             for item in items))
        api = yaml.safe_load(find(items, "Secret", "config-yaml-map")["stringData"]["config.yaml"])
        self.assertEqual(api["upload"]["service"], "s4")
        self.assertEqual(api["upload"]["baseUrl"], "http://s4-s3-proxy:7480")
        for name, constructor, type_key, url_key in (
            ("layout-config-py-map", "dict", "uploadType", "uploadURL"),
            ("extract-config-py-map", "ContainerUploadSettings", "type", "url"),
        ):
            config = ast.parse(find(items, "Secret", name)["stringData"]["config.py"])
            calls = [node for node in ast.walk(config) if isinstance(node, ast.Call)
                     and isinstance(node.func, ast.Name) and node.func.id == constructor]
            settings = next({arg.arg: ast.literal_eval(arg.value) for arg in call.keywords
                             if arg.arg in (type_key, url_key)}
                            for call in calls if any(arg.arg == type_key for arg in call.keywords))
            self.assertEqual(settings[type_key], "s4")
            self.assertEqual(settings[url_key], "http://s4-s3-proxy:7480/eyelevel/")

    def test_staged_upgrade_can_keep_proxy(self):
        items = resources("--set", "s4PathProxy.enabled=true")
        service = find(items, "Service", "s4-s3-proxy")
        pod = find(items, "Deployment", "billing-workloads-s4-s3-proxy")["spec"]["template"]
        for key, value in service["spec"]["selector"].items():
            self.assertEqual(pod["metadata"]["labels"].get(key), value)

    def test_external_storage_does_not_create_s4_alias(self):
        items = resources("--set", "aws-compatible-storage.enabled=false")
        self.assertFalse(any(item["kind"] == "Service" and
                             item["metadata"]["name"] == "s4-s3-proxy"
                             for item in items))

    def test_protected_files_reject_public_bucket_bootstrap(self):
        result = render(
            "--set", "groundx.file.username=,groundx.file.password=",
            "--set", "groundx.file.existing.url=https://files.example.test",
            "--set-json", 'groundx.fileAccess={"enabled":true,"originsPrivate":true,'
            '"frontProxyTLSVerified":true,"publicUrl":"https://files.example.test",'
            '"storageEndpoint":"https://store.example.test",'
            '"signingEndpoint":"https://signing.example.test",'
            '"storageCredentialsSecretName":"store-credentials"}',
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("publicRead", result.stderr)


@unittest.skipUnless(os.environ.get("S4_TEST_ENDPOINT"),
                     "S4_TEST_ENDPOINT must name a disposable S4 instance")
class StorageBootstrapTests(unittest.TestCase):
    def test_bootstrap_preserves_objects_and_limits_anonymous_access(self):
        import boto3
        from botocore.config import Config

        endpoint = os.environ["S4_TEST_ENDPOINT"].rstrip("/")
        try:
            urlopen(f"{endpoint}/", timeout=5).close()
        except HTTPError:
            pass  # An unsigned root request may be denied by a healthy store.
        env = dict(os.environ, S4_ENDPOINT=endpoint,
                   AWS_ACCESS_KEY_ID="s4admin", AWS_SECRET_ACCESS_KEY="s4secret",
                   AWS_DEFAULT_REGION="us-east-1")
        client = boto3.client("s3", endpoint_url=endpoint,
                              aws_access_key_id="s4admin",
                              aws_secret_access_key="s4secret",
                              region_name="us-east-1",
                              config=Config(s3={"addressing_style": "path"}))
        items = resources("--set", "groundx.file.bucketName=billing-test-files",
                          "--set-json",
                          'awsCompatibleStorageBuckets.names=["billing-test-files","billing-artifacts"]')
        job = find(items, "Job", "billing-workloads-s4-create-buckets")
        command = job["spec"]["template"]["spec"]["containers"][0]["command"][2]
        script = command.split("python3 << 'EOF'\n", 1)[1].rsplit("EOF", 1)[0]
        for attempt in range(2):
            subprocess.run([sys.executable, "-c", script], env=env, check=True,
                           capture_output=True, text=True, timeout=120)
            if attempt == 0:
                for bucket in ("billing-test-files", "billing-artifacts"):
                    client.put_object(Bucket=bucket, Key="nested/invoice #1.pdf", Body=b"invoice")
        path = quote("nested/invoice #1.pdf", safe="/")
        with urlopen(f"{endpoint}/billing-test-files/{path}", timeout=5) as response:
            self.assertEqual(response.read(), b"invoice")
        for request in (Request(f"{endpoint}/billing-artifacts/{path}"),
                        Request(f"{endpoint}/billing-test-files/unsigned", data=b"denied", method="PUT")):
            with self.assertRaises(HTTPError) as error:
                urlopen(request, timeout=5)
            self.assertEqual(error.exception.code, 403)


if __name__ == "__main__":
    unittest.main()
