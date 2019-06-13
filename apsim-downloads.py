#!pip install pycountry
#!pip install requests
# On Windows, download and install basemap and pyproj from here:
# https://www.lfd.uci.edu/~gohlke/pythonlibs
#!pip install pyproj-2.1.3-cp36-cp36m-win_amd64.whl
#!pip install basemap-1.2.0-cp36-cp36m-win_amd64.whl

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy
import pandas
import unicodedata
import requests
import tempfile
from iso3166 import countries
from os import path
from matplotlib.patches import Polygon
from matplotlib.collections import PatchCollection
from mpl_toolkits.basemap import Basemap

# Generates a temp file name. Does not create a file on disk.
def get_temp_filename():
    return path.join(tempfile._get_default_tempdir(), next(tempfile._get_candidate_names()))

# returns a dict mapping ISO 3166 country names to country codes.
def get_codes_lookup():
    countriesMap = {}
    for country in countries:
        countriesMap[country.name] = country.alpha3
    return countriesMap

# Gets raw download information from the webservice.
def get_downloads(url, outfile):
    # Get download data from web service
    resp = requests.get(registrations_url)
    if not resp.status_code == 200:
        raise Exception('Error fetching data from webservice: status code = %d' % resp.status_code)
    
    with open(outfile, 'w', encoding = 'utf-8') as file:
        file.write(resp.text)
    
    return pandas.read_csv(downloads_fileName, quotechar = '"', escapechar = '\\', doublequote = True)

# Gets a dict mapping country code to number of downloads from an
# array of country names. Ignores any invalid (non ISO-3166 compliant)
# country names.
def get_country_codes(country_names, codes_lookup):
    #return [codes_lookup.get(country, 'Unknown code') for country in country_names]
    codes = {}
    unknown = []
    default = 'Unknown code'
    for country in country_names:
        code = codes_lookup.get(country, default)
        if code == default:
            if not country in unknown:
                print('Unknown country:', country)
                unknown.append(country)
        elif code in codes:
            codes[code] += 1
        else:
            codes[code] = 1
    return codes, unknown

# Generates a template SQL query to update the database to fix invalid
# country coedes.
def generate_sql(unknowns, filename):
    with open(filename, 'w', encoding = 'utf-8') as file:
        for country in unknowns:
            file.write("""UPDATE [APSIM.Registration].[dbo].[Registrations]
SET [Country] = ''
WHERE [Country] = '%s'\n\n""" % country.replace("'", "''"))
    print('Generated sql template at ', sql_file, sep = '')

# ------------------------------------------------------------------- #
# --------------------------- Main Program -------------------------- #
# ------------------------------------------------------------------- #

# ----- Constants ----- #

# Raw data will be saved to this file
downloads_fileName = 'registrations.csv'
#downloads_filename = get_temp_filename()

registrations_url = 'https://www.apsim.info/APSIM.Registration.Portal/ViewRegistrations.aspx'

# We use the 'Equidistant Cylindrical Projection' projection type.
# Another good alternative is the 'Robinson Projection'.
# https://matplotlib.org/basemap/users/mapsetup.html
map_type = 'cyl'

# We will use the yellow-orange-red colour scheme. Alternatives here:
# https://matplotlib.org/3.1.0/gallery/color/colormap_reference.html
colour_scheme = 'YlOrRd'

# Colour to use for countries with no downloads. Set to '' to use zero
# colour in colour scheme (yellow in the yellow-orange-red scheme).
default_colour = '#dddddd'

# We use the 'bmh' style because 'map' is unavailable on windows.
#print(mpl.style.available) # Uncomment to list all available styles
graph_style = 'bmh'

# This should point to a .shp file. Due to assumptions in the basemap
# library, this variable should *not* include the file extension.
shapefile = 'map_data/ne_10m_admin_0_countries'

# Title above the map.
map_title = 'Number of apsim downloads by country'

# Long description below the map.
map_description = 'Description goes here'

# File to which the map will be written.
map_file = 'apsim-downloads.png'

# ----- End Constants ----- #

# Get downloads info
downloads = get_downloads(registrations_url, downloads_fileName)

# Get country codes
country_codes_lookup = get_codes_lookup() # dict, mapping country names to country codes
country_codes, unknown_countries = get_country_codes(downloads['Country'], country_codes_lookup)

# ----- Remove ----- #
sql_file = 'fix_unknowns.txt'
if len(unknown_countries) > 0:
    generate_sql(unknown_countries, sql_file)
# ----- Remove ----- #

# Create a data frame containing country code, and num downloads.
cols = ['Number of Downloads']
data = pandas.DataFrame.from_dict(country_codes, orient = 'index', columns = cols)
data.index.names = ['Country Code']
data = data.sort_values(cols[0], ascending = False)
max_num_downloads = data[cols[0]].max()

# Generate colour map - indices go from 0..max_num_downloads.
num_colours = max_num_downloads + 1
colour_map = plt.get_cmap(colour_scheme)
scheme = [colour_map(i / num_colours) for i in range(num_colours)]

mpl.style.use(graph_style)

fig = plt.figure(figsize = (22, 12))
ax = fig.add_subplot(111, frame_on = False)
fig.suptitle(map_title, fontsize = 30, y = 0.95)

m = Basemap(lon_0 = 0, projection = map_type)
m.drawmapboundary(color = 'w')

m.readshapefile(shapefile, 'units', color = '#444444', linewidth = 0.2)
# Iterate through states/countries in the shapefile.
for info, shape in zip(m.units_info, m.units):
    iso3 = info['ADM0_A3'] # this gets the iso alpha-3 country code
    if iso3 not in data.index:
        # Zero downloads from this country.
        if not default_colour == '':
            color = default_colour
        else:
            color = scheme[0]
    else:
        color = scheme[data.loc[iso3][cols[0]]]
    
    # Fill this state/country with colour.
    patches = [Polygon(numpy.array(shape), True)]
    pc = PatchCollection(patches)
    pc.set_facecolor(color)
    ax.add_collection(pc)

# Draw colour legend beneath map.
ax_legend = fig.add_axes([0.35, 0.14, 0.3, 0.03], zorder = 3)
cmap = mpl.colors.ListedColormap(scheme)
axis_ticks = numpy.linspace(0, max_num_downloads, 8)
cb = mpl.colorbar.ColorbarBase(ax_legend, cmap = cmap, ticks = axis_ticks, boundaries = axis_ticks, orientation = 'horizontal')

# Add the description beneath the map.
plt.annotate(map_description, xy = (-0.8, -3.2), size = 14, xycoords = 'axes fraction')

# Write the map to disk.
plt.savefig(map_file, bbox_inches = 'tight', pad_inches = 0.2)