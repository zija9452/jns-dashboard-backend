"""
Business metrics dashboard for the Regal POS Backend
Provides a web interface to visualize key business metrics
"""
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import plotly.graph_objects as go
import plotly.express as px
from plotly.utils import PlotlyJSONEncoder
import json
import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
import asyncio
import random  # For demo purposes only


app = FastAPI(title="Regal POS Business Metrics Dashboard")


# Data models for metrics
@dataclass
class SalesDataPoint:
    date: datetime.date
    revenue: float
    transactions: int
    avg_order_value: float


@dataclass
class ProductPerformance:
    product_name: str
    units_sold: int
    revenue: float
    profit_margin: float


@dataclass
class CustomerInsight:
    total_customers: int
    new_customers: int
    repeat_customers: int
    customer_lifetime_value: float


class MetricType(Enum):
    SALES_REVENUE = "sales_revenue"
    TRANSACTION_VOLUME = "transaction_volume"
    CUSTOMER_ACQUISITION = "customer_acquisition"
    PRODUCT_PERFORMANCE = "product_performance"
    USER_ACTIVITY = "user_activity"


# Mock data generator for demonstration
class MockDataGenerator:
    """
    Generates mock data for demonstration purposes
    In a real implementation, this would connect to actual data sources
    """

    @staticmethod
    def generate_sales_data(days: int = 30) -> List[SalesDataPoint]:
        """
        Generate mock sales data
        """
        today = datetime.date.today()
        data = []

        for i in range(days):
            date = today - datetime.timedelta(days=i)
            revenue = random.uniform(1000, 10000)
            transactions = random.randint(20, 200)
            avg_order_value = revenue / transactions

            data.append(SalesDataPoint(
                date=date,
                revenue=revenue,
                transactions=transactions,
                avg_order_value=avg_order_value
            ))

        return sorted(data, key=lambda x: x.date)

    @staticmethod
    def generate_product_performance(count: int = 10) -> List[ProductPerformance]:
        """
        Generate mock product performance data
        """
        products = [
            "Premium Widget", "Basic Gadget", "Deluxe Tool", "Standard Device",
            "Advanced Machine", "Simple Component", "Professional Kit",
            "Industrial Part", "Commercial Supply", "Consumer Product"
        ]

        data = []
        for i in range(min(count, len(products))):
            data.append(ProductPerformance(
                product_name=products[i],
                units_sold=random.randint(50, 500),
                revenue=random.uniform(5000, 50000),
                profit_margin=random.uniform(0.1, 0.4)
            ))

        return sorted(data, key=lambda x: x.revenue, reverse=True)

    @staticmethod
    def generate_customer_insights() -> CustomerInsight:
        """
        Generate mock customer insights
        """
        return CustomerInsight(
            total_customers=random.randint(1000, 10000),
            new_customers=random.randint(50, 200),
            repeat_customers=random.randint(300, 3000),
            customer_lifetime_value=random.uniform(100, 1000)
        )


# Dashboard routes
templates = Jinja2Templates(directory="dashboard/templates")


@app.get("/", response_class=HTMLResponse)
async def dashboard_home(request: Request):
    """
    Main dashboard page
    """
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "title": "Regal POS Business Metrics Dashboard"
    })


@app.get("/api/sales-data")
async def get_sales_data(days: int = 30) -> Dict[str, Any]:
    """
    API endpoint to get sales data
    """
    data = MockDataGenerator.generate_sales_data(days)

    # Prepare data for chart
    dates = [d.date.strftime("%Y-%m-%d") for d in data]
    revenues = [d.revenue for d in data]
    transactions = [d.transactions for d in data]

    # Create line chart for revenue
    revenue_fig = go.Figure(data=go.Scatter(x=dates, y=revenues, mode='lines+markers'))
    revenue_fig.update_layout(title="Daily Revenue", xaxis_title="Date", yaxis_title="Revenue ($)")

    # Create bar chart for transactions
    transaction_fig = go.Figure(data=go.Bar(x=dates, y=transactions))
    transaction_fig.update_layout(title="Daily Transactions", xaxis_title="Date", yaxis_title="Transactions")

    return {
        "revenue_chart": json.loads(json.dumps(revenue_fig, cls=PlotlyJSONEncoder)),
        "transaction_chart": json.loads(json.dumps(transaction_fig, cls=PlotlyJSONEncoder)),
        "summary": {
            "total_revenue": sum(revenues),
            "avg_daily_revenue": sum(revenues) / len(revenues),
            "total_transactions": sum(transactions),
            "avg_daily_transactions": sum(transactions) / len(transactions)
        }
    }


@app.get("/api/product-performance")
async def get_product_performance(top_n: int = 10) -> Dict[str, Any]:
    """
    API endpoint to get product performance data
    """
    data = MockDataGenerator.generate_product_performance(top_n)

    # Prepare data for charts
    product_names = [p.product_name for p in data]
    units_sold = [p.units_sold for p in data]
    revenues = [p.revenue for p in data]

    # Create horizontal bar chart for units sold
    units_fig = go.Figure(data=go.Bar(y=product_names, x=units_sold, orientation='h'))
    units_fig.update_layout(title="Units Sold by Product", xaxis_title="Units Sold", yaxis_title="Product")

    # Create horizontal bar chart for revenue
    revenue_fig = go.Figure(data=go.Bar(y=product_names, x=revenues, orientation='h'))
    revenue_fig.update_layout(title="Revenue by Product", xaxis_title="Revenue ($)", yaxis_title="Product")

    return {
        "units_sold_chart": json.loads(json.dumps(units_fig, cls=PlotlyJSONEncoder)),
        "revenue_chart": json.loads(json.dumps(revenue_fig, cls=PlotlyJSONEncoder)),
        "top_products": [
            {
                "name": p.product_name,
                "units_sold": p.units_sold,
                "revenue": p.revenue,
                "profit_margin": p.profit_margin
            } for p in data
        ]
    }


@app.get("/api/customer-insights")
async def get_customer_insights() -> Dict[str, Any]:
    """
    API endpoint to get customer insights
    """
    insights = MockDataGenerator.generate_customer_insights()

    # Create pie chart for customer breakdown
    labels = ['New Customers', 'Repeat Customers']
    values = [insights.new_customers, insights.repeat_customers]

    customer_fig = go.Figure(data=go.Pie(labels=labels, values=values))
    customer_fig.update_layout(title="Customer Acquisition Breakdown")

    return {
        "customer_chart": json.loads(json.dumps(customer_fig, cls=PlotlyJSONEncoder)),
        "insights": {
            "total_customers": insights.total_customers,
            "new_customers": insights.new_customers,
            "repeat_customers": insights.repeat_customers,
            "customer_lifetime_value": insights.customer_lifetime_value
        }
    }


@app.get("/api/real-time-metrics")
async def get_real_time_metrics() -> Dict[str, Any]:
    """
    API endpoint for real-time metrics
    """
    return {
        "active_users": random.randint(10, 100),
        "current_transactions": random.randint(5, 50),
        "revenue_today": random.uniform(5000, 15000),
        "orders_today": random.randint(50, 200),
        "avg_order_value": random.uniform(25, 75)
    }


# Create templates directory and basic HTML template
import os

# Create dashboard directory structure
os.makedirs("dashboard/templates", exist_ok=True)

# Create a basic dashboard template
template_content = """
<!DOCTYPE html>
<html>
<head>
    <title>{{ title }}</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        .dashboard-card {
            margin-bottom: 20px;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .metric-value {
            font-size: 2em;
            font-weight: bold;
            color: #007bff;
        }
        .metric-label {
            font-size: 0.9em;
            color: #6c757d;
        }
    </style>
</head>
<body>
    <div class="container-fluid">
        <h1 class="mt-4 mb-4">Regal POS Business Metrics Dashboard</h1>

        <!-- Real-time metrics -->
        <div class="row">
            <div class="col-md-2">
                <div class="dashboard-card bg-light">
                    <div class="metric-value" id="active-users">--</div>
                    <div class="metric-label">Active Users</div>
                </div>
            </div>
            <div class="col-md-2">
                <div class="dashboard-card bg-light">
                    <div class="metric-value" id="current-transactions">--</div>
                    <div class="metric-label">Current Transactions</div>
                </div>
            </div>
            <div class="col-md-2">
                <div class="dashboard-card bg-light">
                    <div class="metric-value" id="revenue-today">$--</div>
                    <div class="metric-label">Revenue Today</div>
                </div>
            </div>
            <div class="col-md-2">
                <div class="dashboard-card bg-light">
                    <div class="metric-value" id="orders-today">--</div>
                    <div class="metric-label">Orders Today</div>
                </div>
            </div>
            <div class="col-md-2">
                <div class="dashboard-card bg-light">
                    <div class="metric-value" id="avg-order-value">$--</div>
                    <div class="metric-label">Avg Order Value</div>
                </div>
            </div>
            <div class="col-md-2">
                <div class="dashboard-card bg-light">
                    <div class="metric-value" id="customer-satisfaction">--%</div>
                    <div class="metric-label">Satisfaction</div>
                </div>
            </div>
        </div>

        <!-- Charts row -->
        <div class="row">
            <div class="col-md-6">
                <div class="dashboard-card">
                    <h4>Daily Revenue</h4>
                    <div id="revenue-chart" style="width:100%;height:400px;"></div>
                </div>
            </div>
            <div class="col-md-6">
                <div class="dashboard-card">
                    <h4>Daily Transactions</h4>
                    <div id="transaction-chart" style="width:100%;height:400px;"></div>
                </div>
            </div>
        </div>

        <div class="row">
            <div class="col-md-6">
                <div class="dashboard-card">
                    <h4>Units Sold by Product</h4>
                    <div id="units-sold-chart" style="width:100%;height:400px;"></div>
                </div>
            </div>
            <div class="col-md-6">
                <div class="dashboard-card">
                    <h4>Revenue by Product</h4>
                    <div id="product-revenue-chart" style="width:100%;height:400px;"></div>
                </div>
            </div>
        </div>

        <div class="row">
            <div class="col-md-6">
                <div class="dashboard-card">
                    <h4>Customer Acquisition</h4>
                    <div id="customer-chart" style="width:100%;height:400px;"></div>
                </div>
            </div>
            <div class="col-md-6">
                <div class="dashboard-card">
                    <h4>Top Performing Products</h4>
                    <div id="top-products-table"></div>
                </div>
            </div>
        </div>
    </div>

    <script>
        // Function to fetch and update real-time metrics
        async function updateRealTimeMetrics() {
            try {
                const response = await fetch('/api/real-time-metrics');
                const data = await response.json();

                document.getElementById('active-users').textContent = data.active_users;
                document.getElementById('current-transactions').textContent = data.current_transactions;
                document.getElementById('revenue-today').textContent = '$' + data.revenue_today.toFixed(2);
                document.getElementById('orders-today').textContent = data.orders_today;
                document.getElementById('avg-order-value').textContent = '$' + data.avg_order_value.toFixed(2);

                // Simulate customer satisfaction for demo
                document.getElementById('customer-satisfaction').textContent = (Math.random() * 20 + 80).toFixed(1) + '%';
            } catch (error) {
                console.error('Error fetching real-time metrics:', error);
            }
        }

        // Function to load charts
        async function loadCharts() {
            try {
                // Load sales data charts
                const salesResponse = await fetch('/api/sales-data?days=30');
                const salesData = await salesResponse.json();

                Plotly.newPlot('revenue-chart', salesData.revenue_chart.data, salesData.revenue_chart.layout);
                Plotly.newPlot('transaction-chart', salesData.transaction_chart.data, salesData.transaction_chart.layout);

                // Load product performance charts
                const productResponse = await fetch('/api/product-performance?top_n=10');
                const productData = await productResponse.json();

                Plotly.newPlot('units-sold-chart', productData.units_sold_chart.data, productData.units_sold_chart.layout);
                Plotly.newPlot('product-revenue-chart', productData.revenue_chart.data, productData.revenue_chart.layout);

                // Load customer insights
                const customerResponse = await fetch('/api/customer-insights');
                const customerData = await customerResponse.json();

                Plotly.newPlot('customer-chart', customerData.customer_chart.data, customerData.customer_chart.layout);

                // Create top products table
                const tableDiv = document.getElementById('top-products-table');
                let tableHtml = '<table class="table"><thead><tr><th>Product</th><th>Units Sold</th><th>Revenue</th><th>Profit Margin</th></tr></thead><tbody>';

                productData.top_products.forEach(product => {
                    tableHtml += `<tr>
                        <td>${product.name}</td>
                        <td>${product.units_sold}</td>
                        <td>$${product.revenue.toFixed(2)}</td>
                        <td>${(product.profit_margin * 100).toFixed(1)}%</td>
                    </tr>`;
                });

                tableHtml += '</tbody></table>';
                tableDiv.innerHTML = tableHtml;

            } catch (error) {
                console.error('Error loading charts:', error);
            }
        }

        // Initial load
        loadCharts();
        updateRealTimeMetrics();

        // Update real-time metrics every 10 seconds
        setInterval(updateRealTimeMetrics, 10000);
    </script>
</body>
</html>
"""

# Write the template file
with open("dashboard/templates/dashboard.html", "w") as f:
    f.write(template_content)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)