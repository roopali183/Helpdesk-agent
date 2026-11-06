import json
import os
import sys
import time

import tools
from agent import run_agent

CASES = json.load(open("eval_cases.json", encoding="utf-8-sig"))
RESULTS_FILE = "eval_results.json"


def load_saved():
    if os.path.exists(RESULTS_FILE):
        data = json.load(open(RESULTS_FILE, encoding="utf-8"))
        return {r["id"]: r for r in data}
    return {}


def run_case(case):
    tools.USERS["u101"]["locked"] = True  # reset state
    called = []
    start = time.time()
    answer, error = None, None
    try:
        answer = run_agent(
            case["ticket"],
            approver=lambda name, args: True,  # auto-approve for testing
            on_step=lambda s: called.append(s["tool"]),
        )
    except Exception as e:
        error = str(e)

    if error:
        status = "ERROR"
    else:
        ok = all(t in called for t in case["must_call"]) and all(
            t not in called for t in case["must_not_call"]
        )
        status = "PASS" if ok else "FAIL"

    return {
        "id": case["id"],
        "ticket": case["ticket"],
        "status": status,
        "called": called,
        "error": error[:150] if error else None,
        "daily_quota": bool(error) and ("per day" in error.lower() or "PerDay" in error),
        "seconds": round(time.time() - start, 1),
        "answer": answer,
    }


if __name__ == "__main__":
    # python run_eval.py          -> all cases
    # python run_eval.py 1 2 3    -> only these ids
    wanted = {int(a) for a in sys.argv[1:]}
    cases = [c for c in CASES if not wanted or c["id"] in wanted]
    saved = load_saved()

    for case in cases:
        r = run_case(case)
        print(f"[{r['status']}] #{r['id']} {r['ticket']}")
        print(f"        tools: {r['called']}  ({r['seconds']}s)")
        if r["error"]:
            print(f"        error: {r['error'][:90]}")

        # never replace a real PASS/FAIL with an ERROR
        old = saved.get(r["id"])
        if not (r["status"] == "ERROR" and old and old["status"] in ("PASS", "FAIL")):
            saved[r["id"]] = r

        if r["daily_quota"]:
            print("\nDaily quota is used up. Stopping. Try again after it resets.")
            break
        time.sleep(3)

    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted(saved.values(), key=lambda x: x["id"]), f, indent=2)

    ran = [r for r in saved.values() if r["status"] in ("PASS", "FAIL")]
    passed = sum(r["status"] == "PASS" for r in ran)
    errors = sum(r["status"] == "ERROR" for r in saved.values())
    print(f"\nSCORE (cases that ran): {passed}/{len(ran)} passed")
    print(f"Not counted (errors, rerun later): {errors}")