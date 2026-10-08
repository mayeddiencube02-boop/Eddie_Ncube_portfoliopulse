"""Trigger Airbyte Cloud syncs through the API and wait for them to finish.
Exits with code 1 if any sync fails, so the GitHub Actions run fails loudly.

Environment variables:
  AIRBYTE_CLIENT_ID, AIRBYTE_CLIENT_SECRET   (Airbyte Cloud > Settings > Applications)
  AIRBYTE_CONNECTION_IDS                     comma-separated connection IDs
"""
import os
import sys
import time

import requests

API = "https://api.airbyte.com/v1"
POLL_SECONDS = 15
TIMEOUT_SECONDS = 20 * 60


def get_token():
    r = requests.post(
        f"{API}/applications/token",
        json={
            "client_id": os.environ["AIRBYTE_CLIENT_ID"],
            "client_secret": os.environ["AIRBYTE_CLIENT_SECRET"],
        },
        timeout=60,
    )
    r.raise_for_status()
    return r.json()["access_token"]


def main():
    ids = [c.strip() for c in os.environ["AIRBYTE_CONNECTION_IDS"].split(",") if c.strip()]
    headers = {"Authorization": f"Bearer {get_token()}", "Content-Type": "application/json"}

    jobs = {}
    for cid in ids:
        r = requests.post(f"{API}/jobs", json={"connectionId": cid, "jobType": "sync"},
                          headers=headers, timeout=60)
        if r.status_code >= 400:
            print(f"FAILED to start sync for {cid}: {r.status_code} {r.text}")
            sys.exit(1)
        jobs[cid] = r.json()["jobId"]
        print(f"Started sync for connection {cid} (job {jobs[cid]})")

    deadline = time.time() + TIMEOUT_SECONDS
    pending = dict(jobs)
    failed = False
    while pending and time.time() < deadline:
        time.sleep(POLL_SECONDS)
        for cid, job_id in list(pending.items()):
            r = requests.get(f"{API}/jobs/{job_id}", headers=headers, timeout=60)
            r.raise_for_status()
            data = r.json()
            status = data["status"]
            print(f"  job {job_id}: {status}")
            if status == "succeeded":
                print(f"OK connection {cid}: {data.get('rowsSynced', '?')} rows synced")
                del pending[cid]
            elif status in ("failed", "cancelled", "incomplete"):
                print(f"FAILED connection {cid}: status {status}")
                failed = True
                del pending[cid]

    if pending:
        print(f"TIMED OUT waiting for: {list(pending)}")
        failed = True
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
