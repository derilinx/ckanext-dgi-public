'''A directory of file formats and their properties'''

import re

class Formats(object):
    @classmethod
    def by_display_name(cls):
        '''Returns the formats data as a dict keyed by the display name'''
        if not hasattr(cls, '_by_display_name'):
            data = cls.get_data()
            cls._by_display_name = {}
            for format_dict in data:
                cls._by_display_name[format_dict['display_name']] = format_dict
        return cls._by_display_name

    @classmethod
    def by_mime_type(cls):
        '''Returns the formats data as a dict keyed by mime type'''
        if not hasattr(cls, '_by_mime_type'):
            data = cls.get_data()
            cls._by_mime_type = {}
            for format_dict in data:
                for mime_type in format_dict['mime_types']:
                    cls._by_mime_type[mime_type] = format_dict
        return cls._by_mime_type

    @classmethod
    def by_extension(cls):
        '''Returns the formats data as a dict keyed by filename extension'''
        if not hasattr(cls, '_by_extension'):
            data = cls.get_data()
            cls._by_extension = {}
            for format_dict in data:
                for extension in format_dict['extensions']:
                    cls._by_extension[extension] = format_dict
        return cls._by_extension

    @classmethod
    def by_reduced_name(cls):
        '''Returns the formats data as a dict keyed by "reduced" names for
        each format. This is helpful for matching against user-inputted formats.
        e.g. "TXT / .Zip" is "txt/zip"'''
        if not hasattr(cls, '_by_reduced'):
            data = cls.get_data()
            cls._by_reduced = {}
            for format_dict in data:
                for name in [format_dict['display_name']] + list(format_dict['extensions']) \
                             + list(format_dict['alternative_names']):
                    reduced_name = cls.reduce(name)
                    cls._by_reduced[reduced_name] = format_dict
        return cls._by_reduced

    @staticmethod
    def reduce(format_name):
        format_name = format_name.strip().lower()
        if format_name.startswith('.'): format_name = format_name[1:]
        return re.sub('[^a-z/+]', '', format_name)

    @classmethod
    def match(cls, raw_resource_format):
        '''Given a format that may be badly formatted, try and match it to
        a known format and return that.

        If no match is found, returns None.
        '''
        # Try exact match
        if raw_resource_format in cls.by_display_name():
            return cls.by_display_name()[raw_resource_format]

        # Try canonised match
        reduced_raw = cls.reduce(raw_resource_format)
        if reduced_raw in cls.by_reduced_name():
            return cls.by_reduced_name()[reduced_raw]

    @classmethod
    def get_x_stars_formats(cls, stars):
        '''Returns the display name of formats that are assigned a given star value'''

        return [dat['display_name'] for dat in cls.get_data() if dat['openness'] == stars]


    @classmethod
    def get_data(cls):
        '''Returns the list of data formats, each one as a dict

        e.g. [{'display_name': 'TXT', 'extensions': ('txt',), 'extension': 'txt',
               'mime_types': ('text/plain',), 'openness': 1},
              ...]
        '''
        if not hasattr(cls, '_data'):
            # store the data here so it only loads when first used, rather
            # than on module load
            data_flat = (
                # Display name, alternative names, extensions (lower case), mime-types, openness, icon-name
                ('HTML', ('web page', 'website'), ('html', 'htm', 'asp', 'php'), 'text/html', 1, 'globe--arrow'),
                ('JPEG', (), ('jpg','jpeg'), 'image/jpg', 1, 'image'),
                ('TIFF', (), ('tifflzw','tiff'), 'image/tiff', 1, 'image'),
                ('Database', ('database','sql'), (), (), 1, 'database-sql'),
                ('API', ('api',), (), (), 3, 'server-cloud'),
                ('TXT', (), ('txt',), 'text/plain', 1, 'document-text'),
                ('TXT / Zip', (), ('txt.zip',), 'application/txt+zip', 1, 'document-text'),
                ('PDF', (), ('pdf',), 'application/pdf', 1, 'document-pdf'),
                ('PDF / Zip', (), ('pdf.zip',), 'application/pdf+zip', 1, 'document-pdf'),
                ('RTF', (), ('rtf',), 'application/rtf', 1, 'document-word'),
                ('Zip', (), ('zip',), 'application/x-zip', 1, 'folder-zipper'),
                ('Torrent', (), ('torrent',), 'application/x-bittorrent', 1, ''),
                ('DOC', ('word',), ('doc', 'docx', 'mcw'), 'application/msword', 1, 'document-word'),
                ('ODT', (), ('odt',), 'application/vnd.oasis.opendocument.text', 1, 'document-word'),
                ('PPT', ('powerpoint',), ('ppt', 'pptx', 'ppz'), 'application/mspowerpoint', 1, 'document-powerpoint'),
                ('ODP', (), ('odp',), 'application/vnd.oasis.opendocument.presentation', 1, 'document-powerpoint'),
                ('XLS', ('excel',), ('xls', 'xlsx', 'xlb'), 'application/excel', 2, 'document-excel'),
                ('XLS / Zip', (), ('xls.zip',), 'application/xls+zip', 2, 'document-excel'),
                ('SHP', ('shapefile', 'esri shapefile',), 'shp', (), 3, 'globe-model'),
                ('SHP / Zip', (), ('shp.zip',), 'application/shp+zip', 3, 'globe-model'),
                ('PX', ('PC-Axis',), ('px',), 'text/plain', 3, 'document-invoice'),
                ('CSV', ('csvfile',), ('csv',), 'text/csv', 3, 'document-invoice'),
                ('CSV / Zip', (), ('csv.zip',), 'application/csv+zip', 3, 'document-invoice'),
                ('TSV', ('tsvfile',), ('tsv',), 'text/tsv', 3, 'document-invoice'),
                ('TSV / Zip', (), ('tsv.zip',), 'application/tsv+zip', 3, 'document-invoice'),
                ('PSV', (), ('psv',), 'text/psv', 3, 'document-invoice'),
                ('PSV / Zip', (), ('psv.zip',), 'application/psv+zip', 3, 'document-invoice'),
                ('JSON', (), ('json',), 'application/json', 3, 'document-node'),
                ('json-stat', (), ('json-stat',), 'application/json', 3, 'document-node'),
                ('XML', (), ('xml',), 'text/xml', 3, 'document-code'),
                ('XML / Zip', (), ('xml.zip',), 'application/xml+zip', 3, 'document-code'),
                ('RSS', (), ('rss',), 'text/rss+xml', 3, 'feed-document'),
                ('ODS', (), ('ods',), 'application/vnd.oasis.opendocument.spreadsheet', 3, 'document-excel'),
                ('WMS', ('wms', 'wms ogc'), ('wms'), 'application/vnd.ogc.wms_xml', 3, 'globe-model'),
                ('KML', (), ('kml',), 'application/vnd.google-earth.kml+xml', 3, 'globe-model'),
                ('NetCDF', (), ('cdf', 'netcdf'), 'application/x-netcdf', 3, ''),
                ('IATI', (), ('iati',), 'application/x-iati+xml', 3, 'document-code'),
                ('iCalendar', ('iCal', 'ICS'), ('ics', 'ical'), 'text/calendar', 3, 'calendar-day'),
                ('RDF', ('rdf/xml'), ('rdf'), 'application/rdf+xml', 5, 'document-rdf'),
                ('TTL', ('Turtle','N-Triples'), ('ttl','nt'), 'text/turtle', 5, 'document-rdf'),
                ('RDFa', ('html+rdfa',), (), (), 5, 'document-rdf'),
                ('SPARQL', (), (), 'application/sparql-results+xml', 5, 'document-rdf'),
                ('SPARQL web form', (), (), (), 5, 'document-rdf'),
                ('ID', (), (), (), 1, 'document-text'),
                ('DAT', (), (), (), 1, 'document-text'),
                ('MAP', (), (), (), 1, 'document-text'),
                ('TAB', (), (), (), 1, 'document-text'),
                ('GEOJSON', (), ('geojson'), 'application/geo+json', 3, 'document-node'),
                ('ESRI REST', ('esri rest'), (), (), 2, 'globe-model'),
                ('PX', ('PC-Axis'), ('px'), (), 2, 'document-invoice'),
                ('GTFS', ('gtfs'), (), (), 3, 'globe-model')
                )
            cls._data = []
            for line in data_flat:
                display_name, alternative_names, extensions, mime_types, openness, icon = line
                format_dict = dict(zip(('display_name', 'alternative_names', 'extensions', 'mime_types', 'openness', 'icon'), line))
                format_dict['extension'] = extensions[0] if extensions else ''
                cls._data.append(format_dict)
        return cls._data

# Mime types which give not much clue to the format
VAGUE_MIME_TYPES = set(('application/octet-stream',))
