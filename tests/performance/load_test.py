"""
Performance and load testing for the Regal POS Backend
Using Locust for load testing scenarios
"""
import os
import random
from locust import HttpUser, task, between, constant_pacing, TaskSet
from locust_plugins.csv_logger import CSVLogger
import json


class AuthenticatedUser(HttpUser):
    """
    Represents an authenticated user for load testing
    """
    wait_time = between(1, 3)  # Wait 1-3 seconds between tasks

    def on_start(self):
        """
        Called when a user starts
        """
        self.login()

    def login(self):
        """
        Login to get authentication tokens
        """
        # Use environment variables for credentials or defaults
        username = os.getenv("TEST_USERNAME", "admin")
        password = os.getenv("TEST_PASSWORD", "password")

        response = self.client.post(
            "/auth/login",
            json={
                "username": username,
                "password": password
            },
            catch_response=True
        )

        if response.status_code == 200:
            data = response.json()
            self.access_token = data.get("access_token")
            self.refresh_token = data.get("refresh_token")

            # Set the token in headers for subsequent requests
            self.client.headers.update({
                "Authorization": f"Bearer {self.access_token}"
            })
        else:
            print(f"Login failed with status {response.status_code}")
            self.access_token = None


class APITaskSet(TaskSet):
    """
    Task set for API operations
    """

    @task(3)
    def get_products(self):
        """
        Get products list - most common operation
        """
        with self.client.get("/products", catch_response=True) as response:
            if response.status_code in [200, 201]:
                response.success()
            else:
                response.failure(f"Got wrong response code: {response.status_code}")

    @task(2)
    def get_customers(self):
        """
        Get customers list
        """
        with self.client.get("/customers", catch_response=True) as response:
            if response.status_code in [200, 201]:
                response.success()
            else:
                response.failure(f"Got wrong response code: {response.status_code}")

    @task(1)
    def create_customer(self):
        """
        Create a new customer
        """
        customer_data = {
            "name": f"Load Test Customer {random.randint(1000, 9999)}",
            "email": f"test{random.randint(1000, 9999)}@example.com",
            "phone": f"+1-555-{random.randint(100, 999)}-{random.randint(1000, 9999)}",
            "address": "123 Load Test St, City, State"
        }

        with self.client.post("/customers", json=customer_data, catch_response=True) as response:
            if response.status_code in [200, 201]:
                response.success()
            else:
                response.failure(f"Failed to create customer: {response.status_code}")

    @task(1)
    def get_single_product(self):
        """
        Get a specific product by random ID
        """
        # Use a random product ID - in real scenario, you might want to use IDs from a list
        product_id = random.randint(1, 100)

        with self.client.get(f"/products/{product_id}", catch_response=True) as response:
            if response.status_code in [200, 404]:  # 404 is acceptable if product doesn't exist
                response.success()
            elif response.status_code == 404:
                # 404 is acceptable, just mark as success
                response.success()
            else:
                response.failure(f"Got wrong response code: {response.status_code}")

    @task(1)
    def health_check(self):
        """
        Test health check endpoint
        """
        with self.client.get("/health", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Health check failed: {response.status_code}")


class CustomerBehavior(TaskSet):
    """
    Task set for customer-related operations
    """

    @task(4)
    def view_customers(self):
        """
        View customers with pagination
        """
        page = random.randint(1, 5)
        limit = random.choice([10, 25, 50])

        with self.client.get(f"/customers?skip={(page-1)*limit}&limit={limit}", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Failed to get customers: {response.status_code}")

    @task(1)
    def search_customers(self):
        """
        Search for customers
        """
        search_term = random.choice(["John", "Jane", "Bob", "Alice", ""])

        with self.client.get(f"/customers?search={search_term}", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Failed to search customers: {response.status_code}")


class InvoiceBehavior(TaskSet):
    """
    Task set for invoice-related operations
    """

    @task(2)
    def get_invoices(self):
        """
        Get invoices list
        """
        with self.client.get("/invoices", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Failed to get invoices: {response.status_code}")

    @task(1)
    def create_invoice(self):
        """
        Create a new invoice
        """
        # Sample invoice data
        invoice_data = {
            "customer_id": random.randint(1, 100),
            "items": [
                {
                    "product_id": random.randint(1, 50),
                    "quantity": random.randint(1, 5),
                    "price": round(random.uniform(10.0, 100.0), 2)
                }
            ],
            "total_amount": round(random.uniform(50.0, 500.0), 2),
            "status": "pending"
        }

        with self.client.post("/invoices", json=invoice_data, catch_response=True) as response:
            if response.status_code in [200, 201]:
                response.success()
            else:
                response.failure(f"Failed to create invoice: {response.status_code}")


class RegalPOSUser(AuthenticatedUser):
    """
    Main user class that combines all behaviors
    """
    tasks = [APITaskSet, CustomerBehavior, InvoiceBehavior]


# Alternative user class for anonymous users (without authentication)
class AnonymousUser(HttpUser):
    """
    Represents an anonymous user for testing public endpoints
    """
    wait_time = between(2, 5)

    @task(1)
    def health_check(self):
        """
        Test health check endpoint without authentication
        """
        with self.client.get("/health", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Health check failed: {response.status_code}")

    @task(1)
    def health_db(self):
        """
        Test database health endpoint
        """
        with self.client.get("/health/db", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"DB health check failed: {response.status_code}")


# Performance test configuration
class LoadTestConfiguration:
    """
    Configuration class for load testing
    """

    # Default configuration
    DEFAULT_USERS = 10
    SPAWN_RATE = 2  # Users per second
    RUN_TIME = "5m"  # Run for 5 minutes

    # Environment-specific configurations
    ENV_CONFIGS = {
        "development": {
            "users": 5,
            "spawn_rate": 1,
            "run_time": "2m"
        },
        "staging": {
            "users": 50,
            "spawn_rate": 5,
            "run_time": "10m"
        },
        "production": {
            "users": 100,
            "spawn_rate": 10,
            "run_time": "30m"
        }
    }

    @classmethod
    def get_config(cls, environment: str = None):
        """
        Get configuration for the specified environment
        """
        env = environment or os.getenv("LOAD_TEST_ENV", "development")
        return cls.ENV_CONFIGS.get(env, cls.ENV_CONFIGS["development"])


# Additional performance test scenarios
def simulate_peak_load():
    """
    Simulate peak load scenario
    """
    print("Starting peak load simulation...")
    # This would typically be run as a separate test scenario
    pass


def simulate_stress_test():
    """
    Simulate stress test scenario
    """
    print("Starting stress test...")
    # This would typically be run as a separate test scenario
    pass


def simulate_spike_test():
    """
    Simulate spike test scenario
    """
    print("Starting spike test...")
    # This would typically be run as a separate test scenario
    pass


# Metrics and reporting functions
def log_performance_metrics():
    """
    Log performance metrics to external systems
    """
    # This would integrate with monitoring systems like Prometheus
    pass


if __name__ == "__main__":
    # This section runs when the file is executed directly
    # In practice, locust is run from the command line:
    # locust -f load_test.py --host=http://localhost:8000
    print("Performance test file ready. Run with: locust -f load_test.py --host=http://your-host:port")