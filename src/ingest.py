import duckdb
import pandas as pd
from pathlib import Path

con = duckdb.connect("data/pipeline.duckdb")
con.execute(Path("sql/schema.sql").read_text())

# Dimensions: reload each run (child table first because of the foreign key)
con.execute("DELETE FROM dim_member")
con.execute("DELETE FROM dim_employer")
con.execute("""
    INSERT INTO dim_employer
    SELECT employer_id, employer_name, due_day
    FROM read_csv('data/raw/employers.csv')
""")
con.execute("""
    INSERT INTO dim_member
    SELECT member_id, employer_id, date_of_birth, join_date, status, monthly_salary
    FROM read_csv('data/raw/members.csv')
""")

# Raw layer: everything kept as text, exactly as received, plus lineage columns
frames = []
for f in sorted(Path("data/raw").glob("E*_2026-09.csv")):
    df = pd.read_csv(f, dtype=str, keep_default_na=False)
    df.insert(0, "row_num", range(1, len(df) + 1))
    df.insert(0, "source_file", f.name)
    frames.append(df)
raw_df = pd.concat(frames, ignore_index=True)

con.register("raw_df", raw_df)
con.execute("CREATE OR REPLACE TABLE raw_contribution AS SELECT * FROM raw_df")
con.unregister("raw_df")

# Staging layer: typed columns; unparseable values become NULL instead of crashing
con.execute("""
    CREATE OR REPLACE TABLE stg_contribution AS
    SELECT
        source_file, row_num, member_id, employer_id,
        TRY_CAST(period_month    AS DATE)          AS period_month,
        TRY_CAST(employee_amount AS DECIMAL(12,2)) AS employee_amount,
        TRY_CAST(employer_amount AS DECIMAL(12,2)) AS employer_amount,
        TRY_CAST(received_date   AS DATE)          AS received_date
    FROM raw_contribution
""")

for t in ["dim_employer", "dim_member", "raw_contribution", "stg_contribution"]:
    print(t, con.execute(f"SELECT count(*) FROM {t}").fetchone()[0])
con.close()