This lays out the schema for the data warehouse in BigQuery for Divvybikes

models:
 -name: fact_trips
 -description: Fact table of all the rides in the month downloaded from divvybikes

 -name: dim_stations
 -description: Contains the id of each station, is updated once a month to account for station construction/changes. 


 -name: weekly_trips
 -description: Aggregates the amounts of rides started and ended at each station to rank the stations in order of popularity

 airflow dags backfill divvybikes_elt_pipeline -s 2021-11-01 -e 2021-01-02 
 airflow dags backfill \
    --start-date 2021-11-01 \
    --end-date 2021-01-02  \
    divvybikes_elt_pipeline