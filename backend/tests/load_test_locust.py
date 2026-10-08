import random
from locust import HttpUser, between, task


class GraphIntelLoadUser(HttpUser):
    """Locust load test client simulating active market intelligence researchers."""

    wait_time = between(0.1, 0.5)

    def on_start(self):
        """Authenticate or register user upon spawn."""
        self.username = f"loadtest_{random.randint(1000, 999999)}@graphintel.io"
        self.password = "SecurePass123!"
        self.headers = {}

        # Register
        reg_resp = self.client.post(
            "/api/v1/auth/register",
            json={
                "email": self.username,
                "password": self.password,
                "role": "ANALYST",
            },
        )
        if reg_resp.status_code in (200, 201):
            data = reg_resp.json()
            token = data.get("access_token")
            if token:
                self.headers["Authorization"] = f"Bearer {token}"
        else:
            # Login if user existed
            login_resp = self.client.post(
                "/api/v1/auth/login",
                data={"username": self.username, "password": self.password},
            )
            if login_resp.status_code == 200:
                token = login_resp.json().get("access_token")
                if token:
                    self.headers["Authorization"] = f"Bearer {token}"

    @task(3)
    def test_health_endpoints(self):
        """Simulate Kubernetes / load balancer health probes."""
        self.client.get("/api/v1/health/live", name="Health: Liveness")
        self.client.get("/api/v1/health/ready", name="Health: Readiness")

    @task(2)
    def test_metrics_scrape(self):
        """Simulate Prometheus metrics scraping."""
        self.client.get("/api/v1/metrics", name="Prometheus Scrape")

    @task(4)
    def test_vector_query(self):
        """Simulate fast vector retrieval queries."""
        questions = [
            "What were the key venture rounds in 2023?",
            "What is OpenAI's corporate structure?",
            "When was Anthropic founded?",
        ]
        q = random.choice(questions)
        self.client.post(
            "/api/v1/query",
            json={"question": q, "retrieval_mode": "vector", "top_k": 5},
            headers=self.headers,
            name="Query: Vector RAG",
        )

    @task(3)
    def test_hybrid_graphrag_query(self):
        """Simulate fused hybrid GraphRAG queries."""
        questions = [
            "Which companies acquired startups founded by former Google executives?",
            "Who founded DeepMind and how did Google acquire it?",
            "What is the connection between Anthropic and OpenAI?",
        ]
        q = random.choice(questions)
        self.client.post(
            "/api/v1/query",
            json={"question": q, "retrieval_mode": "hybrid", "top_k": 5, "max_graph_hops": 3},
            headers=self.headers,
            name="Query: Hybrid GraphRAG",
        )
