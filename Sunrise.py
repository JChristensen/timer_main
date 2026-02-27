import math, time

# constants
OFFICIAL_ZENITH = 90.83333  # 90°50'
CIVIL_ZENITH = 96.0
NAUTICAL_ZENITH = 102.0
ASTRONOMICAL_ZENITH = 108.0

class Sunrise:
    """Calculate sunrise and sunset times for a given day and
    a given location (latitude and longitude.)"""

    def __init__(self, lat=45.8124, lon=-84.7285, zenith=OFFICIAL_ZENITH):
        self.lat = lat
        self.lon = lon
        self.zenith = zenith

    def calc_rise_set(self, t):
        """Given time t as a struct_time containing tm_gmtoff,
        calculate sunrise and sunset as struct_time and return
        them in a list."""
        offset_hours = t.tm_gmtoff / 3600.0
        yday = t.tm_yday
        hour, minute = self.calc_sunset(yday, offset_hours, False)
        sunrise = time.struct_time((t.tm_year, t.tm_mon, t.tm_mday, \
            hour, minute, 0, t.tm_wday, t.tm_yday, t.tm_isdst))
        hour, minute = self.calc_sunset(yday, offset_hours, True)
        sunset = time.struct_time((t.tm_year, t.tm_mon, t.tm_mday, \
            hour, minute, 0, t.tm_wday, t.tm_yday, t.tm_isdst))
        return [sunrise, sunset]

    def calc_sunset(self, doy, utc_offset, sunset):
        """Given day of year and utc_offset, calculates sunset time
        if sunset is True, else calculates sunrise time. Returns
        the time as a list of two integers, hour and minute."""

        hour = 0
        minute = 0

        # Convert the longitude to hour value and calculate an approximate time.
        lonhour = (self.lon / 15)
        if (sunset):
            t = doy + ((18 - lonhour) / 24)
        else:
            t = doy + ((6 - lonhour) / 24)

        # Calculate the Sun's mean anomaly
        m = (0.9856 * t) - 3.289

        # Calculate the Sun's true longitude
        sinm = math.sin(self.deg_to_rad(m))
        sin2m = math.sin(2 * self.deg_to_rad(m))
        l = self.adjust_to_360 (m + (1.916 * sinm) + (0.02 * sin2m) + 282.634)

        # Calculate the Sun's right ascension(RA)
        tanl = 0.91764 * math.tan(self.deg_to_rad(l))
        ra = self.adjust_to_360 (self.rad_to_deg(math.atan(tanl)))

        # Putting the RA value into the same quadrant as L
        lq = (math.floor(l / 90)) * 90
        raq = (math.floor(ra / 90)) * 90
        ra = ra + (lq - raq)

        # Convert RA values to hours
        ra /= 15

        # Calculate the Sun's declination
        sindec = 0.39782 * math.sin(self.deg_to_rad(l))
        cosdec = math.cos(math.asin(sindec))

        # Calculate the Sun's local hour angle
        # float cosh = (cos(deg2rad(m_zenith)) - (sindec * sin(deg2rad(m_lat))))
        #   / (cosdec * cos(deg2rad(m_lat)));
        cosH = (math.cos(self.deg_to_rad(self.zenith)) \
            - (sindec * math.sin(self.deg_to_rad(self.lat)))) \
            / (cosdec * math.cos(self.deg_to_rad(self.lat)))

        # if cosH > 1 the sun never rises on this date at this location
        # if cosH < -1 the sun never sets on this date at this location
        if (cosH >  1):
            return
        elif (cosH < -1):
            return

        # Finish calculating H and convert into hours
        if (sunset):
            h = self.rad_to_deg(math.acos(cosH))
        else:
            h = 360 - self.rad_to_deg(math.acos(cosH))
        h /= 15

        # Calculate local mean time of rising/setting
        t = h + ra - (0.06571 * t) - 6.622

        # Adjust back to UTC
        ut = self.adjust_to_24(t - lonhour)
        # Adjust for current time zone
        ut = self.adjust_to_24(ut + utc_offset)
        ut += 30 / 3600     # round up by 30 seconds
        hour = int(ut)
        minute = int(60.0 * (ut - hour))
        return [hour, minute]

    def adjust_to_360(self, x):
        if (x > 360.0):
            x -= 360.0
        elif (x < 0.0):
            x += 360.0
        return x

    def adjust_to_24(self, x):
        if (x > 24.0):
            x -= 24.0
        elif (x < 0.0):
            x += 24.0
        return x

    def deg_to_rad(self, degrees):
        return degrees * math.pi / 180.0

    def rad_to_deg(self, radians):
        return radians / (math.pi / 180.0)
