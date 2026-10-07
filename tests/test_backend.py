import base64
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location("backend", Path(__file__).parents[1] / "backend.py")
backend = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(backend)
ID = "11111111-2222-4333-8444-555555555555"


class BackendTests(unittest.TestCase):
    def test_names_with_colons_and_backslashes_and_non_wireguard(self):
        data = f"{ID}:wireguard:yes:Home\\: VPN\\\\work\nother:802-11-wireless:yes:Wi-Fi\n"
        with patch.object(backend, "nmcli", return_value=data):
            self.assertEqual(backend.profiles(), [{"uuid": ID, "name": "Home: VPN\\work", "active": True}])

    def test_actions_use_uuid_and_no_shell(self):
        with patch.object(backend, "profiles", return_value=[{"uuid": ID}]), patch.object(backend, "nmcli") as call:
            backend.change_connection("up", ID)
            call.assert_called_once_with("connection", "up", "uuid", ID)

    def test_unknown_and_malicious_ids_cannot_mutate_connections(self):
        with patch.object(backend, "profiles", return_value=[]), patch.object(backend, "nmcli") as call:
            for identifier in [ID, "--help", "$(touch /tmp/invalid)"]:
                with self.assertRaises(backend.BackendError):
                    backend.change_connection("up", identifier)
            call.assert_not_called()

    def test_reject_remote_file(self):
        with self.assertRaises(backend.BackendError):
            backend.config_path("file://remote/wg.conf")

    def test_reject_hooks_and_special_routing(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test.conf"
            for key in ["PostUp", "PreDown", "Table", "SaveConfig"]:
                path.write_text(f"[Interface]\n{key} = something\n")
                with self.assertRaises(backend.BackendError):
                    backend.config_path(str(path))

    def test_native_import_prepared_offline_without_autoconnect(self):
        # Synthetic test keys only; no connection is submitted to NetworkManager.
        key = base64.b64encode(bytes(range(32))).decode()
        peer = base64.b64encode(bytes(range(1, 33))).decode()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "wg-test.conf"
            path.write_text(f"[Interface]\nPrivateKey = {key}\nAddress = 10.42.0.2/32\nDNS = 10.42.0.1\n[Peer]\nPublicKey = {peer}\nEndpoint = example.com:51820\nAllowedIPs = 10.42.0.0/24\nPersistentKeepalive = 25\n")
            path.chmod(0o600)
            connection = backend.prepare_import(path.as_uri())
            self.assertFalse(connection.get_setting_connection().get_autoconnect())
            self.assertEqual(connection.get_connection_type(), "wireguard")
            self.assertEqual(connection.get_setting_by_name("wireguard").get_peers_len(), 1)
            self.assertEqual(connection.get_setting_ip4_config().get_num_addresses(), 1)
            self.assertTrue(connection.verify())

    def test_missing_nmcli_has_actionable_error(self):
        with patch.object(backend.subprocess, "run", side_effect=FileNotFoundError):
            with self.assertRaisesRegex(backend.BackendError, "nmcli fehlt"):
                backend.profiles()


if __name__ == "__main__":
    unittest.main()
