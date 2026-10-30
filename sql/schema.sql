CREATE TABLE IF NOT EXISTS dim_employer (
  employer_id   VARCHAR PRIMARY KEY,
  employer_name VARCHAR,
  due_day       INTEGER            -- day of month contributions are due
);

CREATE TABLE IF NOT EXISTS dim_member (
  member_id      VARCHAR PRIMARY KEY,
  employer_id    VARCHAR REFERENCES dim_employer(employer_id),
  date_of_birth  DATE,
  join_date      DATE,
  status         VARCHAR,          -- ACTIVE / LEFT
  monthly_salary DECIMAL(12,2)
);

CREATE TABLE IF NOT EXISTS fact_contribution (
  member_id        VARCHAR,
  employer_id      VARCHAR,
  period_month     DATE,           -- first day of the contribution month
  employee_amount  DECIMAL(12,2),
  employer_amount  DECIMAL(12,2),
  received_date    DATE,
  source_file      VARCHAR,
  PRIMARY KEY (member_id, period_month)   -- enforces idempotent loads
);

CREATE TABLE IF NOT EXISTS fact_exception (
  source_file VARCHAR,
  row_number  INTEGER,
  member_id   VARCHAR,
  rule_name   VARCHAR,
  details     VARCHAR,
  detected_at TIMESTAMP DEFAULT current_timestamp
);
