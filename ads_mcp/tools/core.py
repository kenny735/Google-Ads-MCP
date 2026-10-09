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

"""Tools for exposing simple, core API methods to the MCP server."""

from typing import Any, Dict, List
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations

import ads_mcp.utils as utils

from google.ads.googleads.errors import GoogleAdsException
from google.ads.googleads.v25.services.types.customer_service import (
    ListAccessibleCustomersResponse,
)

customers_mcp = FastMCP("customers")


@customers_mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
def list_accessible_customers() -> List[str]:
    """Returns ids of customers directly accessible by the user authenticating the call.

    Use this tool first to discover available customer IDs if the user hasn't
    provided one. Most other tools require a valid customer ID as input.

    Returns:
        List[str]: A list of customer IDs.
    """
    ga_service = utils.get_googleads_service("CustomerService")
    accessible_customers: ListAccessibleCustomersResponse = (
        ga_service.list_accessible_customers()
    )
    # remove customer/ from the start of each resource
    return [
        cust_rn.removeprefix("customers/")
        for cust_rn in accessible_customers.resource_names
    ]


_HIERARCHY_FIELDS = [
    "customer_client.client_customer",
    "customer_client.descriptive_name",
    "customer_client.level",
    "customer_client.manager",
    "customer_client.status",
    "customer_client.currency_code",
    "customer_client.time_zone",
]


@customers_mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
def get_account_hierarchy(
    manager_customer_id: str | int,
    login_customer_id: str | int | None = None,
) -> List[Dict[str, Any]]:
    """Returns the account tree under a manager (MCC) account.

    Each row describes one account under the manager, including the manager
    itself at level 0, with its name, level, status, currency and time zone.
    Use `level` to rebuild the tree: level 1 accounts are direct children,
    level 2 accounts sit under a sub-manager, and so on.

    Args:
        manager_customer_id: The id of the manager account to start from.
        login_customer_id: Optional manager customer ID to use as the
            login-customer-id header. Defaults to the manager_customer_id.

    Returns:
        List[Dict[str, Any]]: One dict per account, ordered by level, with the
        keys customer_id, name, level, is_manager, status, currency_code and
        time_zone.
    """
    manager_customer_id = utils.clean_customer_id(manager_customer_id)
    ga_service = utils.get_googleads_service(
        "GoogleAdsService",
        login_customer_id=login_customer_id or manager_customer_id,
    )
    query = (
        f"SELECT {', '.join(_HIERARCHY_FIELDS)} FROM customer_client "
        "ORDER BY customer_client.level"
    )
    try:
        rows = []
        for batch in ga_service.search_stream(
            customer_id=manager_customer_id, query=query
        ):
            for row in batch.results:
                client = row.customer_client
                rows.append(
                    {
                        "customer_id": client.client_customer.removeprefix(
                            "customers/"
                        ),
                        "name": client.descriptive_name,
                        "level": client.level,
                        "is_manager": client.manager,
                        "status": client.status.name,
                        "currency_code": client.currency_code,
                        "time_zone": client.time_zone,
                    }
                )
        return rows
    except GoogleAdsException as ex:
        error_msgs = [
            f"Google Ads API Error: {error.message}"
            for error in ex.failure.errors
        ]
        raise ToolError(
            f"Request ID: {ex.request_id}\n" + "\n".join(error_msgs)
        )
