DELETE FROM divvybikes_data_all.fact_trips
WHERE COALESCE (fact_trips.ride_end, fact_trips.ride_start) IS NULL;