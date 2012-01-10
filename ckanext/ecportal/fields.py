geographic_granularity_options = ['national', 'regional', 'local authority', 'ward', 'point']

region_options = ('England', 'Scotland', 'Wales', 'Northern Ireland', 'Overseas', 'Global')

region_groupings = {'United Kingdom':['England', 'Scotland', 'Wales', 'Northern Ireland'], 'Great Britain':['England', 'Scotland', 'Wales']}

region_abbreviations = {'UK':'United Kingdom', 'N. Ireland':'Northern Ireland', 'GB':'Great Britain'}

tag_pool = ['accident', 'road', 'traffic', 'health', 'illness', 'disease', 'population', 'school', 'accommodation', 'children', 'married', 'emissions', 'benefit', 'alcohol', 'deaths', 'mortality', 'disability', 'unemployment', 'employment', 'armed forces', 'asylum', 'cancer', 'births', 'burglary', 'child', 'tax credit', 'criminal damage', 'drug', 'earnings', 'education', 'economic', 'fire', 'fraud', 'forgery', 'fuel', 'green', 'greenhouse gas', 'homeless', 'hospital', 'waiting list', 'housing', 'care', 'income', 'census', 'mental health', 'disablement allowance', 'jobseekers allowance', 'national curriculum', 'older people', 'living environment', 'higher education', 'living environment', 'school absence', 'local authority', 'carbon dioxide', 'energy', 'teachers', 'fostering', 'tide', 'gas', 'electricity', 'transport', 'veterinary', 'fishing', 'export', 'fisheries', 'pest', 'recycling', 'waste', 'crime', 'anti-social behaviour', 'police', 'refugee', 'identity card', 'immigration', 'planning', 'communities', 'lettings', 'finance', 'ethnicity', 'trading standards', 'trade', 'business', 'child protection', 'jobs', 'weather', 'climate', 'rainfall', 'cloud', 'snow', 'humidity', 'pressure', 'precipitation', 'sunshine', 'frost', 'temperature']

tag_search_fields = ['name', 'title', 'notes', 'categories', 'agency']

class GeoCoverageType(object):
    @staticmethod
    def get_instance():
        if not hasattr(GeoCoverageType, 'instance'):
            GeoCoverageType.instance = GeoCoverageType.Singleton()
        return GeoCoverageType.instance

    class Singleton(object):
        def __init__(self):
            regions_str = region_options
            self.groupings = region_groupings
            self.regions = [(region_str, GeoCoverageType.munge(region_str)) for region_str in regions_str]
            self.regions_munged = [GeoCoverageType.munge(region_str) for region_str in regions_str]

        def munged_regions_to_printable_region_names(self, munged_regions):
            incl_regions = []
            for region_str, region_munged in self.regions:
                if region_munged in munged_regions:
                    incl_regions.append(region_str)
            for grouping_str, regions_str in self.groupings.items():
                all_regions_in = True
                for region_str in regions_str:
                    if region_str not in incl_regions:
                        all_regions_in = False
                        break
                if all_regions_in:
                    for region_str in regions_str:
                        incl_regions.remove(region_str)
                    incl_regions.append('%s (%s)' % (grouping_str, ', '.join(regions_str)))
            return ', '.join(incl_regions)

        def str_to_db(self, regions_str):
            for abbrev, region in region_abbreviations.items():
                regions_str = regions_str.replace(abbrev, region)
            for grouping, regions in region_groupings.items():
                regions_str = regions_str.replace(grouping, ' '.join(regions))
            regions_munged = []
            for region, region_munged in self.regions:
                if region in regions_str:
                    regions_munged.append(region_munged)
            return self.form_to_db(regions_munged)

        def form_to_db(self, form_regions):
            assert isinstance(form_regions, list)
            coded_regions = u''
            for region_str, region_munged in self.regions:
                coded_regions += '1' if region_munged in form_regions else '0'
            regions_str = self.munged_regions_to_printable_region_names(form_regions)
            return '%s: %s' % (coded_regions, regions_str)

        def db_to_form(self, form_regions):
            '''
            @param form_regions e.g. 110000: England, Scotland
            @return e.g. ["england", "scotland"]
            '''
            regions = []
            if len(form_regions)>len(self.regions):
                for i, region in enumerate(self.regions):
                    region_str, region_munged = region
                    if form_regions[i] == '1':
                        regions.append(region_munged)
            return regions

    @staticmethod
    def munge(region):
        return region.lower().replace(' ', '_')

    def __getattr__(self, name):
        return getattr(self.instance, name)

