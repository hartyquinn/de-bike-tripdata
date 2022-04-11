CREATE OR REPLACE TABLE divvybikes_data_all.dm_weekly_trips(
    station STRING, 
    total_weekly_trips INT
)
AS
SELECT station_map_dim_table.station_name, COUNT (fact_trips.ride_id) AS total_weekly_trips
FROM divvybikes_data_all.fact_trips
INNER JOIN divvybikes_data_all.station_map_dim_table
    ON fact_trips.start_station_id = station_map_dim_table.station_id
GROUP BY 1
ORDER BY 2 DESC;