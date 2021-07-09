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
import math
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
from enum import Enum

class ColourDistribution(Enum):
    Linear = 0
    Polynomial = 1
    Exponential = 2

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
def get_colour_scheme(data, colour_scheme, distribution):
    # Get the number of downloads from the country with the greatest
    # number of downloads.
    max_num_downloads = pandas.value_counts(data['Country'].values).max()
    if data.empty:
        max_num_downloads = 0

    num_colours = max_num_downloads + 1
    colour_map = plt.get_cmap(colour_scheme)

    if distribution == ColourDistribution.Linear:
        scheme = [colour_map(i) for i in axis_ticks]
    elif distribution == ColourDistribution.Polynomial:
        scheme = [colour_map(math.sqrt(math.sqrt(i))) for i in axis_ticks]
    elif distribution == ColourDistribution.Exponential:
        scheme = [colour_map(math.exp(-i)) for i in axis_ticks]
    else:
        raise ValueError('Unknown colour distribution type %s' % distribution)

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
            print('\rWorking: ', '%.2f' % (progress * 100), '%; eta = ', '%.2fs' % eta, sep = '', end = '')
        else:
            print('\rWorking: ', '%.2f' % (progress * 100), '%', sep = '', end = '')
        file = cache_dir + '/' + file
        images.append(imageio.imread(file))
        i += 1
    print('\rWorking: 100.00%; eta = 0.00s\nWriting animation to disk...')
    imageio.mimsave(gif_file, images)

def graph_downloads_for_country(downloads, dates, country, filename):
    downloads = downloads[downloads['Country'] == country]
    x = []
    y = []
    for dt in dates:
        current_date = dt.__str__()
        downloads_before_now = downloads[downloads['Date'] < current_date]
        x.append(dt)
        y.append(len(downloads_before_now))
    
    plt.clf()
    plt.plot(x, y)
    plt.title('%s APSIM Downloads over time' % country)
    plt.xlabel('Date')
    plt.ylabel('Cumulative number of downloads')
    plt.grid(True)
    plt.savefig(filename)
    plt.clf()

def get_colour(colours, x):
    if len(colours) < 1:
        raise ValueError("No colours provided in colours array")
    if len(colours) != len(axis_ticks):
        raise ValueError("Length of colours array not equal to length of axis ticks array")

    for tick, colour in zip(axis_ticks, colours):
        if x <= tick:
            return colour
            
    return colours[len(colours) - 1]

def get_colour_greg(x):
    colours = mpl.colors.CSS4_COLORS
    if x == 0:
        return colours['white']
    if x < 300:
        return colours['skyblue']
    if x < 600:
        return colours['royalblue']
    if x < 900:
        return colours['yellow']
    if x < 1200:
        return colours['lime']
    if x < 1500:
        return colours['orange']

    return colours['red']

def build_static_image(download_data, description, filename):
    # Get country codes
        country_codes, unknown_countries = get_country_codes(download_data['Country'], country_codes_lookup)

        # Create a data frame containing country code, and num downloads.
        cols = ['Number of Downloads']
        data = pandas.DataFrame.from_dict(country_codes, orient = 'index', columns = cols)
        data.index.names = ['Country Code']
        data = data.sort_values(cols[0], ascending = False)
        mpl.style.use(graph_style)

        max_num_downloads = data[cols[0]].max()

        fig.suptitle(map_title, fontsize = 30, y = 0.95)

        # Iterate through states/countries in the shapefile.
        for info, shape in zip(m.units_info, m.units):
            iso3 = info['ADM0_A3'] # this gets the iso alpha-3 country code
            if iso3 in data.index:
                num_downloads = data.loc[iso3][cols[0]]
            else:
                num_downloads = 0

            #axis_max = max_num_downloads 
            #color = get_colour(colours, num_downloads / axis_max)
            color = get_colour_greg(num_downloads)
            
            # Fill this state/country with colour.
            patches = [Polygon(numpy.array(shape), True)]
            pc = PatchCollection(patches)
            pc.set_facecolor(color)
            ax.add_collection(pc)

        # Draw colour legend beneath map.
        if len(fig.axes) < 2:
            ax_legend = fig.add_axes([0.35, 0.14, 0.3, 0.03], zorder = 3)

            colours = mpl.colors.CSS4_COLORS
            scheme = [colours['white'], colours['skyblue'], colours['royalblue'], colours['yellow'], colours['lime'], colours['orange'], colours['red']]

            labels = [str(l) for l in axis_tick_labels]
            labels[len(labels) - 1] = '>' + labels[len(labels) - 1]
            
            #ticks = [0, 200, 500, 1000, 2000, 7000, max_num_downloads]
            ticks = [0, 300, 600, 900, 1200, 1500, max_num_downloads]
            labels = [str(x) for x in ticks]
            labels[len(labels) - 1] = ''
            labels.insert(0, '')
            actual_ticks = numpy.linspace(0, 1, len(ticks))
            cmap = []
            for value, colour in zip(actual_ticks, scheme):
                cmap.append((value, colour))

            actual_ticks = numpy.linspace(0, 1, len(ticks) + 1)
            cm = mpl.colors.LinearSegmentedColormap.from_list('custom', cmap, len(cmap))
            cb = mpl.colorbar.ColorbarBase(ax_legend, cmap = cm, orientation = 'horizontal')
            
            cb.set_ticks(actual_ticks)
            cb.set_ticklabels(labels)

        # Add the description beneath the map.
        if description != '':
            plt.annotate(description, xy = (-0.8, -3.2), size = 14, xycoords = 'axes fraction')

        # Write the map to disk.
        plt.savefig(filename, bbox_inches = 'tight', pad_inches = 0.2)

def filter(dataframe, field, value):
    return dataframe[dataframe[field] == value]

def print_stats(data):
    num_regos = len(filter(data, 'Type', 'Registration'))
    num_upgrades = len(filter(data, 'Type', 'Upgrade'))
    num_au = len(filter(data, 'Country', 'Australia'))
    num_nz = len(filter(data, 'Country', 'New Zealand'))
    num_us = len(filter(data, 'Country', 'United States of America'))
    num_china = len(filter(data, 'Country', 'China'))

    num_classic = len(filter(data, 'Product', 'APSIM'))
    # Some older version of next gen write their version into the product column
    # Therefore we need to do a string contains rather than equality check.
    num_nextgen = len(data[data['Product'].str.contains('APSIM Next Generation')])

    print('APSIM Download/Registration statistics for 2019/20 financial year')
    print('-----------------------------------------------------------------')
    print('Number of downloads (upgrades + registrations): %d' % len(data))
    print('Number of registrations: %d' % num_regos)
    print('Number of upgrades: %d\n' % num_upgrades)

    print('Number of downloads (classic):  %d' % num_classic)
    print('Number of downloads (next gen): %d\n' % num_nextgen)

    print('Number of countries with registered downloads: %d' % len(data.Country.unique()))
    print('Number of downloads from Australia: %d' % num_au)
    print('Number of downloads from New Zealand: %d' % num_nz)
    print('Number of downloads from USA: %d' % num_us)
    print('Number of downloads from China: %d\n' % num_china)

# ------------------------------------------------------------------- #
# --------------------------- Main Program -------------------------- #
# ------------------------------------------------------------------- #

# ----- Constants ----- #

# Raw data will be saved to this file
downloads_fileName = 'registrations.csv'
#downloads_filename = get_temp_filename()

registrations_url = 'https://apsimdev.apsim.info/APSIM.Registration.Portal/ViewRegistrations.aspx'

date_format = '%Y-%m-%d'

# We use the 'Equidistant Cylindrical Projection' projection type.
# Another good alternative is the 'Robinson Projection'.
# https://matplotlib.org/basemap/users/mapsetup.html
map_type = 'cyl'

# We will use the yellow-orange-red colour scheme. Alternatives here:
# https://matplotlib.org/3.1.0/gallery/color/colormap_reference.html
colour_scheme = 'jet'

# Colour distribution algorithm. Polynomial tends to work best.
colour_distribution = ColourDistribution.Polynomial

# Iff true, use discrete colour blocks
discrete_colours = True

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
map_title = 'Number of APSIM downloads by country in 2019/20'

# Long description below the map.
map_description = ''

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
    sys.exit(0)

# Get downloads info from web service.
downloads = get_downloads(registrations_url, downloads_fileName)
#downloads = downloads[downloads['Country'] != 'Australia']

# Determine date range
first_date = min(downloads['Date'], key = lambda x: time.strptime(x, date_format))
last_date = max(downloads['Date'], key = lambda x: time.strptime(x, date_format))

dates = [x.date() for x in pandas.date_range(first_date, last_date, freq = 'MS')]

# Get a dict, mapping country names to country codes
country_codes_lookup = get_codes_lookup()

graph_downloads_for_country(downloads, dates, 'United States of America', 'downloads-us.png')
graph_downloads_for_country(downloads, dates, 'Brazil', 'downloads-brazil.png')

axis_max = 1000
axis_ticks = [0.05, 0.1, 0.15, 0.2, 0.3, 0.4, 0.6, 0.8, 1] #numpy.linspace(0, 1, num_ticks)
num_ticks = len(axis_ticks)
axis_tick_labels = [0, 200, 500, 1000, 2000, 7000] #numpy.linspace(0, axis_max, num_ticks + 1, dtype = int)

# Calculate the colour scheme
colours = get_colour_scheme(downloads, colour_scheme, colour_distribution)
cmap = mpl.colors.ListedColormap(colours, N = num_ticks if discrete_colours else len(colours))

# images is the array of images which will be used in the gif
images = []
i = 0

fig = plt.figure(figsize = (22, 12))
ax = fig.add_subplot(111, frame_on = False)

m = Basemap(lon_0 = 0, projection = map_type)
m.drawmapboundary(color = 'w')
m.readshapefile(shapefile, 'units', color = '#444444', linewidth = 0.2)

desc = 'Generated on %s' % time.strftime(date_format, time.localtime())
#desc += '\n%s colour scheme with %s colour distribution' % (colour_scheme, colour_distribution)

start_date_str = '2019-07-01'
end_date_str = '2020-06-30'

downloads_in_timeframe = downloads[(downloads['Date'] > start_date_str) & (downloads['Date'] < end_date_str)]
print_stats(downloads_in_timeframe)
build_static_image(downloads_in_timeframe, desc, 'apsim-downloads.png')
#generate_animation()