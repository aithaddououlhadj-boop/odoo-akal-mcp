import os
import xmlrpc.client
from mcp.server.mcpserver import MCPServer

mcp = MCPServer("Odoo AKAL LAB")

ODOO_URL = os.environ.get("ODOO_URL", "https://odoo.akallab.com")
ODOO_DB = os.environ.get("ODOO_DB", "Database")
ODOO_USER = os.environ.get("ODOO_USER")
ODOO_API_KEY = os.environ.get("ODOO_API_KEY")


def odoo_connection():
    if not ODOO_USER or not ODOO_API_KEY:
        raise RuntimeError("Odoo credentials are not configured.")

    common = xmlrpc.client.ServerProxy(
        f"{ODOO_URL}/xmlrpc/2/common"
    )

    uid = common.authenticate(
        ODOO_DB,
        ODOO_USER,
        ODOO_API_KEY,
        {}
    )

    if not uid:
        raise RuntimeError("Odoo authentication failed.")

    models = xmlrpc.client.ServerProxy(
        f"{ODOO_URL}/xmlrpc/2/object"
    )

    return uid, models


@mcp.tool()
def test_odoo_connection() -> dict:
    """Test the secure connection to Odoo AKAL LAB."""
    uid, _ = odoo_connection()

    return {
        "success": True,
        "message": "Connexion Odoo AKAL LAB réussie",
        "uid": uid
    }


@mcp.tool()
def search_customers(name: str, limit: int = 10) -> list:
    """Search AKAL LAB customers by name."""
    uid, models = odoo_connection()

    return models.execute_kw(
        ODOO_DB,
        uid,
        ODOO_API_KEY,
        "res.partner",
        "search_read",
        [[["name", "ilike", name]]],
        {
            "fields": ["name", "email", "phone"],
            "limit": min(limit, 20)
        }
    )
 @mcp.tool()
def search_customer_orders(customer_name: str, limit: int = 10) -> list:
    """Search sales orders for an AKAL LAB customer."""
    uid, models = odoo_connection()

    partners = models.execute_kw(
        ODOO_DB,
        uid,
        ODOO_API_KEY,
        "res.partner",
        "search_read",
        [[["name", "ilike", customer_name]]],
        {
            "fields": ["id", "name"],
            "limit": 10
        }
    )

    if not partners:
        return []

    partner_ids = [partner["id"] for partner in partners]

    orders = models.execute_kw(
        ODOO_DB,
        uid,
        ODOO_API_KEY,
        "sale.order",
        "search_read",
        [[["partner_id", "in", partner_ids]]],
        {
            "fields": [
                "name",
                "date_order",
                "partner_id",
                "amount_untaxed",
                "amount_tax",
                "amount_total",
                "state",
                "invoice_status"
            ],
            "limit": min(limit, 20),
            "order": "date_order desc"
        }
    )

    return orders
@mcp.tool()
def search_orders(customer_name: str, limit: int = 10) -> list:
    """Search sales orders by customer name, including order lines."""
    uid, models = odoo_connection()

    orders = models.execute_kw(
        ODOO_DB,
        uid,
        ODOO_API_KEY,
        "sale.order",
        "search_read",
        [[["partner_id.name", "ilike", customer_name]]],
        {
            "fields": [
                "name",
                "partner_id",
                "date_order",
                "amount_untaxed",
                "amount_tax",
                "amount_total",
                "state",
                "invoice_status",
                "order_line"
            ],
            "limit": min(limit, 20),
            "order": "date_order desc"
        }
    )

    for order in orders:
        line_ids = order.get("order_line", [])

        if line_ids:
            lines = models.execute_kw(
                ODOO_DB,
                uid,
                ODOO_API_KEY,
                "sale.order.line",
                "read",
                [line_ids],
                {
                    "fields": [
                        "product_id",
                        "name",
                        "product_uom_qty",
                        "price_unit",
                        "price_subtotal"
                    ]
                }
            )
        else:
            lines = []

        order["lines"] = lines
        order.pop("order_line", None)

    return orders

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "10000"))

mcp.run(
        transport="streamable-http",
        host="0.0.0.0",
        port=port,
        streamable_http_path="/mcp",
        stateless_http=True,
        json_response=True
    )
