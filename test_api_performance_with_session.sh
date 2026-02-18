#!/bin/bash
# Script to test the product API performance using curl with session authentication
# This script should be run from the backend directory

echo "Testing API endpoints performance with session authentication..."

# Define the API base URL
API_BASE_URL="http://localhost:8000"

# Create a temporary cookie file
COOKIE_FILE=$(mktemp)

# Function to login and get session cookie
login_and_get_session() {
    echo "Logging in to get session cookie..."

    LOGIN_RESPONSE=$(curl -s -c "$COOKIE_FILE" -X POST \
        -H "Content-Type: application/json" \
        -d '{"username":"admin","password":"admin123"}' \
        "$API_BASE_URL/auth/session-login")

    if echo "$LOGIN_RESPONSE" | grep -q "session_token\|Login successful"; then
        echo "Login successful!"
        echo "Session cookie stored in: $COOKIE_FILE"
        echo "Cookie contents:"
        cat "$COOKIE_FILE"
        return 0
    else
        echo "Login failed!"
        echo "Response: $LOGIN_RESPONSE"
        return 1
    fi
}

# Function to test endpoint response time with session cookie
test_endpoint_with_session() {
    local endpoint=$1
    local method=${2:-GET}
    local data=${3:-""}

    echo ""
    echo "Testing $method $endpoint with session authentication"

    if [ "$method" = "POST" ] && [ -n "$data" ]; then
        # Measure response time for POST with data and session
        time curl -s -b "$COOKIE_FILE" -w "\nResponse time: %{time_total}s\n" \
            -X POST \
            -H "Content-Type: application/json" \
            -d "$data" \
            "$API_BASE_URL$endpoint" | head -20
    else
        # Measure response time for GET request with session
        time curl -s -b "$COOKIE_FILE" -w "\nResponse time: %{time_total}s\n" \
            -X GET \
            -H "Content-Type: application/json" \
            "$API_BASE_URL$endpoint" | head -20
    fi
}

# First, login to get the session cookie
if login_and_get_session; then
    # Test health endpoint
    test_endpoint_with_session "/health" "GET"

    # Test the specific product endpoint you mentioned
    test_endpoint_with_session "/products/view-product" "GET"

    # Test basic products endpoint
    test_endpoint_with_session "/products/" "GET"

    # Test the get-products endpoint with a sample ID if any products exist
    echo ""
    echo "Testing /products endpoint to get a product ID for detailed lookup..."
    PRODUCT_LIST=$(curl -s -b "$COOKIE_FILE" -X GET -H "Content-Type: application/json" "$API_BASE_URL/products/")
    PRODUCT_ID=$(echo "$PRODUCT_LIST" | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)

    if [ -n "$PRODUCT_ID" ] && [ "$PRODUCT_ID" != "null" ]; then
        echo "Found product ID: $PRODUCT_ID, testing detailed product endpoint..."
        test_endpoint_with_session "/products/get-products/$PRODUCT_ID" "GET"
    else
        echo "No products found or unable to extract product ID"
        # Try getting a list of products with a smaller limit to see if there are any
        test_endpoint_with_session "/products/?limit=10" "GET"
    fi

    # Clean up
    rm -f "$COOKIE_FILE"
else
    echo "Cannot test authenticated endpoints without valid session."
    echo "Trying to check if there are any unauthenticated endpoints available..."
    curl -s -X GET -H "Content-Type: application/json" "$API_BASE_URL/docs"
fi

echo ""
echo "Performance testing complete."
echo "Note: The 'time' command shows the total response time for each endpoint."