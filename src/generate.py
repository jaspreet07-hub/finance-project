import random
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

random.seed(42)
Path("data/raw").mkdir(parents=True, exist_ok=True)
Path("data/truth").mkdir(parents=True, exist_ok=True)

employers = pd.DataFrame({
    "employer_id": [f"E{i:03d}" for i in range(1, 6)],
    "employer_name": [f"Company {c}" for c in "ABCDE"],
    "due_day": [7, 10, 15, 10, 7],
})

members = pd.DataFrame({
    "member_id": [f"M{i:05d}" for i in range(1, 501)],
    "employer_id": [random.choice(employers.employer_id) for _ in range(500)],
    "date_of_birth": [date(1965, 1, 1) + timedelta(days=random.randint(0, 12000)) for _ in range(500)],
    "join_date": [date(2015, 1, 1) + timedelta(days=random.randint(0, 3000)) for _ in range(500)],
    "status": random.choices(["ACTIVE", "LEFT"], weights=[93, 7], k=500),
    "monthly_salary": [round(random.uniform(25000, 150000), 2) for _ in range(500)],
})

employers.to_csv("data/raw/employers.csv", index=False)
members.to_csv("data/raw/members.csv", index=False)

period = date(2026, 9, 1)   # contribution month
truth = []

for emp in employers.itertuples():
    # contributions for September are due in October, on the employer's due day
    due = date(2026, 10, emp.due_day)

    rows = []
    active = members[(members.employer_id == emp.employer_id) & (members.status == "ACTIVE")]
    for m in active.itertuples():
        rows.append({
            "member_id": m.member_id,
            "employer_id": emp.employer_id,
            "period_month": period.isoformat(),
            "employee_amount": round(m.monthly_salary * 0.10, 2),
            "employer_amount": round(m.monthly_salary * 0.10, 2),
            "received_date": (due - timedelta(days=random.randint(0, 3))).isoformat(),
        })
    df = pd.DataFrame(rows)

    # inject labelled errors into about 4% of rows
    n_errors = max(1, len(df) // 25)
    for i in random.sample(range(len(df)), n_errors):
        kind = random.choice(["DUPLICATE_ROW", "UNKNOWN_MEMBER", "INVALID_AMOUNT",
                              "ABOVE_LIMIT", "LATE_SUBMISSION"])
        member_before = df.iloc[i]["member_id"]

        if kind == "DUPLICATE_ROW":
            df = pd.concat([df, df.iloc[[i]]], ignore_index=True)
        elif kind == "UNKNOWN_MEMBER":
            unknown_id = f"M{90000 + len(truth):05d}"
            df.iloc[i, df.columns.get_loc("member_id")] = unknown_id
        elif kind == "INVALID_AMOUNT":
            df.iloc[i, df.columns.get_loc("employee_amount")] = -100
        elif kind == "ABOVE_LIMIT":
            df.iloc[i, df.columns.get_loc("employer_amount")] *= 5
        elif kind == "LATE_SUBMISSION":
            df.iloc[i, df.columns.get_loc("received_date")] = (due + timedelta(days=12)).isoformat()

        truth.append({
            "file": f"{emp.employer_id}_2026-09.csv",
            "member_id": unknown_id if kind == "UNKNOWN_MEMBER" else member_before,
            "rule_name": kind,
        })

    df.to_csv(f"data/raw/{emp.employer_id}_2026-09.csv", index=False)

pd.DataFrame(truth).to_csv("data/truth/injected_errors.csv", index=False)
print(f"Generated {len(employers)} employer files, {len(truth)} injected errors")