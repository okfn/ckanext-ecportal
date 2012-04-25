# -*- coding: UTF8 -*-
'''
**Notice**: Vim users please check the tests README file before
            editing this file.
'''

from ckan.lib.create_test_data import CreateTestData as CkanCreateTestData


class CreateTestData(CkanCreateTestData):
    @classmethod
    def create_ecportal_search_test_data(cls, extra_core_fields):
        cls.create_arbitrary(ecportal_search_items,
                             extra_core_fields=extra_core_fields)

# Some random fixtures useful for testing multilingual search aspects
# Tags are EuroVoc terms
ecportal_search_items = [
    {
        'name':u'test-english',
        'title':u'Test language English - Some random title about Fishing Industries',
        'description':u'''Georg Briel (21 August 1907 - 16 May 1980) was a highly decorated Oberstleutnant
                          in the Wehrmacht during World War II. He was also a recipient of the Knight's Cross of the
                          Iron Cross. The Knight's Cross of the Iron Cross was awarded to recognise extreme
                          battlefield bravery or successful military leadership. Georg Briel was captured by
                          Allied troops in May 1945 and was released by June 1945.''',
        'tags': [u'nuclear weapon', u'fodder cereals', u'fine arts'],
        'extras': {
            'test-extra-1': u'Public Library'
        }
    },
    {
        'name':u'test-czech',
        'title':u'Test language Czech - Sjednocení pražských měst',
        'description':u'''Samotné jméno Praha vyvolává nejvíce diskuzí, které zřejmě nebudou nikdy uzavřeny.
                          Název se běžně odvozuje od slova práh. Historici obvykle tvrdí, že Praha je pojmenována po
                          říčním prahu či jezu, který se nacházel někde na místě dnešního Karlova mostu.
                          Přes tento brod přecházeli lidé přes řeku.''',
        'tags': [u'jedrsko orožje', u'krmna žita', u'lepe umetnosti'],
        'extras': {
            'test-extra-1': u'Druhá světová válka'
        }
    },
    {
        'name':u'test-greek',
        'title':u'Test language Greek - Πανίδα και Χλωρίδα',
        'description':u'''Η Κρήτη είναι απομονωμένη από τις υπόλοιπες ηπειρωτικές περιοχές της Ευρώπης,
                          της Ασίας και της Αφρικής, γεγονός που αποτυπώνεται έντονα στη γενετική διαφορετικότητα
                          της πανίδας και της χλωρίδας του νησιού. Από τον κρητικό αίγαγρο (κρι κρι), τον κρητικό
                          αγριόγατο και την Κρητική μυγαλή.''',
        'tags': [u'πυρηνικά όπλα', u'κτηνοτροφικό σιτηρό', u'καλές τέχνες'],
        'extras': {
            'test-extra-1': u'Προανακτορική περίοδος'
        }
    },
    {
        'name':u'test-catalan',
        'title':u'Test language Catalan - Força Barça',
        'description':u'''El Metro de Barcelona és una xarxa de ferrocarril metropolità soterrat
                          que dóna servei a Barcelona, l'Hospitalet de Llobregat, Cornellà de Llobregat,
                          Santa Coloma de Gramenet, Badalona, Sant Boi de Llobregat i Montcada i Reixac.''',
        'tags': [u'arma nuclear', u'cereal farratger', u'belles arts'],
        'extras': {
            'test-extra-1': u'Il·lusió i raïm'
        }
    }
]
