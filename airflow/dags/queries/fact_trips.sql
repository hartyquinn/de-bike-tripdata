CREATE OR REPLACE TABLE divvybikes_data_all.fact_trips (
    ride_id STRING,
    bike_type STRING,
    ride_start TIMESTAMP,
    ride_end TIMESTAMP, 
    start_station_name STRING,
    start_station_id STRING,
    end_station_name STRING,
    end_station_id STRING,
    member_casual STRING
)
PARTITION BY TIMESTAMP_TRUNC(ride_start, DAY)
AS
SELECT 
ride_id,
rideable_type AS bike_type,
started_at AS ride_start,
ended_at AS ride_end, 
start_station_name,
start_station_id,
end_station_name,
end_station_id,
member_casual,

FROM divvybikes_data_all.external_table ;
