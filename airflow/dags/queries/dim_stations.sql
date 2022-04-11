CREATE OR REPLACE TABLE dim_stations
AS
SELECT 
station_id STRING PRIMARY KEY NOT NULL,
station_name STRING NOT NULL,
total_docks FLOAT NOT NULL,
latitude FLOAT NOT NULL,
longitude FLOAT NOT NULL 

FROM station_map_dim_table