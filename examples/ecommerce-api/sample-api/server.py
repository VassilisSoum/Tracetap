#!/usr/bin/env python3
"""
Sample E-commerce API Server

A minimal e-commerce API for demonstrating TraceTap capabilities.
Run with: python server.py

Endpoints:
- GET  /products          - List all products
- GET  /products/{id}     - Get product details
- POST /cart              - Add item to cart
- GET  /cart              - View cart
- DELETE /cart/{item_id}  - Remove item from cart
- POST /checkout          - Process checkout
- GET  /orders/{id}       - Get order status
- GET  /health            - Health check
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
from urllib.parse import urlparse, parse_qs
from datetime import datetime
import re

# In-memory data store
PRODUCTS = [
    {"id": 1, "name": "Laptop Pro 15", "price": 1299.99, "category": "Electronics", "stock": 50},
    {"id": 2, "name": "Wireless Mouse", "price": 49.99, "category": "Electronics", "stock": 200},
    {"id": 3, "name": "USB-C Hub", "price": 79.99, "category": "Electronics", "stock": 150},
    {"id": 4, "name": "Mechanical Keyboard", "price": 149.99, "category": "Electronics", "stock": 75},
    {"id": 5, "name": "Monitor Stand", "price": 89.99, "category": "Furniture", "stock": 100},
    {"id": 6, "name": "Desk Lamp", "price": 39.99, "category": "Furniture", "stock": 120},
]

CART = []
ORDERS = {}
ORDER_COUNTER = 1000


class EcommerceHandler(BaseHTTPRequestHandler):
    """HTTP request handler for e-commerce API"""

    def _send_response(self, status_code, data=None, content_type="application/json"):
        """Send JSON response"""
        self.send_response(status_code)
        self.send_header("Content-Type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

        if data is not None:
            response = json.dumps(data, indent=2)
            self.wfile.write(response.encode())

    def _read_body(self):
        """Read and parse JSON body"""
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length > 0:
            body = self.rfile.read(content_length)
            return json.loads(body.decode())
        return {}

    def _match_path(self, pattern):
        """Match URL path against pattern with {id} placeholders"""
        parsed = urlparse(self.path)
        path = parsed.path.rstrip('/')

        # Convert pattern to regex
        regex = pattern.replace('{id}', r'(\d+)').rstrip('/') + '$'
        match = re.match(regex, path)

        if match:
            return match.groups()
        return None

    def do_OPTIONS(self):
        """Handle CORS preflight"""
        self._send_response(200)

    def do_GET(self):
        """Handle GET requests"""
        parsed = urlparse(self.path)
        path = parsed.path.rstrip('/')

        # Health check
        if path == "/health":
            self._send_response(200, {"status": "healthy", "timestamp": datetime.now().isoformat()})
            return

        # List products
        if path == "/products":
            query = parse_qs(parsed.query)
            category = query.get('category', [None])[0]

            if category:
                filtered = [p for p in PRODUCTS if p['category'].lower() == category.lower()]
                self._send_response(200, filtered)
            else:
                self._send_response(200, PRODUCTS)
            return

        # Get product by ID
        match = self._match_path("/products/{id}")
        if match:
            product_id = int(match[0])
            product = next((p for p in PRODUCTS if p['id'] == product_id), None)

            if product:
                self._send_response(200, product)
            else:
                self._send_response(404, {"error": "Product not found", "product_id": product_id})
            return

        # View cart
        if path == "/cart":
            total = sum(item['price'] * item['quantity'] for item in CART)
            self._send_response(200, {
                "items": CART,
                "total": round(total, 2),
                "item_count": len(CART)
            })
            return

        # Get order by ID
        match = self._match_path("/orders/{id}")
        if match:
            order_id = int(match[0])
            order = ORDERS.get(order_id)

            if order:
                self._send_response(200, order)
            else:
                self._send_response(404, {"error": "Order not found", "order_id": order_id})
            return

        # Not found
        self._send_response(404, {"error": "Endpoint not found", "path": path})

    def do_POST(self):
        """Handle POST requests"""
        global ORDER_COUNTER
        parsed = urlparse(self.path)
        path = parsed.path.rstrip('/')

        # Add to cart
        if path == "/cart":
            body = self._read_body()
            product_id = body.get('product_id')
            quantity = body.get('quantity', 1)

            if not product_id:
                self._send_response(400, {"error": "product_id is required"})
                return

            product = next((p for p in PRODUCTS if p['id'] == product_id), None)
            if not product:
                self._send_response(404, {"error": "Product not found", "product_id": product_id})
                return

            # Check if already in cart
            existing = next((item for item in CART if item['product_id'] == product_id), None)
            if existing:
                existing['quantity'] += quantity
                cart_item = existing
            else:
                cart_item = {
                    "cart_item_id": len(CART) + 1,
                    "product_id": product_id,
                    "name": product['name'],
                    "price": product['price'],
                    "quantity": quantity
                }
                CART.append(cart_item)

            self._send_response(200, {
                "message": "Item added to cart",
                "item": cart_item,
                "cart_total": round(sum(item['price'] * item['quantity'] for item in CART), 2)
            })
            return

        # Checkout
        if path == "/checkout":
            if not CART:
                self._send_response(400, {"error": "Cart is empty"})
                return

            body = self._read_body()
            payment_method = body.get('payment_method', 'credit_card')
            shipping_address = body.get('shipping_address', '')

            if not shipping_address:
                self._send_response(400, {"error": "shipping_address is required"})
                return

            # Create order
            ORDER_COUNTER += 1
            order_id = ORDER_COUNTER
            total = sum(item['price'] * item['quantity'] for item in CART)

            order = {
                "id": order_id,
                "items": CART.copy(),
                "total": round(total, 2),
                "payment_method": payment_method,
                "shipping_address": shipping_address,
                "status": "confirmed",
                "created_at": datetime.now().isoformat(),
                "estimated_delivery": "3-5 business days"
            }

            ORDERS[order_id] = order
            CART.clear()

            self._send_response(201, order)
            return

        # Not found
        self._send_response(404, {"error": "Endpoint not found", "path": path})

    def do_DELETE(self):
        """Handle DELETE requests"""
        parsed = urlparse(self.path)
        path = parsed.path.rstrip('/')

        # Remove from cart
        match = self._match_path("/cart/{id}")
        if match:
            cart_item_id = int(match[0])
            global CART

            original_length = len(CART)
            CART = [item for item in CART if item.get('cart_item_id') != cart_item_id]

            if len(CART) < original_length:
                self._send_response(200, {"message": "Item removed from cart"})
            else:
                self._send_response(404, {"error": "Cart item not found"})
            return

        self._send_response(404, {"error": "Endpoint not found", "path": path})

    def log_message(self, format, *args):
        """Log HTTP requests"""
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {args[0]}")


def run_server(port=5000):
    """Start the e-commerce API server"""
    server = HTTPServer(('0.0.0.0', port), EcommerceHandler)
    print(f"""
+--------------------------------------------------+
|  E-commerce Sample API                           |
+--------------------------------------------------+
| Server: http://localhost:{port}                    |
+--------------------------------------------------+
| Endpoints:                                       |
|   GET  /products          - List products        |
|   GET  /products/{{id}}     - Product details      |
|   POST /cart              - Add to cart          |
|   GET  /cart              - View cart            |
|   DELETE /cart/{{id}}       - Remove from cart     |
|   POST /checkout          - Process order        |
|   GET  /orders/{{id}}       - Order status         |
|   GET  /health            - Health check         |
+--------------------------------------------------+
| Press Ctrl+C to stop                             |
+--------------------------------------------------+
""")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
        server.shutdown()


if __name__ == '__main__':
    run_server()
