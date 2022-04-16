from datetime import datetime
import logging
import os
import zipfile
import string
from zipfile import ZipFile
from io import BytesIO
from airflow import DAG 
from google.cloud import storage
from airflow.models.connection import Connection
from airflow.exceptions import AirflowFailException
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator

from airflow.providers.google.cloud.operators.bigquery import BigQueryCreateExternalTableOperator, BigQueryExecuteQueryOperator, BigQueryInsertJobOperator, BigQueryUpsertTableOperator

import pyarrow.csv as pv
import pyarrow.parquet as pq

url_prefix = "https://divvy-tripdata.s3.amazonaws.com/"
zip_name = "202004-divvy-tripdata.zip"
file_name = zip_name.replace('.zip', '.csv')
url_template = url_prefix + file_name
bucket_name = "divvybikes-tripdata"
parquet_file = file_name.replace('.csv', '.parquet')
path_to_local_home = os.getenv("CSV_FILE_DIR", "/opt/airflow/dags/datasets/")

PROJECT_ID = os.environ.get("GCP_PROJECT_ID")
BUCKET = os.environ.get("GCP_GCS_BUCKET")
BIGQUERY_DATASET = os.environ.get("BIGQUERY_DATASET", 'divvybikes_data_all')
DATASET = "divvybikes"
INPUT_PART = "raw"
INPUT_FILETYPE = "parquet"

URL_PREFIX = "https://divvy-tripdata.s3.amazonaws.com/"
DIVVY_URL_TEMPLATE = URL_PREFIX + "{{ execution_date.strftime(\'%Y%m\')}}-divvy-tripdata.zip"
DIVVY_ZIP_FILE_TEMPLATE = path_to_local_home + "{{ execution_date.strftime(\'%Y%m\')}}-divvy-tripdata.zip"
DIVVY_CSV_FILE_TEMPLATE = path_to_local_home + "{{ execution_date.strftime(\'%Y%m\')}}-divvy-tripdata.csv"
DIVVY_PARQUET_FILE_TEMPLATE = path_to_local_home + "{{ execution_date.strftime(\'%Y%m\')}}-divvy-tripdata.parquet"
DIVVY_PARQUET_FILE_KEY_TEMPLATE = "{{ execution_date.strftime(\'%Y%m\')}}-divvy-tripdata.parquet"


def extract_csv_from_zip(zipped_file:string) -> None:
    zip_file = zipfile.ZipFile(zipped_file)
    zip_file.extractall(path_to_local_home)


def format_to_parquet(src_file, dest_file):
    if not src_file.endswith('.csv'):
        logging.error("Can only accept source files in CSV format, for the moment")
        return
    table = pv.read_csv(src_file)
    pq.write_table(table, dest_file)

def upload_to_gcs(bucket, object_name, local_file):
    """
    Ref: https://cloud.google.com/storage/docs/uploading-objects#storage-upload-object-python
    :param bucket: GCS bucket name
    :param object_name: target path & file-name
    :param local_file: source path & file-name
    :return:
    """
    # WORKAROUND to prevent timeout for files > 6 MB on 800 kbps upload speed.
    # (Ref: https://github.com/googleapis/python-storage/issues/74)
    storage.blob._MAX_MULTIPART_SIZE = 5 * 1024 * 1024  # 5 MB
    storage.blob._DEFAULT_CHUNKSIZE = 5 * 1024 * 1024  # 5 MB
    # End of Workaround

    client = storage.Client()
    bucket = client.bucket(bucket)

    blob = bucket.blob(object_name)
    blob.upload_from_filename(local_file)


default_args = {
    "owner": "airflow",
    "start_date": datetime(2020, 5, 1),
    "depends_on_past": False,
    "retries": 1,
    "catchup":True,
    "max_active_runs": 2
}


with DAG(
    dag_id="divvybikes_elt_pipeline",
    schedule_interval="@monthly",
    default_args=default_args,
    catchup=False,
    max_active_runs=1,
    tags=['divvybikes'],
    template_searchpath="/opt/airflow/dags/queries/"
) as dag:                          

    
    download_dataset = BashOperator(
        task_id="download_dataset",
        bash_command=f"curl -sSL {DIVVY_URL_TEMPLATE} > {DIVVY_ZIP_FILE_TEMPLATE}"
    )

    extract_csv = PythonOperator(
        task_id="extract_csv",
        python_callable=extract_csv_from_zip,
        op_kwargs={
            "zipped_file":f"{DIVVY_ZIP_FILE_TEMPLATE}"
        }
    )

    convert_file_to_parquet = PythonOperator(
        task_id="convert_file_to_parquet",
        python_callable=format_to_parquet,
        op_kwargs={
            "src_file":f"{DIVVY_CSV_FILE_TEMPLATE}",
            "dest_file":f"{DIVVY_PARQUET_FILE_TEMPLATE}"
        }
    )

    upload_to_gcs_task = PythonOperator(
        task_id="upload_to_gcs_task",
        python_callable=upload_to_gcs,
        op_kwargs={
            "bucket": BUCKET,
            "object_name": f"raw/{DIVVY_PARQUET_FILE_KEY_TEMPLATE}",
            "local_file": f"{DIVVY_PARQUET_FILE_TEMPLATE}",
        },
    )


    gcs_to_external_table_task = BigQueryCreateExternalTableOperator(
        task_id="gcs_to_external_table_Task",
        bucket=BUCKET,
        source_objects=["raw/*"],
        destination_project_dataset_table=f"{PROJECT_ID}.{BIGQUERY_DATASET}.external_table",
        source_format="PARQUET"
    )


    remove_files = BashOperator(
        task_id="remove_downloaded_files",
        bash_command=f"rm -f {DIVVY_CSV_FILE_TEMPLATE} {DIVVY_PARQUET_FILE_TEMPLATE} {DIVVY_ZIP_FILE_TEMPLATE} _MACOSX "
    )

    create_fact_trips_task = BigQueryInsertJobOperator(
    task_id="create_fact_trips_table",
    configuration={
        "query": {
            "query": "{% include 'fact_trips.sql' %}",
            "useLegacySql": False,
        }
    }
    )

    clean_trips_task = BigQueryExecuteQueryOperator(
        task_id="clean_fact_trips_table",
        sql = 'clean_trips.sql',
        use_legacy_sql = False
    )

    upsert_dim_stations_task = BigQueryUpsertTableOperator(
    task_id="upsert_dim_stations_table",
    dataset_id=BIGQUERY_DATASET,
    table_resource={
        "tableReference": {"tableId": "station_map_dim_table"},
        },
    )

    create_monthly_trips_task = BigQueryInsertJobOperator(
    task_id="create_monthly_trips_model",
    configuration={
        "query": {
            "query": "{% include 'monthly_trips.sql' %}",
            "useLegacySql": False,
        }
    }
    )


    download_dataset >> extract_csv >> convert_file_to_parquet >> upload_to_gcs_task >> remove_files >> gcs_to_external_table_task 
    gcs_to_external_table_task >> create_fact_trips_task >> clean_trips_task
    gcs_to_external_table_task >> upsert_dim_stations_task
    clean_trips_task >> create_monthly_trips_task
    upsert_dim_stations_task >> create_monthly_trips_task