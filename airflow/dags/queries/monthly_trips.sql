CREATE OR REPLACE TABLE divvybikes_data_all.dm_monthly_trips(
    station STRING, 
    monthly_trips TIMESTAMP,
    total_monthly_trips INT,
    member_trips INT,
    casual_trips INT

)
AS
SELECT station_map_dim_table.station_name AS station,
TIMESTAMP_TRUNC(fact_trips.ride_start,month) AS monthly_trips,
COUNT (fact_trips.ride_id) AS total_monthly_trips,
COUNT(CASE WHEN fact_trips.member_casual = 'member' THEN 1 ELSE NULL END) AS member_trips,
COUNT(CASE WHEN fact_trips.member_casual = 'casual' THEN 1 ELSE NULL END) AS casual_trips
FROM divvybikes_data_all.fact_trips
INNER JOIN divvybikes_data_all.station_map_dim_table
    ON fact_trips.start_station_id = station_map_dim_table.station_id
GROUP BY 1,2
ORDER BY 3 DESC;