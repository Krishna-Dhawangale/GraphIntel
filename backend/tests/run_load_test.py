import asyncio
import json
import statistics
import time
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from httpx import ASGITransport, AsyncClient
from app.main import app


def calculate_percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    idx = int(len(sorted_vals) * p)
    idx = min(idx, len(sorted_vals) - 1)
    return round(sorted_vals[idx], 2)


async def simulate_user(client: AsyncClient, user_idx: int) -> tuple[float, bool]:
    t0 = time.perf_counter()
    try:
        # Hit health & live
        resp = await client.get("/api/v1/health/live")
        success = resp.status_code == 200
        latency_ms = (time.perf_counter() - t0) * 1000.0
        return latency_ms, success
    except Exception:
        latency_ms = (time.perf_counter() - t0) * 1000.0
        return latency_ms, False


async def run_concurrent_load_test(concurrency_levels=(10, 50, 100)):
    transport = ASGITransport(app=app)
    results = {}

    print("================================================================")
    print("GraphIntel Concurrency & Throughput Benchmark (Locust / ASGI)")
    print("================================================================")

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Warmup
        await client.get("/api/v1/health")

        for concurrency in concurrency_levels:
            total_requests = concurrency * 5  # 5 requests per concurrent client
            tasks = [simulate_user(client, i) for i in range(total_requests)]
            
            t_start = time.perf_counter()
            outcomes = await asyncio.gather(*tasks)
            t_total_sec = time.perf_counter() - t_start

            latencies = [lat for lat, ok in outcomes]
            successes = sum(1 for lat, ok in outcomes if ok)
            errors = total_requests - successes
            error_rate = (errors / total_requests) * 100.0
            throughput = total_requests / t_total_sec

            stats = {
                "concurrency": concurrency,
                "total_requests": total_requests,
                "successful_requests": successes,
                "error_rate_pct": round(error_rate, 2),
                "duration_sec": round(t_total_sec, 3),
                "throughput_rps": round(throughput, 2),
                "latency_avg_ms": round(statistics.mean(latencies), 2),
                "latency_p50_ms": calculate_percentile(latencies, 0.50),
                "latency_p95_ms": calculate_percentile(latencies, 0.95),
                "latency_p99_ms": calculate_percentile(latencies, 0.99),
            }
            results[f"{concurrency}_users"] = stats

            print(f"\n--- Concurrency: {concurrency} Users ---")
            print(f"Total Requests: {total_requests}")
            print(f"Throughput:     {stats['throughput_rps']:.2f} req/s")
            print(f"Error Rate:     {stats['error_rate_pct']:.2f}%")
            print(f"Latency Avg:    {stats['latency_avg_ms']:.2f} ms")
            print(f"Latency p50:    {stats['latency_p50_ms']:.2f} ms")
            print(f"Latency p95:    {stats['latency_p95_ms']:.2f} ms")
            print(f"Latency p99:    {stats['latency_p99_ms']:.2f} ms")

    Path("load_test_results.json").write_text(json.dumps(results, indent=2))
    return results


if __name__ == "__main__":
    asyncio.run(run_concurrent_load_test())
