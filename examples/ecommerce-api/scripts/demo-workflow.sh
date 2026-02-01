#!/bin/bash
# TraceTap E-commerce Demo Workflow
# Executes a complete checkout flow through the proxy

set -e

echo "==================================================="
echo "  E-commerce Checkout Flow Demo"
echo "==================================================="
echo ""
echo "This script demonstrates a complete checkout workflow"
echo "through the TraceTap proxy."
echo ""
echo "Prerequisites:"
echo "  - TraceTap proxy running on port 8080"
echo "  - Sample API running on port 5000"
echo ""

API_URL="http://localhost:5000"
PROXY="http://localhost:8080"

echo "Step 1: Browse products..."
echo "GET /products"
curl -s -x "$PROXY" "$API_URL/products" | python3 -m json.tool
echo ""

echo "Step 2: View product details..."
echo "GET /products/1"
curl -s -x "$PROXY" "$API_URL/products/1" | python3 -m json.tool
echo ""

echo "Step 3: View another product..."
echo "GET /products/3"
curl -s -x "$PROXY" "$API_URL/products/3" | python3 -m json.tool
echo ""

echo "Step 4: Add Laptop to cart..."
echo "POST /cart"
curl -s -x "$PROXY" -X POST "$API_URL/cart" \
    -H "Content-Type: application/json" \
    -d '{"product_id": 1, "quantity": 2}' | python3 -m json.tool
echo ""

echo "Step 5: Add USB-C Hub to cart..."
echo "POST /cart"
curl -s -x "$PROXY" -X POST "$API_URL/cart" \
    -H "Content-Type: application/json" \
    -d '{"product_id": 3, "quantity": 1}' | python3 -m json.tool
echo ""

echo "Step 6: View cart..."
echo "GET /cart"
curl -s -x "$PROXY" "$API_URL/cart" | python3 -m json.tool
echo ""

echo "Step 7: Checkout..."
echo "POST /checkout"
CHECKOUT_RESPONSE=$(curl -s -x "$PROXY" -X POST "$API_URL/checkout" \
    -H "Content-Type: application/json" \
    -d '{"payment_method": "credit_card", "shipping_address": "123 Main St, Anytown, ST 12345"}')
echo "$CHECKOUT_RESPONSE" | python3 -m json.tool

# Extract order ID
ORDER_ID=$(echo "$CHECKOUT_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])")
echo ""

echo "Step 8: Check order status..."
echo "GET /orders/$ORDER_ID"
curl -s -x "$PROXY" "$API_URL/orders/$ORDER_ID" | python3 -m json.tool
echo ""

echo "==================================================="
echo "  Checkout Flow Complete!"
echo "==================================================="
echo ""
echo "All requests have been captured by TraceTap."
echo "Press Ctrl+C in the TraceTap terminal to export."
