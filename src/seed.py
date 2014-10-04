import random

__author__ = '@badu_bizzle'

from faker import Factory

fake = Factory.create()

from elasticsearch import Elasticsearch
INDEX = "whookapptest"
DOC = "user"
es = Elasticsearch([{u'host': u'127.0.0.1', u'port': b'9200'}])
# try:
#     es.indices.delete(index=INDEX)
# except:
#     pass
es.indices.create(index=INDEX,ignore=400)
import phonenumbers
import pycountry
for r in range(0,500):
    phone = fake.phone_number().split("x")[0]
    Id =   str(int("".join([ c if c.isdigit() else "" for c in phone])))
    body = dict(phone=Id,
                name=fake.first_name(),
                age=random.choice(range(18,35)),
                gender=random.choice(['male','female']),
                location=fake.city(),
                status=random.choice([1,0]),
                status_message=" ".join(fake.text().split()[:10]))
    p = ("+%s" % Id.strip())
    try:
        phone_number = phonenumbers.parse(p, None)
        locale_code = phonenumbers.region_code_for_country_code(phone_number.country_code)
        country=pycountry.countries.get(alpha2=locale_code)
        body['country_name'] = country.name
        body['locale_code'] = locale_code
        if not (es.exists(index=INDEX, doc_type=DOC, id=Id)):
            es.index(index=INDEX, doc_type=DOC, id=Id, body=body)
    except Exception as e:
        print "Error :%s" % str(e)


