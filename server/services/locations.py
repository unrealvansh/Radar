import math
import re

NCR = 'Delhi NCR'

CITIES = {
    'New Delhi': (28.6139, 77.2090, NCR, ['new delhi']),
    'Delhi': (28.6519, 77.2315, NCR, ['delhi']),
    'Noida': (28.5355, 77.3910, NCR, ['noida']),
    'Greater Noida': (28.4744, 77.5040, NCR, ['greater noida']),
    'Gurugram': (28.4595, 77.0266, NCR, ['gurugram', 'gurgaon']),
    'Ghaziabad': (28.6692, 77.4538, NCR, ['ghaziabad']),
    'Faridabad': (28.4089, 77.3178, NCR, ['faridabad']),
    'Sonipat': (28.9931, 77.0151, NCR, ['sonipat', 'sonepat']),
    'Meerut': (28.9845, 77.7064, None, ['meerut']),
    'Mumbai': (19.0760, 72.8777, None, ['mumbai', 'bombay']),
    'Navi Mumbai': (19.0330, 73.0297, 'Mumbai', ['navi mumbai']),
    'Thane': (19.2183, 72.9781, 'Mumbai', ['thane']),
    'Pune': (18.5204, 73.8567, None, ['pune']),
    'Bengaluru': (12.9716, 77.5946, None, ['bengaluru', 'bangalore', 'bangalore urban']),
    'Mysuru': (12.2958, 76.6394, None, ['mysuru', 'mysore']),
    'Manipal': (13.3525, 74.7928, None, ['manipal']),
    'Mangaluru': (12.9141, 74.8560, None, ['mangaluru', 'mangalore', 'surathkal']),
    'Hyderabad': (17.3850, 78.4867, None, ['hyderabad', 'secunderabad']),
    'Chennai': (13.0827, 80.2707, None, ['chennai', 'madras']),
    'Vellore': (12.9165, 79.1325, None, ['vellore']),
    'Coimbatore': (11.0168, 76.9558, None, ['coimbatore']),
    'Madurai': (9.9252, 78.1198, None, ['madurai']),
    'Tiruchirappalli': (10.7905, 78.7047, None, ['tiruchirappalli', 'trichy']),
    'Puducherry': (11.9416, 79.8083, None, ['puducherry', 'pondicherry']),
    'Kolkata': (22.5726, 88.3639, None, ['kolkata', 'calcutta']),
    'Kharagpur': (22.3460, 87.2320, None, ['kharagpur']),
    'Ahmedabad': (23.0225, 72.5714, None, ['ahmedabad']),
    'Gandhinagar': (23.2156, 72.6369, None, ['gandhinagar']),
    'Surat': (21.1702, 72.8311, None, ['surat']),
    'Vadodara': (22.3072, 73.1812, None, ['vadodara', 'baroda']),
    'Jaipur': (26.9124, 75.7873, None, ['jaipur']),
    'Jodhpur': (26.2389, 73.0243, None, ['jodhpur']),
    'Udaipur': (24.5854, 73.7125, None, ['udaipur']),
    'Kota': (25.2138, 75.8648, None, ['kota']),
    'Pilani': (28.3670, 75.6040, None, ['pilani']),
    'Chandigarh': (30.7333, 76.7794, None, ['chandigarh']),
    'Mohali': (30.7046, 76.7179, 'Chandigarh', ['mohali']),
    'Ludhiana': (30.9010, 75.8573, None, ['ludhiana']),
    'Amritsar': (31.6340, 74.8723, None, ['amritsar']),
    'Jalandhar': (31.3260, 75.5762, None, ['jalandhar']),
    'Patiala': (30.3398, 76.3869, None, ['patiala']),
    'Kurukshetra': (29.9695, 76.8783, None, ['kurukshetra']),
    'Hisar': (29.1492, 75.7217, None, ['hisar']),
    'Lucknow': (26.8467, 80.9462, None, ['lucknow']),
    'Kanpur': (26.4499, 80.3319, None, ['kanpur']),
    'Varanasi': (25.3176, 82.9739, None, ['varanasi', 'banaras']),
    'Prayagraj': (25.4358, 81.8463, None, ['prayagraj', 'allahabad']),
    'Agra': (27.1767, 78.0081, None, ['agra']),
    'Dehradun': (30.3165, 78.0322, None, ['dehradun']),
    'Roorkee': (29.8543, 77.8880, None, ['roorkee']),
    'Indore': (22.7196, 75.8577, None, ['indore']),
    'Bhopal': (23.2599, 77.4126, None, ['bhopal']),
    'Gwalior': (26.2183, 78.1828, None, ['gwalior']),
    'Jabalpur': (23.1815, 79.9864, None, ['jabalpur']),
    'Nagpur': (21.1458, 79.0882, None, ['nagpur']),
    'Nashik': (19.9975, 73.7898, None, ['nashik']),
    'Aurangabad': (19.8762, 75.3433, None, ['aurangabad', 'chhatrapati sambhajinagar']),
    'Raipur': (21.2514, 81.6296, None, ['raipur', 'naya raipur']),
    'Bhubaneswar': (20.2961, 85.8245, None, ['bhubaneswar']),
    'Rourkela': (22.2604, 84.8536, None, ['rourkela']),
    'Patna': (25.5941, 85.1376, None, ['patna']),
    'Ranchi': (23.3441, 85.3096, None, ['ranchi']),
    'Guwahati': (26.1445, 91.7362, None, ['guwahati']),
    'Kochi': (9.9312, 76.2673, None, ['kochi', 'cochin', 'ernakulam']),
    'Thiruvananthapuram': (8.5241, 76.9366, None, ['thiruvananthapuram', 'trivandrum']),
    'Kozhikode': (11.2588, 75.7804, None, ['kozhikode', 'calicut']),
    'Visakhapatnam': (17.6868, 83.2185, None, ['visakhapatnam', 'vizag']),
    'Vijayawada': (16.5062, 80.6480, None, ['vijayawada']),
    'Warangal': (17.9689, 79.5941, None, ['warangal']),
    'Goa': (15.4909, 73.8278, None, ['goa', 'panaji', 'panjim']),
    'Shimla': (31.1048, 77.1734, None, ['shimla']),
    'Srinagar': (34.0837, 74.7973, None, ['srinagar']),
    'Jammu': (32.7266, 74.8570, None, ['jammu']),
}

_ALIASES = sorted(((alias, name) for name, (_, _, _, aliases) in CITIES.items() for alias in aliases),
                  key=lambda a: -len(a[0]))
_ALIAS_RE = [(re.compile(r'(?<![a-z])' + re.escape(alias) + r'(?![a-z])'), name) for alias, name in _ALIASES]

ONLINE_WORDS = re.compile(r'(?<![a-z])(online|virtual)(?![a-z])')
REMOTE_WORDS = re.compile(r'(?<![a-z])(remote|wfh|work from home|anywhere|worldwide)(?![a-z])')
HYBRID_WORDS = re.compile(r'(?<![a-z])hybrid(?![a-z])')
ONSITE_WORDS = re.compile(r'(?<![a-z])(offline|in-person|in person|onsite|on-site)(?![a-z])')

ONLINE_SOURCES = {'Codeforces', 'CodeChef', 'LeetCode', 'HackerRank'}


def detect(text, source=''):
    t = (text or '').lower()
    city = next((name for rx, name in _ALIAS_RE if rx.search(t)), None)

    if source in ONLINE_SOURCES or ONLINE_WORDS.search(t):
        mode = 'online'
    elif HYBRID_WORDS.search(t):
        mode = 'hybrid'
    elif REMOTE_WORDS.search(t):
        mode = 'remote'
    elif city or ONSITE_WORDS.search(t):
        mode = 'onsite'
    else:
        mode = None

    if not city:
        return {'city': None, 'region': None, 'lat': None, 'lon': None, 'mode': mode}
    lat, lon, region, _ = CITIES[city]
    return {'city': city, 'region': region or city, 'lat': lat, 'lon': lon, 'mode': mode}


def distance_km(lat1, lon1, lat2, lon2):
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def nearest_city(lat, lon):
    name = min(CITIES, key=lambda n: distance_km(lat, lon, CITIES[n][0], CITIES[n][1]))
    return name, distance_km(lat, lon, CITIES[name][0], CITIES[name][1])
