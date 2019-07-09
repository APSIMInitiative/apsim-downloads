#!pip install pycountry
#!pip install requests
# On Windows, download and install basemap and pyproj from here:
# https://www.lfd.uci.edu/~gohlke/pythonlibs
#!pip install pyproj-2.1.3-cp36-cp36m-win_amd64.whl
#!pip install basemap-1.2.0-cp36-cp36m-win_amd64.whl

# Basemap package generates deprecated warnings. This is good to know,
# but for now I don't plan on switching to a different package any time
# soon so for now just ignore these warnings.
import warnings
warnings.filterwarnings('ignore')

import imageio
import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy
import os
import pandas
import requests
import sys
import tempfile
import time
import unicodedata
#import warnings

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

# Generates the colour scheme
def get_colour_scheme(data, colour_scheme):
    # Get the number of downloads from the country with the greatest
    # number of downloads.
    max_num_downloads = pandas.value_counts(data['Country'].values).max()
    if data.empty:
        max_num_downloads = 0

    # Generate colour map - indices go from 0..max_num_downloads.
    num_colours = max_num_downloads + 1
    colour_map = plt.get_cmap(colour_scheme)
    scheme = [colour_map(i / num_colours) for i in range(num_colours)]

    return scheme

# Individual frames are saved as apsim-downloads_xxx.png, where xxx is
# a number. This function returns this number.
def get_image_number(filename):
    return int(os.path.splitext(filename)[0].split('_')[1])

# Builds the gif by appending all frames in the output directory.
def rebuild_gif(filename, cache_dir):
    image_names = [f for f in os.listdir(cache_dir) if os.path.isfile(os.path.join(cache_dir, f))]
    image_names.sort(key = lambda x: get_image_number(x))
    images = []

    start_time = time.time()
    i = 0

    for file in image_names:
        progress = i / len(image_names)
        if i > 0: # Only show time remaining if i > 0
            elapsed = time.time() - start_time
            eta = elapsed / progress - elapsed
            print('Working: ', '%.2f' % (progress * 100), '%; eta = ', '%.2fs' % eta, sep = '')
        else:
            print('Working: ', '%.2f' % (progress * 100), '%', sep = '')
        file = cache_dir + '/' + file
        images.append(imageio.imread(file))
        i += 1
    print('Done. Writing animation disk...')
    imageio.mimsave(gif_file, images)

# ------------------------------------------------------------------- #
# --------------------------- Main Program -------------------------- #
# ------------------------------------------------------------------- #

# ----- Constants ----- #

# Raw data will be saved to this file
downloads_fileName = 'registrations.csv'
#downloads_filename = get_temp_filename()

registrations_url = 'https://www.apsim.info/APSIM.Registration.Portal/ViewRegistrations.aspx'

date_format = '%Y-%m-%d'

# We use the 'Equidistant Cylindrical Projection' projection type.
# Another good alternative is the 'Robinson Projection'.
# https://matplotlib.org/basemap/users/mapsetup.html
map_type = 'cyl'

# We will use the yellow-orange-red colour scheme. Alternatives here:
# https://matplotlib.org/3.1.0/gallery/color/colormap_reference.html
colour_scheme = 'jet'

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
map_description = ''

# Number of ticks shown in the axis scale.
num_ticks = 8

# Cache directory. Each 'frame' (an image) will be saved here.
cache = 'output'

# File to which the map will be written.
map_file = cache + '/apsim-downloads'

# gif filename
gif_file = 'apsim-downloads.gif'

# if set to false, we will re-download data from the webservice and
# recreate all images.
use_cache = False

# ----- End Constants ----- #

# If using cache, just rebuild gif and exit.
if use_cache:
    rebuild_gif(gif_file, cache)
    sys.exit()

# Get downloads info from web service.
downloads = get_downloads(registrations_url, downloads_fileName)

# Determine date range
first_date = min(downloads['Date'], key = lambda x: time.strptime(x, date_format))
last_date = max(downloads['Date'], key = lambda x: time.strptime(x, date_format))

dates = [x.date() for x in pandas.date_range(first_date, last_date, freq = 'MS')]

# Get a dict, mapping country names to country codes
country_codes_lookup = get_codes_lookup()

# Calculate the colour scheme
colours = get_colour_scheme(downloads, colour_scheme)

# images is the array of images which will be used in the gif
images = []
i = 0

fig = plt.figure(figsize = (22, 12))
ax = fig.add_subplot(111, frame_on = False)

m = Basemap(lon_0 = 0, projection = map_type)
m.drawmapboundary(color = 'w')
m.readshapefile(shapefile, 'units', color = '#444444', linewidth = 0.2)

# Dict mapping country codes to cumulative number of downloads in that
# country as of last month.
downloads_prev = {}

# Dict mapping country map coordinate info to patch info.
country_patches = {}

# Initialise a stopwatch for output diagnostics.
start_time = time.time()

cum_downloads_us = {}
us_downloads_x = []
us_downloads_y = []
for dt in dates:
    t1 = time.time() # Used to record the duration of each iteration
    progress = i / len(dates)
    if i > 0: # Only show time remaining if i > 0
        elapsed = time.time() - start_time
        eta = elapsed / progress - elapsed
        print('Working: ', '%.2f' % (progress * 100), '%; eta = ', '%.2fs' % eta, sep = '')
    else:
        print('Working: ', '%.2f' % (progress * 100), '%', sep = '')
    # Each time around the loop, we only look at downloads before the current date.
    current_date = dt.__str__()
    downloads_before_now = downloads[downloads['Date'] < current_date]

    # Get country codes
    country_codes, unknown_countries = get_country_codes(downloads_before_now['Country'], country_codes_lookup)

    # Create a data frame containing country code, and num downloads.
    cols = ['Number of Downloads']
    data = pandas.DataFrame.from_dict(country_codes, orient = 'index', columns = cols)
    data.index.names = ['Country Code']
    data = data.sort_values(cols[0], ascending = False)
    us_downloads_x.append(dt)
    us_downloads_y.append(len(downloads_before_now[downloads_before_now['Country'] == 'United States of America']))

    mpl.style.use(graph_style)

    title = map_title + ' - ' + dt.strftime('%b %Y')
    fig.suptitle(title, fontsize = 30, y = 0.95)

    # Iterate through states/countries in the shapefile.
    n = 0
    for info, shape in zip(m.units_info, m.units):
        iso3 = info['ADM0_A3'] # this gets the iso alpha-3 country code
        j = m.units.index(shape)
        if iso3 in data.index:
            num_downloads = data.loc[iso3][cols[0]]
            if iso3 not in downloads_prev or downloads_prev[iso3] != num_downloads:
                # Only update this country's data if it has changed since last month.
                downloads_prev[iso3] = num_downloads
                color = colours[num_downloads]

                # Fill this state/country with colour.
                if country_patches and j in country_patches:
                    pc = country_patches[j]
                    pc.set_facecolor(color)
                else:
                    patches = [Polygon(numpy.array(shape), True)]
                    pc = PatchCollection(patches)
                    pc.set_facecolor(color)
                    country_patches[j] = pc
                    ax.add_collection(pc)
                n += 1
    print('i = %d; n = %d' % (i, n))
    # Draw colour legend beneath map.
    ax_legend = fig.add_axes([0.35, 0.14, 0.3, 0.03], zorder = 3)
    cmap = mpl.colors.ListedColormap(colours)
    axis_ticks = numpy.linspace(0, 1, num_ticks)
    axis_tick_labels = numpy.linspace(0, len(colours) - 1, num_ticks, dtype = int)
    cb = mpl.colorbar.ColorbarBase(ax_legend, ticks = axis_ticks, cmap = cmap, orientation = 'horizontal')
    cb.set_ticks(axis_ticks)
    cb.set_ticklabels(axis_tick_labels)

    # Add the description beneath the map.
    if map_description != '':
        plt.annotate(map_description, xy = (-0.8, -3.2), size = 14, xycoords = 'axes fraction')

    # Write the map to disk.
    filename = map_file + '_' + str(i) + '.png'
    plt.savefig(filename, bbox_inches = 'tight', pad_inches = 0.2)
    images.append(imageio.imread(filename))
    i += 1
    print('Iteration duration = %.2fs' % (time.time() - t1))

print('Working: 100.00%')
print('Finished generating heatmaps. Building animation...')
imageio.mimsave(gif_file, images)

plt.plot(us_downloads_x, us_downloads_y)
plt.title('US APSIM Downloads over time')
plt.xlabel('Date')
plt.ylabel('Cumulative number of downloads')
plt.grid(True)
plt.savefig('downloads-us.png')
print('done')
