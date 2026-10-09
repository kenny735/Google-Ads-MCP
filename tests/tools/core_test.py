# Copyright 2026 Google LLC.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Test cases for core tools."""

import unittest
from unittest.mock import MagicMock, patch

from ads_mcp.tools import core


class TestCoreTools(unittest.TestCase):
    """Test cases for the core tools module."""

    @patch("ads_mcp.utils.get_googleads_service")
    def test_list_accessible_customers_success(self, mock_get_service):
        """Tests that list_accessible_customers returns customer IDs with prefix stripped."""
        mock_service = MagicMock()
        mock_response = MagicMock()
        mock_response.resource_names = [
            "customers/1234567890",
            "customers/9876543210",
        ]
        mock_service.list_accessible_customers.return_value = mock_response
        mock_get_service.return_value = mock_service

        result = core.list_accessible_customers()

        self.assertEqual(result, ["1234567890", "9876543210"])
        mock_get_service.assert_called_once_with("CustomerService")
        mock_service.list_accessible_customers.assert_called_once()

    @patch("ads_mcp.utils.get_googleads_service")
    def test_get_account_hierarchy_success(self, mock_get_service):
        """Tests that get_account_hierarchy flattens customer_client rows."""
        client = MagicMock()
        client.client_customer = "customers/111"
        client.descriptive_name = "Child"
        client.level = 1
        client.manager = False
        client.status.name = "ENABLED"
        client.currency_code = "EUR"
        client.time_zone = "Europe/Paris"
        batch = MagicMock()
        batch.results = [MagicMock(customer_client=client)]
        mock_service = MagicMock()
        mock_service.search_stream.return_value = [batch]
        mock_get_service.return_value = mock_service

        result = core.get_account_hierarchy("123-456-7890")

        self.assertEqual(
            result,
            [
                {
                    "customer_id": "111",
                    "name": "Child",
                    "level": 1,
                    "is_manager": False,
                    "status": "ENABLED",
                    "currency_code": "EUR",
                    "time_zone": "Europe/Paris",
                }
            ],
        )
        mock_get_service.assert_called_once_with(
            "GoogleAdsService", login_customer_id="1234567890"
        )
        self.assertEqual(
            mock_service.search_stream.call_args.kwargs["customer_id"],
            "1234567890",
        )


if __name__ == "__main__":
    unittest.main()
