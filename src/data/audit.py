import os
import pandas as pd

DATA_PATH = "data/raw/drotar/dataSciRep_public/"

SVC_COLUMNS = ["x", "y", "timestamp", "pen_status", "azimuth", "altitude", "pressure"]
REQUIRED_COLUMNS = {"x", "y", "pressure", "azimuth", "altitude"}

results = []

for user_folder in sorted(os.listdir(DATA_PATH)):
    user_path = os.path.join(DATA_PATH, user_folder)
    if not os.path.isdir(user_path):
        continue

    for session in os.listdir(user_path):
        session_path = os.path.join(user_path, session)
        if not os.path.isdir(session_path):
            continue

        for file in os.listdir(session_path):
            if file.endswith(".svc"):
                file_path = os.path.join(session_path, file)
                try:
                    df = pd.read_csv(file_path, sep=" ", skiprows=1, header=None, names=SVC_COLUMNS)
                    cols = set(df.columns)
                    missing = REQUIRED_COLUMNS - cols
                    status = "OK" if not missing else f"MISSING: {missing}"
                    rows = len(df)
                except Exception as e:
                    status = f"ERROR: {e}"
                    rows = 0

                results.append({
                    "user": user_folder,
                    "session": session,
                    "file": file,
                    "rows": rows,
                    "status": status
                })

ok = [r for r in results if r["status"] == "OK"]
issues = [r for r in results if r["status"] != "OK"]

print(f"Total .svc files checked: {len(results)}")
print(f"✓ OK: {len(ok)}")
print(f"✗ Issues: {len(issues)}")

if issues:
    print("\n--- Problem files ---")
    for r in issues:
        print(f"  [{r['status']}] {r['user']}/{r['session']}/{r['file']}")