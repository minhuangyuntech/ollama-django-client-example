import io
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch
from urllib.error import HTTPError

from django.test import Client, SimpleTestCase, override_settings
from django.core.management import call_command, CommandError

from .gateway import Answer, GatewayError, ask, list_models


@override_settings(OLLAMA_GATEWAY_API_KEY="test-only-never-deploy-this-api-key-12345")
class GatewayTests(SimpleTestCase):
    @patch("chat.gateway.build_opener")
    def test_models_and_header_keep_key_server_side(self, opener):
        opener.return_value.open.return_value.__enter__.return_value = io.BytesIO(b'{"models":[{"name":"mock-classroom"}]}')
        self.assertEqual(list_models(), ["mock-classroom"])
        req = opener.return_value.open.call_args.args[0]
        self.assertTrue(req.get_header("X-api-key").startswith("test-only-"))
        self.assertNotIn("key=", req.full_url)

    @patch("chat.gateway._request")
    def test_chat_and_nanosecond_metric_calculation(self, request):
        request.return_value = ({"model":"mock","done":True,"message":{"content":"MOCK 回答"},
                                 "eval_count":20,"eval_duration":2_000_000_000,"total_duration":3_000_000_000}, 3500)
        result = ask("mock", "你好")
        self.assertEqual(result.tokens_per_second, 10)
        self.assertEqual(result.server_total_ms, 3000)
        self.assertEqual(result.elapsed_ms, 3500)
        self.assertFalse(request.call_args.args[1]["stream"])

    @patch("chat.gateway._request")
    def test_incomplete_answer_is_rejected(self, request):
        request.return_value = ({"done":False,"message":{"content":"partial"}}, 1)
        with self.assertRaises(GatewayError): ask("mock", "question")

    @patch("chat.gateway.build_opener")
    def test_auth_error_is_clear_and_does_not_expose_key(self, opener):
        opener.return_value.open.side_effect = HTTPError("http://gateway/api/tags",401,"unauthorized",{},None)
        with self.assertRaises(GatewayError) as result: list_models()
        self.assertIn("401", str(result.exception))
        self.assertNotIn("test-only-never", str(result.exception))

    @override_settings(OLLAMA_GATEWAY_API_KEY="")
    @patch("chat.gateway.build_opener")
    def test_missing_key_stops_before_network(self, opener):
        with self.assertRaises(GatewayError): list_models()
        opener.assert_not_called()

    @override_settings(OLLAMA_GATEWAY_URL="http://localhost:not-a-port")
    @patch("chat.gateway.build_opener")
    def test_invalid_origin_is_handled_before_network(self, opener):
        with self.assertRaises(GatewayError): list_models()
        opener.assert_not_called()

    @override_settings(OLLAMA_GATEWAY_API_KEY="not-valid\nheader")
    @patch("chat.gateway.build_opener")
    def test_invalid_key_is_handled_before_network(self, opener):
        with self.assertRaises(GatewayError): list_models()
        opener.assert_not_called()

    @patch("chat.gateway._request")
    def test_missing_zero_and_nonfinite_metrics(self, request):
        request.return_value = ({"done":True,"message":{"content":"MOCK"},
                                 "eval_count":12,"eval_duration":0,"total_duration":float("inf")}, 1)
        result = ask("mock", "question")
        self.assertIsNone(result.tokens_per_second)
        self.assertIsNone(result.server_total_ms)
        self.assertIsNone(result.load_ms)

    def test_redirect_does_not_send_credentials_to_new_origin(self):
        received = []

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args): pass

            def do_GET(self):
                if self.path == "/api/tags":
                    self.send_response(302)
                    self.send_header("Location", f"http://localhost:{self.server.server_port}/redirect-target")
                    self.end_headers()
                else:
                    received.append(self.headers.get("X-API-Key"))
                    self.send_response(200)
                    self.end_headers()

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with override_settings(OLLAMA_GATEWAY_URL=f"http://127.0.0.1:{server.server_port}"):
                with self.assertRaises(GatewayError) as result: list_models()
            self.assertEqual(result.exception.status, 302)
            self.assertEqual(received, [])
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)


class SiteTests(SimpleTestCase):
    @patch("chat.views.list_models", return_value=["mock-classroom"])
    def test_page_has_model_form_and_no_api_key(self, models):
        with override_settings(OLLAMA_GATEWAY_API_KEY="test-only-never-deploy-this-api-key-12345"):
            response = self.client.get("/")
        self.assertContains(response, "mock-classroom")
        self.assertContains(response, "csrfmiddlewaretoken")
        self.assertNotContains(response, "test-only-never")

    @patch("chat.views.list_models", return_value=["mock-classroom"])
    @patch("chat.views.ask")
    def test_post_renders_escaped_answer_and_metrics(self, ask_mock, models):
        ask_mock.return_value = Answer("mock-classroom", "<script>alert(1)</script>", 1200, 10, 5, 1000, 100)
        response = self.client.post("/", {"model":"mock-classroom","question":"你好"})
        self.assertContains(response,"&lt;script&gt;")
        self.assertNotContains(response,"<script>alert(1)</script>")
        self.assertContains(response,"1200 ms")

    @patch("chat.views.list_models", return_value=["mock-classroom"])
    @patch("chat.views.ask")
    def test_invalid_model_and_empty_question_do_not_call_ai(self, ask_mock, models):
        self.client.post("/", {"model":"not-offered","question":""})
        ask_mock.assert_not_called()

    @patch("chat.views.list_models", return_value=["mock-classroom"])
    def test_csrf_check_rejects_missing_token(self, models):
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(client.post("/",{"model":"mock-classroom","question":"你好"}).status_code,403)

    @patch("chat.views.list_models", side_effect=GatewayError("中介 API 已達上限（429）",429))
    def test_upstream_problem_has_a_readable_page(self, models):
        self.assertContains(self.client.get("/"), "429")

    @patch("chat.views.list_models", return_value=["mock-classroom"])
    @patch("chat.views.ask")
    def test_missing_metrics_are_reported_without_invented_numbers(self, ask_mock, models):
        ask_mock.return_value = Answer("mock-classroom", "MOCK", 1, None, None, None, None)
        response = self.client.post("/", {"model":"mock-classroom","question":"你好"})
        self.assertContains(response, "未回報", count=4)


class DiagnosticTests(SimpleTestCase):
    @patch("chat.management.commands.check_gateway.list_models", return_value=["mock-model"])
    @patch("chat.management.commands.check_gateway._request")
    def test_diagnostics_check_service_and_models_without_printing_key(self, request, models):
        request.side_effect = [({"status":"ok"}, 1), ({"status":"ready"}, 1)]
        output = io.StringIO()
        call_command("check_gateway", stdout=output)
        self.assertIn("mock-model", output.getvalue())
        self.assertNotIn("test-only-never", output.getvalue())
        self.assertEqual([v.args[0] for v in request.call_args_list], ["/healthz", "/readyz"])

    @patch("chat.management.commands.check_gateway._request", side_effect=GatewayError("金鑰問題（401）",401))
    def test_diagnostics_fail_with_clear_endpoint(self, request):
        with self.assertRaisesMessage(CommandError, "/healthz：金鑰問題（401）"):
            call_command("check_gateway", stdout=io.StringIO())
