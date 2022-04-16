Data Modeling for the data warehouse in BigQuery for Divvybikes

    models:
    -name: fact_trips
        -description: Fact table of all the rides in the month downloaded from divvybikes
        -columns:
            -ride_id STRING: ID for each ride
            -bike_type STRING: categorizes the bike type as one of two
            -ride_start TIMESTAMP: ride start time, timestamped 
            -ride_end TIMESTAMP: ride end time, timestamped
            -start_station_name STRING: name of the ride starting station
            -start_station_id STRING: Id
            -end_station_name STRING: name of the ending ride station
            -end_station_id STRING: 
            -member_casual STRING: Whether or not the trip was taken by a member of divvybikes or a one time user 

    -name: dim_stations
        -description: Contains the id of each station, is updated once a month to account for station construction/changes. 

    -name: weekly_trips
        -description: Aggregates the amounts of rides started and ended at each station to rank the stations in order of popularity