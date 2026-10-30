import os
import subprocess
import sys
from pathlib import Path

import duckdb
import pytest

ROOT = Path(__file__).resolve().parents[1]
DB = str(ROOT / "data" / "pipeline.duckdb")


def run(script):
    subprocess.run([sys.executable, str(ROOT / "src" / script)], cwd=ROOT, check=True,
                   capture_output=True, env={**os.environ, "PYTHONUTF8": "1"})


def q(sql):
    con = duckdb.connect(DB, read_only=True)
    try:
        return con.execute(sql).fetchall()
    finally:
        con.close()


@pytest.fixture(scope="session", autouse=True)
def pipeline():
    for s in ["generate.py", "ingest.py", "validate.py", "load.py"]:
        run(s)


def test_reconciliation():
    staged = q("SELECT count(*) FROM stg_contribution")[0][0]
    loaded = q("SELECT count(*) FROM fact_contribution")[0][0]
    quarantined = q("""SELECT count(DISTINCT source_file || '-' || row_number)
                       FROM fact_exception WHERE rule_name <> 'LATE_SUBMISSION'""")[0][0]
    assert staged == loaded + quarantined


def test_no_duplicate_keys():
    assert q("""SELECT count(*) FROM (SELECT 1 FROM fact_contribution
                GROUP BY member_id, period_month HAVING count(*) > 1)""")[0][0] == 0


def test_no_nulls():
    assert q("""SELECT count(*) FROM fact_contribution
                WHERE member_id IS NULL OR employer_id IS NULL OR period_month IS NULL
                   OR employee_amount IS NULL OR employer_amount IS NULL
                   OR received_date IS NULL""")[0][0] == 0


def test_loaded_members_are_known_active_and_match_employer():
    assert q("""SELECT count(*) FROM fact_contribution f
                LEFT JOIN dim_member m USING (member_id)
                WHERE m.member_id IS NULL OR m.status <> 'ACTIVE'
                   OR m.employer_id <> f.employer_id""")[0][0] == 0


def test_amounts_positive_and_within_limit():
    assert q("""SELECT count(*) FROM fact_contribution f
                JOIN dim_member m USING (member_id)
                WHERE f.employee_amount <= 0 OR f.employer_amount <= 0
                   OR f.employee_amount + f.employer_amount > 0.30 * m.monthly_salary""")[0][0] == 0


def test_load_is_idempotent():
    before = q("SELECT count(*) FROM fact_contribution")[0][0]
    run("load.py")
    assert q("SELECT count(*) FROM fact_contribution")[0][0] == before