from datetime import datetime
import os
import requests
from zipfile import ZipFile
from io import BytesIO

from airflow import DAG 
from google.cloud import storage
from airflow.models.connection import Connection
from airflow.exceptions import AirflowFailException
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator

from airflow.providers.google.cloud.operators.bigquery import BigQueryCreateExternalTableOperator

path_to_local_home = os.getenv("CSV_FILE_DIR", "/opt/airflow/dags/datasets/")
PROJECT_ID = os.environ.get("GCP_PROJECT_ID")
BUCKET = os.environ.get("GCP_GCS_BUCKET")
BIGQUERY_DATASET = os.environ.get("BIGQUERY_DATASET", 'divvybikes_data_all')

STATION_MAP_CSV_FILE_PATH = path_to_local_home + "Divvy_Bicycle_Stations_-_All_-_Map.csv"
STATION_MAP_CSV = "Divvy_Bicycle_Stations_-_All_-_Map.csv"
STATION_MAP_URL="https://data.cityofchicago.org/api/views/bk89-9dk7/rows.csv?accessType=DOWNLOAD"

def upload_to_gcs(bucket, object_name, local_file):
    # WORKAROUND to prevent timeout for files > 6 MB on 800 kbps upload speed.
    # (Ref: https://github.com/googleapis/python-storage/issues/74)
    storage.blob._MAX_MULTIPART_SIZE = 5 * 1024 * 1024  # 5 MB
    storage.blob._DEFAULT_CHUNKSIZE = 5 * 1024 * 1024  # 5 MB
    # End of Workaround

    client = storage.Client()
    bucket = client.bucket(bucket)

    blob = bucket.blob(object_name)
    blob.upload_from_filename(local_file)

def download_map_url():
    url = STATION_MAP_URL
    local_filename = STATION_MAP_CSV_FILE_PATH 
    # NOTE the stream=True parameter below
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(local_filename, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192): 
                f.write(chunk)
    return local_filename
   
default_args = {
    "owner": "airflow",
    "start_date": datetime(2020, 5, 1),
    "depends_on_past": False,
    "retries": 1,
    "catchup":True,
}


with DAG(
    dag_id="divvybikes_station_map_upload",
    schedule_interval="@monthly",
    default_args=default_args,
    catchup=False,
    max_active_runs=1,
    tags=['divvybikes'],
) as dag:                          
   
    download_map_url_task = PythonOperator(
        task_id="download_station_map",
        python_callable=download_map_url
    )

    upload_map_to_gcs_task = PythonOperator(
        task_id="upload_map_to_gcs_task",
        python_callable=upload_to_gcs,
        op_kwargs={
            "bucket": BUCKET,
            "object_name": f"{STATION_MAP_CSV}",
            "local_file": f"{STATION_MAP_CSV_FILE_PATH}",
        },
    )

    gcs_map_to_external_table_task =BigQueryCreateExternalTableOperator(
        task_id="gcs_map_to_external_table_Task",
        bucket=BUCKET,
        source_objects=[f"{STATION_MAP_CSV}"],
        destination_project_dataset_table= f"{PROJECT_ID}.{BIGQUERY_DATASET}.station_map_dim_table",
        schema_fields=[{"name": "station_id", "type": "STRING", "mode": "REQUIRED"},
               {"name": "station_name", "type": "STRING", "mode": "REQUIRED"},
               {"name": "total_docks", "type": "FLOAT", "mode": "NULLABLE"},
               {"name": "docks_in_service", "type": "FLOAT", "mode": "NULLABLE"},
               {"name": "status", "type": "STRING", "mode": "NULLABLE"},
               {"name": "latitude", "type": "FLOAT", "mode": "REQUIRED"},
               {"name": "longitude", "type": "FLOAT", "mode": "REQUIRED"},
               {"name": "location", "type": "STRING", "mode": "NULLABLE"}]
    )    


    download_map_url_task >> upload_map_to_gcs_task >> gcs_map_to_external_table_task