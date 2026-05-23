from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from src.feishu_sender import send_feishu_webhook_from_file


class FeishuSenderTests(unittest.TestCase):
    @patch("src.feishu_sender.requests.post")
    def test_send_feishu_webhook_from_file(self, mock_post: Mock) -> None:
        mock_resp = Mock()
        mock_resp.status_code = 200
        mock_resp.text = "ok"
        mock_resp.raise_for_status = Mock()
        mock_resp.json = Mock(return_value={"StatusCode": 0, "StatusMessage": "success"})
        mock_post.return_value = mock_resp

        card_path = Path(__file__).resolve().parents[1] / "output/feishu_cards/2026-05-22-ai-paper.json"
        resp = send_feishu_webhook_from_file("http://127.0.0.1:8080/webhook", card_path)

        self.assertEqual(resp.status_code, 200)
        mock_post.assert_called_once()
        _, kwargs = mock_post.call_args
        self.assertEqual(kwargs["headers"]["Content-Type"], "application/json")
        self.assertEqual(kwargs["json"]["msg_type"], "interactive")
        self.assertIn("card", kwargs["json"])


if __name__ == "__main__":
    unittest.main()
