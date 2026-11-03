import argparse
import concurrent.futures
import statistics
import time
import urllib.error
import urllib.request


def send_request(url: str, timeout: float) -> tuple[bool, float, str]:
    started = time.perf_counter()
    request = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            response.read()
            return 200 <= response.status < 300, time.perf_counter() - started, str(response.status)
    except (OSError, urllib.error.URLError, TimeoutError) as error:
        return False, time.perf_counter() - started, str(error)


def main() -> None:
    parser = argparse.ArgumentParser(description="Measure StoreX logging API latency.")
    parser.add_argument("--url", default="http://localhost:18080/test-log")
    parser.add_argument("--requests", type=int, default=1000)
    parser.add_argument("--concurrency", type=int, default=20)
    parser.add_argument("--timeout", type=float, default=15)
    args = parser.parse_args()

    if not 1 <= args.requests <= 50_000:
        parser.error("--requests must be between 1 and 50000")
    if not 1 <= args.concurrency <= 100:
        parser.error("--concurrency must be between 1 and 100")
    if args.timeout <= 0:
        parser.error("--timeout must be positive")

    started = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrency) as executor:
        results = list(executor.map(lambda _: send_request(args.url, args.timeout), range(args.requests)))
    elapsed = time.perf_counter() - started

    latencies = [duration for _, duration, _ in results]
    successes = sum(1 for success, _, _ in results if success)
    failures = args.requests - successes
    print(f"Requests: {args.requests}; concurrency: {args.concurrency}")
    print(f"Total time: {elapsed:.3f}s")
    print(f"Average response: {statistics.mean(latencies) * 1000:.2f}ms")
    print(f"Successful: {successes}; failed: {failures}")
    if failures:
        for success, _, error in results:
            if not success:
                print(f"Failure: {error}")
                break


if __name__ == "__main__":
    main()
