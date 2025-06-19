import sys

import httpx


def main():
    if len(sys.argv) == 0:
        raise ValueError("No input provided")
    key = sys.argv[1]
    data = sys.argv[2]

    r = httpx.post(
        f"http://localhost:8080/Agent/{key}/run",
        json=data,
        timeout=60,
    )
    r.raise_for_status()

    print(r.json())


if __name__ == "__main__":
    main()
