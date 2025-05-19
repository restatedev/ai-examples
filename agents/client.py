import sys

import httpx

def main():
    if len(sys.argv) == 0:
        raise ValueError("No input provided")
    data = sys.argv[1]

    r = httpx.post(
        "http://localhost:8080/Agent/my-user/run",
        json=data,
        timeout=60,
    )
    r.raise_for_status()

    print(r.json())


if __name__ == "__main__":
    main()