import pandas as pd

CSV_PATH = "data/raw/drotar/dataSciRep_Public.csv"

REQUIRED_COLUMNS = {"x", "y", "pressure", "azimuth", "altitude"}

df = pd.read_csv(CSV_PATH)

results = []

for user_id, group in df.groupby("user_id"):
    rows = len(group)
    cols = set(group.columns)
    missing = REQUIRED_COLUMNS - cols

    if rows == 0:
        status = "EMPTY"
    elif missing:
        status = f"MISSING: {missing}"
    else:
        status = "OK"

    results.append({
        "user_id": user_id,
        "rows": rows,
        "status": status
    })

ok = [r for r in results if r["status"] == "OK"]
issues = [r for r in results if r["status"] != "OK"]

print(f"Total subjects checked: {len(results)}")
print(f"✓ OK: {len(ok)}")
print(f"✗ Issues: {len(issues)}")

if issues:
    print("\n--- Problem subjects ---")
    for r in issues:
        print(f"  [{r['status']}] user_{r['user_id']} — {r['rows']} rows")
