-- Transact-SQL Scalar Function Syntax
CREATE OR REPLACE FUNCTION calculate_trip_distance (@start_station_id STRING, @end_station_id STRING)
RETURNS FLOAT
AS 
BEGIN 
	DECLARE --Declares the data validation variables and the trip_distance variable
		@trip_distance FLOAT,
		@start_station_exists STRING,
        @end_station_exists STRING
	SELECT @start_station_exists = COUNT(*),@end_station_exists = COUNT(*) --Validates that the stations exist
	FROM dim_stations
	WHERE start_station_exists = @start_station_id AND end_station_exists = @end_station_id
	IF @start_station_exists = 0 OR @end_station_exists = 0
		SET @trip_distance = -1 -- Returns a negative value if station Ids do not exist

	ELSE --Calculates the distance between the two points
		BEGIN 
			SELECT @trip_distance = ASIN( SQRT(
            SIN(RADIANS(end_station_id.latitude-start_station_id.latitude)/2)^2 
                + (
                    (sin(radians(end_station_id.longitude-start_station_id.longitude)/2)^2) *
                    cos(radians(start_station_id.latitude)) *
                    cos(radians(end_station_id.latitude))
                )
          )
        ) * cast('7926.3352' as float) * cast('0.8684' as float)
            FROM dim_stations
		END
RETURN trip_distance
END;