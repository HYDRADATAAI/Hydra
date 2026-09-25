# HYDRA SQL Data Quality Sample

Status: **PUBLIC / SYNTHETIC / NON-LIVE**

A compact SQLite portfolio sample that extends HYDRA's public data-engineering evidence into SQL.

It demonstrates:

- relational schema design;
- CTEs;
- joins;
- window functions;
- aggregations;
- data-quality classification;
- duplicate detection;
- quality summary reporting;
- Python + SQL test automation.

The fixture is synthetic and does not represent live market data.

## Flow

`synthetic CSV -> raw table -> alias join -> normalized view -> quality checks -> accepted/quarantine views -> analytical summary`

## Run

```powershell
python run_demo.py
python -m unittest discover -s tests -v
```

Expected output:

- `build/hydra_sql_demo.db`
- `build/quality_summary.json`

This sample is career evidence for SQL/data-engineering fundamentals, not a production database or warehouse.
