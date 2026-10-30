import duckdb
import pandas as pd

con = duckdb.connect("data/pipeline.duckdb")
con.execute("DELETE FROM fact_exception")          # rerunnable

con.execute("""
CREATE OR REPLACE TEMP VIEW base AS
SELECT s.*,
       m.employer_id AS m_employer, m.status, m.monthly_salary, e.due_day,
       row_number() OVER (PARTITION BY s.member_id, s.period_month
                          ORDER BY s.source_file, s.row_num) AS occurrence
FROM stg_contribution s
LEFT JOIN dim_member   m ON s.member_id   = m.member_id
LEFT JOIN dim_employer e ON s.employer_id = e.employer_id
""")

RULES = {
    "MALFORMED_FIELD": ("period_month IS NULL OR employee_amount IS NULL "
                        "OR employer_amount IS NULL OR received_date IS NULL",
                        "'empty or unparseable field'"),
    "DUPLICATE_ROW":   ("occurrence > 1",
                        "'member and period already seen'"),
    "UNKNOWN_MEMBER":  ("m_employer IS NULL",
                        "'member_id not in dim_member'"),
    "EMPLOYER_MISMATCH": ("m_employer IS NOT NULL AND m_employer <> employer_id",
                          "'row employer ' || employer_id || ' vs member employer ' || m_employer"),
    "LEFT_MEMBER":     ("status = 'LEFT'",
                        "'contribution for a member who has left'"),
    "INVALID_AMOUNT":  ("employee_amount <= 0 OR employer_amount <= 0",
                        "'non-positive amount'"),
    "ABOVE_LIMIT":     ("monthly_salary IS NOT NULL AND "
                        "employee_amount + employer_amount > 0.30 * monthly_salary",
                        "'total exceeds 30% of salary'"),
    "LATE_SUBMISSION": ("received_date > CAST(period_month + INTERVAL 1 MONTH AS DATE) + (due_day - 1)",
                        "'received ' || CAST(received_date AS VARCHAR) || ' after due day ' || due_day"),
}

for name, (condition, details) in RULES.items():
    con.execute(f"""
        INSERT INTO fact_exception (source_file, row_number, member_id, rule_name, details)
        SELECT source_file, row_num, member_id, '{name}', {details}
        FROM base WHERE {condition}
    """)

print(con.sql("SELECT rule_name, count(*) AS n FROM fact_exception GROUP BY 1 ORDER BY 2 DESC"))

# Measure detection against the injected-error answer key
truth = (pd.read_csv("data/truth/injected_errors.csv")
           .rename(columns={"file": "source_file"}).drop_duplicates())
flagged = (con.execute("SELECT source_file, member_id, rule_name FROM fact_exception").df()
              .drop_duplicates())
keys = ["source_file", "member_id", "rule_name"]
hits = truth.merge(flagged, on=keys)
tested = flagged[flagged.rule_name.isin(truth.rule_name.unique())]
tp = len(tested.merge(truth, on=keys))
print(f"Recall:    {len(hits)}/{len(truth)} = {len(hits)/len(truth):.0%}")
print(f"Precision: {tp}/{len(tested)} = {tp/len(tested):.0%}")
con.close()