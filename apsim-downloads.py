#!pip install pycountry
#!pip install requests
#!pip install pycountry-convert
# On Windows, download and install basemap and pyproj from here:
# https://www.lfd.uci.edu/~gohlke/pythonlibs
#!pip install pyproj-2.1.3-cp36-cp36m-win_amd64.whl
#!pip install basemap-1.2.0-cp36-cp36m-win_amd64.whl

# Basemap package generates deprecated warnings. This is good to know,
# but for now I don't plan on switching to a different package any time
# soon so for now just ignore these warnings.
import warnings
warnings.filterwarnings('ignore')
import pycountry_convert
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
import datetime as dt
from dateutil.relativedelta import relativedelta
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

def graph_downloads_for_country(title, downloads, dates, country, filename):
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
    plt.title(title % country)
    plt.xlabel('Date')
    plt.ylabel('Cumulative number of downloads')
    plt.grid(True)
    plt.savefig(filename)
    plt.clf()
    
def graph_downloads(title, downloads, dates, filename):
    x = []
    y = []
    for dt in dates:
        current_date = dt.__str__()
        downloads_before_now = downloads[downloads['Date'] < current_date]
        x.append(dt)
        y.append(len(downloads_before_now))
    
    plt.clf()
    plt.plot(x, y)
    plt.title(title)
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

def get_colour_index(x):
    colours = mpl.colors.CSS4_COLORS
    if x == 0:
        return 0
    if x < 500:
        return 1
    if x < 1000:
        return 2
    if x < 1500:
        return 3

    return 4

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

        # Blue colour scheme from ColorBrewer 2.0
        scheme = ['#ffffff','#d3eec9','#addfa4','#7ac77c','#49751f']

        # Iterate through states/countries in the shapefile.
        for info, shape in zip(m.units_info, m.units):
            iso3 = info['ADM0_A3'] # this gets the iso alpha-3 country code
            if iso3 in data.index:
                num_downloads = data.loc[iso3][cols[0]]
            else:
                num_downloads = 0

            #axis_max = max_num_downloads 
            color = scheme[get_colour_index(num_downloads)]
            
            # Fill this state/country with colour.
            patches = [Polygon(numpy.array(shape), True)]
            pc = PatchCollection(patches)
            pc.set_facecolor(color)
            ax.add_collection(pc)

        # Draw colour legend beneath map.
        if len(fig.axes) < 2:
            ax_legend = fig.add_axes([0.35, 0.14, 0.3, 0.03], zorder = 3)

            labels = [str(l) for l in axis_tick_labels]
            labels[len(labels) - 1] = '>' + labels[len(labels) - 1]
            
            ticks = [0, 500, 1000, 1500, max_num_downloads]
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

# Return true iff a country is in Africa
def isInAfrica(country):
    country_code = pycountry_convert.country_name_to_country_alpha2(country, cn_name_format="default")
    print('Checking continent for country %s (%s)' % (country, country_code))
    if (country_code == 'AQ'):
        return False # Antarctica - apparently it's not a continent???
    continent_name = ""
    try:
        pycountry_convert.country_alpha2_to_continent_code(country_code)
    except:
        continent_name = ""
        
    return continent_name == 'AF'

def filter(dataframe, field, value):
    return dataframe[dataframe[field] == value]
    
# Filter the dataframe by the given expression
# @param dataframe: the dataframe to be filtered
# @param field: field (column) name in the dataframe to be filtered
# @param filterfunc: function which takes a string and returns a bool
def filterLambda(dataframe, field, filterfunc):
    return dataframe[dataframe[field].apply(filterfunc)]

def print_stats(data):
    num_regos = len(filter(data, 'Type', 'Registration'))
    num_upgrades = len(filter(data, 'Type', 'Upgrade'))
    au = filter(data, 'Country', 'Australia')
    num_au_classic = len(filter(au, 'Product', 'APSIM'))
    num_au_nextgen = len(au[au['Product'].str.contains('APSIM Next Generation')])

    nz = filter(data, 'Country', 'New Zealand')
    num_nz_classic = len(filter(nz, 'Product', 'APSIM'))
    num_nz_nextgen = len(nz[nz['Product'].str.contains('APSIM Next Generation')])

    us = filter(data, 'Country', 'United States of America')
    num_us_classic = len(filter(us, 'Product', 'APSIM'))
    num_us_nextgen = len(us[us['Product'].str.contains('APSIM Next Generation')])

    china = filter(data, 'Country', 'China')
    num_china_classic = len(filter(china, 'Product', 'APSIM'))
    num_china_nextgen = len(china[china['Product'].str.contains('APSIM Next Generation')])

    africa = filterLambda(data, 'Country', isInAfrica)
    num_africa_classic = len(filter(africa, 'Product', 'APSIM'))
    num_africa_nextgen = len(africa[africa['Product'].str.contains('APSIM Next Generation')])

    num_classic = len(filter(data, 'Product', 'APSIM'))
    # Some older version of next gen write their version into the product column
    # Therefore we need to do a string contains rather than equality check.
    num_nextgen = len(data[data['Product'].str.contains('APSIM Next Generation')])

    print('')
    print('Copy the stats below into Graphs.xlsx')
    print('APSIM Download/Registration statistics %s to %s' % (start_date_str, end_date_str))
    print('-------------------------------------------------------------------')
    print('Number of downloads (upgrades + registrations): %d' % len(data))
    print('Number of registrations:                        %d' % num_regos)
    print('Number of upgrades:                             %d' % num_upgrades)
    print('Number of downloads (classic):                  %d' % num_classic)
    print('Number of downloads (next gen):                 %d' % num_nextgen)
    print('Number of countries with registered downloads:  %d' % len(data.Country.unique()))
    print('Number of downloads from Australia (classic):   %d' % num_au_classic)
    print('Number of downloads from Australia (nextgen):   %d' % num_au_nextgen)
    print('Number of downloads from New Zealand (classic): %d' % num_nz_classic)
    print('Number of downloads from New Zealand (nextgen): %d' % num_nz_nextgen)
    print('Number of downloads from USA (classic):         %d' % num_us_classic)
    print('Number of downloads from USA (nextgen):         %d' % num_us_nextgen)
    print('Number of downloads from China (classic):       %d' % num_china_classic)
    print('Number of downloads from China (nextgen):       %d' % num_china_nextgen)
    print('Number of downloads from Africa (classic):      %d' % num_africa_classic)
    print('Number of downloads from Africa (nextgen):      %d' % num_africa_nextgen)

# ------------------------------------------------------------------- #
# --------------------------- Main Program -------------------------- #
# ------------------------------------------------------------------- #

# ----- Constants ----- #

# Raw data will be saved to this file
downloads_fileName = 'registrations.csv'
#downloads_filename = get_temp_filename()

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

# Downloads are shown for time period starting on 1 July of this year.
start_date_str = '2020-01-01'

# Downloads are shown for time period ending on 30 June of this year.
end_date_str = '2020-12-31'

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

# Read command line.
if(len(sys.argv) == 3) :
	start_date_str = sys.argv[1]
	end_date_str = sys.argv[2]

print('You need to manually download registrations and store in registrations.csv')

# Title above the map.
map_title = 'Number of APSIM downloads by country %s to %s' % (start_date_str, end_date_str)

# If using cache, just rebuild gif and exit.
if use_cache:
    rebuild_gif(gif_file, cache)
    sys.exit(0)

# Get downloads info from web service.
downloads = pandas.read_csv(downloads_fileName, quotechar = '"', escapechar = '\\', doublequote = True)

# Only want APSIM downloads, not APSoil etc...
downloads = downloads[downloads['Product'].str.contains('APSIM')]

#downloads = downloads[downloads['Country'] != 'Australia']

# Determine date range
first_date = min(downloads['Date'], key = lambda x: time.strptime(x, date_format))
last_date = max(downloads['Date'], key = lambda x: time.strptime(x, date_format))

dates = [x.date() for x in pandas.date_range(first_date, last_date, freq = 'MS')]

# Get a dict, mapping country names to country codes
country_codes_lookup = get_codes_lookup()

graph_downloads('APSIM Downloads', downloads, dates, 'downloads-all.png')
graph_downloads_for_country('APSIM Downloads: %s', downloads, dates, 'United States of America', 'downloads-us.png')
graph_downloads_for_country('APSIM Downloads: %s', downloads, dates, 'Brazil', 'downloads-brazil.png')
graph_downloads_for_country('APSIM Downloads: %s', downloads, dates, 'Australia', 'downloads-australia.png')
graph_downloads_for_country('APSIM Downloads: %s', downloads, dates, 'China', 'downloads-china.png')

# Only want APSIM Next Gen downloads
nextgen = downloads[downloads['Product'].str.contains('APSIM Next Generation')]
graph_downloads('APSIM Next Generation Downloads', nextgen, dates, 'downloads-all-nextgen.png')
graph_downloads_for_country('APSIM Next Generation Downloads: %s', nextgen, dates, 'United States of America', 'downloads-us-nexgen.png')
graph_downloads_for_country('APSIM Next Generation Downloads: %s', nextgen, dates, 'Brazil', 'downloads-brazil-nextgen.png')
graph_downloads_for_country('APSIM Next Generation Downloads: %s', nextgen, dates, 'Australia', 'downloads-australia-nextgen.png')
graph_downloads_for_country('APSIM Next Generation Downloads: %s', nextgen, dates, 'China', 'downloads-china-nextgen.png')

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

downloads_in_timeframe = downloads[(downloads['Date'] >= start_date_str) & (downloads['Date'] <= end_date_str)]
print_stats(downloads_in_timeframe)
build_static_image(downloads_in_timeframe, desc, 'apsim-downloads.png')
#generate_animation()
#
# Generate downloads by year table.

print('Year, NumClassic, NumNextGen')
start_date = dt.datetime.strptime(start_date_str, '%Y-%m-%d')
end_date = dt.datetime.strptime(end_date_str, '%Y-%m-%d')
while (start_date <= end_date):
  end_year = dt.datetime(start_date.year, 12, 31)
  data = downloads[(downloads['Date'] >= start_date.strftime('%Y-%m-%d')) & (downloads['Date'] <= end_year.strftime('%Y-%m-%d'))]

  num_classic = len(filter(data, 'Product', 'APSIM'))
  num_nextgen = len(data[data['Product'].str.contains('APSIM Next Generation')])

  print(f'{start_date.year}, {num_classic}, {num_nextgen}')
  start_date = start_date + relativedelta(years=1)

