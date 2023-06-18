# apsim-downloads

Maps apsim downloads by country

### Instructions

Build docker container:

docker build -t apsim-downloads .

Run:

docker run -it -v $PWD:/wd apsim-downloads 2015-01-01 2023-05-15

NOTE: Before running script you need to manually download and clean registrations.csv.

    