#!/bin/ash
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE TABLE public.noaa_daily
    (
    record_date date NOT NULL,
    station_id text COLLATE pg_catalog."default" NOT NULL,
    datatype text COLLATE pg_catalog."default" NOT NULL,
    attributes text COLLATE pg_catalog."default",
    value double precision NOT NULL,
    CONSTRAINT noaa_daily_pkey PRIMARY KEY (record_date, station_id, datatype)
    )
    WITH (
        OIDS = FALSE
    )
    TABLESPACE pg_default;

    ALTER TABLE public.noaa_daily
        OWNER to crobin;

    CREATE TABLE public.noaa_station
    (
        station_id text COLLATE pg_catalog."default" NOT NULL,
        name text COLLATE pg_catalog."default",
        latitude double precision,
        longitude double precision,
        elevation double precision,
        elevation_unit text COLLATE pg_catalog."default",
        mindate date,
        maxdate date,
        datacoverage double precision,
        CONSTRAINT noaa_station_pkey PRIMARY KEY (station_id)
    )
    WITH (
        OIDS = FALSE
    )
    TABLESPACE pg_default;

    ALTER TABLE public.noaa_station
        OWNER to crobin;
EOSQL
