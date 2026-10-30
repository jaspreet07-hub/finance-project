from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator

default_args = {"retries": 2, "retry_delay": timedelta(minutes=2)}

with DAG(
    dag_id="contribution_recon",
    start_date=datetime(2026, 10, 1),
    schedule="0 6 * * *",          # daily at 06:00
    catchup=False,
    default_args=default_args,
) as dag:
    ingest   = BashOperator(task_id="ingest",   bash_command="python /opt/project/src/ingest.py")
    validate = BashOperator(task_id="validate", bash_command="python /opt/project/src/validate.py")
    load     = BashOperator(task_id="load",     bash_command="python /opt/project/src/load.py")

    ingest >> validate >> load