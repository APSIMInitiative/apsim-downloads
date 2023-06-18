FROM python:3.11.2-slim-buster

# Install python packages
RUN pip install pycountry pycountry_convert requests pyproj basemap certifi imageio pandas iso3166


WORKDIR /wd
    
ENTRYPOINT ["python3", "apsim-downloads.py"]
