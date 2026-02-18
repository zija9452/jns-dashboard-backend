#!/bin/bash
# Script to test the product API performance using curl
# This script should be run from the backend directory

echo "Testing API endpoints performance..."

# Define the API base URL
API_BASE_URL="http://localhost:8000"

# Function to test endpoint response time
test_endpoint() {
    local endpoint=$1
    local method=${2:-GET}
    local data=${3:-""}

    echo ""
    echo "Testing $method $endpoint"

    if [ "$method" = "POST" ] && [ -n "$data" ]; then
        # Measure response time for POST with data
        time curl -s -w "\nResponse time: %{time_total}s\n" \
            -X POST \
            -H "Content-Type: application/json" \
            -d "$data" \
            "$API_BASE_URL$endpoint" | head -20
    else
        # Measure response time for GET request
        time curl -s -w "\nResponse time: %{time_total}s\n" \
            -X GET \
            -H "Content-Type: application/json" \
            "$API_BASE_URL$endpoint" | head -20
    fi
}

# First, let's try to login to get a session
echo "Attempting to login to get session..."
LOGIN_RESPONSE=$(curl -s -X POST \
    -H "Content-Type: application/json" \
    -d '{"username":"admin","password":"admin123"}' \
    "$API_BASE_URL/auth/login")

if echo "$LOGIN_RESPONSE" | grep -q "access_token"; then
    echo "Login successful!"
    # Extract session cookie if needed
    SESSION_COOKIE=$(echo "$LOGIN_RESPONSE" | grep -o '"session_id":"[^"]*"' | cut -d'"' -f4)
else
    echo "Login failed or not required for this endpoint"
fi

# Test health endpoint first
test_endpoint "/health" "GET"

# Test the specific product endpoint you mentioned
test_endpoint "/products/view-product" "GET"

# Test basic products endpoint
test_endpoint "/products/" "GET"

# Test the get-products endpoint with a sample ID if any products exist
echo ""
echo "Testing /products endpoint to get a product ID for detailed lookup..."
PRODUCT_LIST=$(curl -s -X GET -H "Content-Type: application/json" "$API_BASE_URL/products/")
PRODUCT_ID=$(echo "$PRODUCT_LIST" | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)

if [ -n "$PRODUCT_ID" ] && [ "$PRODUCT_ID" != "null" ]; then
    echo "Found product ID: $PRODUCT_ID, testing detailed product endpoint..."
    test_endpoint "/products/get-products/$PRODUCT_ID" "GET"
else
    echo "No products found or unable to extract product ID"
fi

echo ""
echo "Performance testing complete."
echo "Note: The 'time' command shows the total response time for each endpoint."