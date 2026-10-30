from pathlib import Path

import duckdb

con = duckdb.connect("data/pipeline.duckdb", read_only=True)
by_rule = con.execute("SELECT rule_name, count(*) FROM fact_exception GROUP BY 1 ORDER BY 2 DESC, 1").fetchall()
by_emp = con.execute("SELECT substr(source_file, 1, 4), count(*) FROM fact_exception GROUP BY 1 ORDER BY 1").fetchall()
staged = con.execute("SELECT count(*) FROM stg_contribution").fetchone()[0]
loaded = con.execute("SELECT count(*) FROM fact_contribution").fetchone()[0]
quarantined = con.execute("""SELECT count(DISTINCT source_file || '-' || row_number)
    FROM fact_exception WHERE rule_name <> 'LATE_SUBMISSION'""").fetchone()[0]
con.close()

lines = ["# Pipeline summary", "",
         f"- Rows staged: {staged}", f"- Rows loaded: {loaded}",
         f"- Rows quarantined: {quarantined}",
         f"- Reconciliation: {'OK' if staged == loaded + quarantined else 'MISMATCH'}",
         "", "## Exceptions by rule", "", "| Rule | Count |", "|---|---|"]
lines += [f"| {r} | {n} |" for r, n in by_rule]
lines += ["", "## Exceptions by employer", "", "| Employer | Count |", "|---|---|"]
lines += [f"| {e} | {n} |" for e, n in by_emp]

Path("reports").mkdir(exist_ok=True)
Path("reports/summary.md").write_text("\n".join(lines), encoding="utf-8")
print("\n".join(lines))