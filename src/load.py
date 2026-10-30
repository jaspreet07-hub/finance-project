import duckdb

con = duckdb.connect("data/pipeline.duckdb")

# Load every row except those quarantined. Late rows are valid, just flagged.
# INSERT OR REPLACE keyed on (member_id, period_month) makes reruns safe.
con.execute("""
    INSERT OR REPLACE INTO fact_contribution
    SELECT s.member_id, s.employer_id, s.period_month,
           s.employee_amount, s.employer_amount, s.received_date, s.source_file
    FROM stg_contribution s
    WHERE NOT EXISTS (
        SELECT 1 FROM fact_exception x
        WHERE x.source_file = s.source_file
          AND x.row_number  = s.row_num
          AND x.rule_name  <> 'LATE_SUBMISSION'
    )
""")

staged      = con.execute("SELECT count(*) FROM stg_contribution").fetchone()[0]
loaded      = con.execute("SELECT count(*) FROM fact_contribution").fetchone()[0]
quarantined = con.execute("""
    SELECT count(DISTINCT source_file || '-' || row_number)
    FROM fact_exception WHERE rule_name <> 'LATE_SUBMISSION'
""").fetchone()[0]

print(f"staged={staged} loaded={loaded} quarantined={quarantined}")
print("Reconciles" if staged == loaded + quarantined else "MISMATCH: investigate")
con.close()