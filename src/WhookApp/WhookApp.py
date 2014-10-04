import json

__author__ = '@badu_bizzle'

ES_INDEX_NAME = "whookapp"
from redis import Redis
from elasticsearch import Elasticsearch
es = Elasticsearch([{u'host': u'127.0.0.1', u'port': b'9200'}])
redis_db = Redis()

#create index for whookapp
es.indices.create(index=ES_INDEX_NAME, ignore=400)

# for parsing phone numbers and automatically getting user's country
# based on the phone number. Useful for narrowing down hookup searches
# to country of the user requesting for hookup
import phonenumbers
import pycountry
class WhookAppResponse:
    FIND_HELP_DOC = "To find hook up:\nFIND, gender [from age] [to age] [location]"
    WELCOME = 'Welcome to WhookApp\n\nWhookApp is free hookup service ' \
              'helps you to find hookups through WhatsApp.'

    HELP_DOC = WELCOME + "\n\n1. To create your profile\n" \
                         "JOIN, your name, gender, age, location \n\n" \
                         "2. To find hookups\n" \
                         "FIND, gender, [from age] [to age] [location]\n\n" \
                         "3. To stop\n" \
                         "STOP\n\n" \
                         "4. To see help info\n" \
                         "HELP"
    REGISTER_SUCCESS = 'You have successfully registered!'
    JOIN_INFO = "Send\nJOIN, name, gender, age, location \n"
    SHOULD_REGISTER = "You do not have a profile on WhookApp yet.\nTo create your profile send:\n\nJOIN, your name, gender, age, location \n"
    UPDATED_SUCCESSFULLY = "Profile updated successfully."
    DELETED_SUCCESSFULLY = "You profile is no longer on WhookApp.\nRemember, you can always come back by sending JOIN"
    REGISTERED_ALREADY = "You already have a profile on WhookApp. Thanks"
    ACCOUNT_ACTIVATED = "Welcome back on WhookApp. Get lucky!"
    INVALID_REQUEST = "Invalid request. Send HELP for more info."

class User:
    STATUS_ACTIVE = 1
    STATUS_DELETED = 3
    KEY_PHONE = 'phone'
    KEY_AGE = 'age'
    KEY_GENDER = 'gender'
    KEY_LOCATION = 'location'
    KEY_STATUS = 'status'
    KEY_STATUS_MESSAGE = 'status_message'
    KEY_NAME = 'name'
    KEY_COUNTRY_NAME = 'country'
    KEY_LOCALE_CODE = 'locale_code'

    def __init__(self, phone, name, gender, age, location):
        self.phone = phone
        self.name = name
        self.gender = gender
        self.age = age
        self.location = location
        self.status = User.STATUS_ACTIVE
        self.status_message = ""
        self.county_name = ""
        self.locale_code = ""

    def to_json_object(self):
        data = dict()
        data[User.KEY_NAME] = self.name
        data[User.KEY_AGE] = self.age
        data[User.KEY_GENDER] = self.gender
        data[User.KEY_LOCATION] = self.location
        data[User.KEY_STATUS] = self.status
        data[User.KEY_STATUS_MESSAGE] = self.status_message
        data[User.KEY_PHONE] = self.phone
        data[User.KEY_COUNTRY_NAME]=self.county_name
        data[User.KEY_LOCALE_CODE]=self.locale_code
        return data


class WhookApp:

    UN_AUTH_COMMANDS = ['help', 'h','i','info','stats']
    AUTH_COMMANDS = []
    AVAILABLE_COMMANDS = ['join', 'j', 'status', 'stop', 's', 'search', 'info', 'i', 'help', 'h', 'find', 'f', 'profile', 'p','next','n']

    MESSAGE_ID_KEY = 'id'
    SENDER_KEY = 'sender'
    SENDER_NAME_KEY = 'name'
    IS_BROADCAST_KEY = 'broadcast'
    CONTENT_KEY = 'content'
    TIMESTAMP_KEY = 'ts'
    ES_INDEX_NAME = "whookapp"
    ES_DOC_USER = "user"

    def __init__(self, json_object):
        self.status = 0
        self.json_object = json_object
        self.message = self.json_object[WhookApp.CONTENT_KEY]
        self.sender = self.json_object[WhookApp.SENDER_KEY]
        self.sender_phone = self.sender.split("@")[0].strip()
        self.timestamp = self.json_object[WhookApp.TIMESTAMP_KEY]
        parts = [s.strip() for s in self.message.split(",")]
        self.arguments = parts[1:]
        self.command = parts[0].lower().strip()
        self.reply = None
        self.success = False
        self.country_name=None
        self.country_code=None

    def process(self):
        print("Process packet %s" % self.command)
        if self.command in WhookApp.AVAILABLE_COMMANDS:
            if not self.command in WhookApp.UN_AUTH_COMMANDS:
                user = self.get_user(self.sender_phone)
                if user is None:
                    self.success = True
                    self.reply =WhookAppResponse.SHOULD_REGISTER
                    return
            print ("Command %s found" % self.command)
            if self.command == "status":
                self.status_()
            elif hasattr(self, self.command):
                cmd = getattr(self, self.command)
                cmd()
            else:
                print("No command found on object")
        else:
            #if self.message.strip() in WhookApp.TAL_TO_SOMEONE:
                #pass
            print ("Command not available")
            self.reply = WhookAppResponse.INVALID_REQUEST
            self.success = True
    def status_(self):
        print "Updating status: %s" % self.arguments
        if len(self.arguments) > 0:
            status_message = ",".join(self.arguments) if len(self.arguments)>1 else self.arguments[0]
            if self.update_user_status(self.sender_phone,status_message):
                self.success = True
                self.reply=WhookAppResponse.UPDATED_SUCCESSFULLY
        else:
            user = self.get_user(self.sender_phone)
            self.success = True
            self.reply = ("Your current status: %s" % user['status_message'])


    def join(self):
        #join user
        # join, badu bizzle, male, 25, accra
        print("Registering new user")
        profile = self.arguments
        if len(profile) < 4:
            user = self.get_user(self.sender_phone)
            if user is not None:
                if int(user['status'])==User.STATUS_DELETED:
                    #reactivate user
                    self.update_user(self.sender_phone, {User.KEY_STATUS:User.STATUS_ACTIVE})
                    self.reply = WhookAppResponse.ACCOUNT_ACTIVATED
                    self.success=True
                else:
                    self.reply = WhookAppResponse.REGISTERED_ALREADY
                    self.success = True
            else:
                self.success = True
                self.reply =WhookAppResponse.SHOULD_REGISTER# None # WhookAppResponse.JOIN_INFO
        else:
            name = profile[0]
            gender = profile[1].lower()
            age = int(profile[2])
            location = profile[3]
            phone = self.sender_phone
            user = User(phone=phone, name=name, gender=gender, age=age, location=location)
            #if self.user_exists(phone):
            #    self.success = True
            #    self.reply = WhookAppResponse.ALREADY_REGISTERED

            phone_number = phonenumbers.parse(("+%s" % self.sender_phone.strip()), None)
            locale_code = phonenumbers.region_code_for_country_code(phone_number.country_code)
            country=pycountry.countries.get(alpha2=locale_code)
            user.country_name=country.name
            user.locale_code=locale_code


            if self.register_user(user):
                self.success = True
                self.reply = WhookAppResponse.REGISTER_SUCCESS
            else:
                self.success = True
                self.reply = None

    def stats(self):
        # get stats on the hookup service
        data = dict()
        data['Total users']=0
        data['Male'] = 0
        data['Female']=0

        pass

    def j(self):
        self.join()

    def info(self):
        self.success = True
        self.reply = WhookAppResponse.WELCOME

    def i(self):
        self.info()

    def help(self):
        self.success = True
        f = open("help.txt")
        self.reply = "".join(f.readlines())# WhookAppResponse.HELP_DOC

    def h(self):
        self.help()

    def stop(self):
        self.success = True
        if self.sender_phone is not None:
            if self.user_exists(self.sender_phone):
                if self.update_user(self.sender_phone, {User.KEY_STATUS:User.STATUS_DELETED}):
                    self.reply = WhookAppResponse.DELETED_SUCCESSFULLY

    def profile(self):
        try:
            user = es.get_source(index=WhookApp.ES_INDEX_NAME, doc_type=WhookApp.ES_DOC_USER,id=self.sender_phone)
            if user:
                self.success = True
                self.reply = self.display_user_profile(user)
            return user
        except Exception as e:
            print "Error: %s" % str(e)

        return None

    def p(self):
        self.profile()

    def update_user(self, phone, doc_dict):

        try:
            es.update(index=WhookApp.ES_INDEX_NAME, doc_type=WhookApp.ES_DOC_USER,id=phone, body={'doc':doc_dict})
            return True
        except:
            pass

        return False

    def user_exists(self, phone):
        try:
            return es.exists(index=WhookApp.ES_INDEX_NAME, doc_type=WhookApp.ES_DOC_USER, id=phone)
        except Exception as e:
            print "Error :%s" % str(e)

        return False

    def register_user(self, user):
        if isinstance(user, User):
            if user.phone:
                try:
                    if es.exists(index=WhookApp.ES_INDEX_NAME, doc_type=WhookApp.ES_DOC_USER, id=user.phone):
                        es.update(index=WhookApp.ES_INDEX_NAME, doc_type=WhookApp.ES_DOC_USER, id=user.phone,
                                  body={'doc': user.to_json_object()})
                    else:
                        es.index(index=WhookApp.ES_INDEX_NAME, doc_type=WhookApp.ES_DOC_USER,
                                 body=user.to_json_object(), id=user.phone)
                    return True
                except:
                    pass
        return False

    def update_user_status(self, phone, status_message):
        if self.user_exists(phone):
            print "Updating status message: %s" % status_message
            es.update(index=WhookApp.ES_INDEX_NAME, doc_type=WhookApp.ES_DOC_USER, id=phone,
                      body={'doc': {'status_message': status_message}})
            return True
        else:
            print "User doesnt exist"

        return False

    def get_user(self, phone):
        if phone:
            try:
                result = es.get_source(index=WhookApp.ES_INDEX_NAME, doc_type=WhookApp.ES_DOC_USER, id=phone)
                return result
            except Exception as e:
                print "Error: %s" % str(e)

        return None

    def display_user_profile(self, user_dict):
        print "Diplay user: %s" % user_dict
        s = "Name: %s \nAge: %s\nLocation: %s\nPhone: +%s\nMessage: %s" % (str(user_dict[User.KEY_NAME]),
                                                              str(user_dict[User.KEY_AGE]),
                                                              str(user_dict[User.KEY_LOCATION]),
                                                              str(user_dict[User.KEY_PHONE]),
                                                              str(user_dict[User.KEY_STATUS_MESSAGE]))
        return s

    def get_search_arguments(self):
        try:
            data = dict(gender=None, from_age=None, to_age=None, location=None)
            if self.arguments is not None:
                if len(self.arguments) > 0:
                    data['gender'] = self.arguments[0].lower().strip()

                if len(self.arguments) > 1:
                    try:
                        data['from_age'] = int(self.arguments[1])
                    except:
                        pass

                if len(self.arguments) > 2:
                    try:
                        data['to_age'] = int(self.arguments[2])
                    except:
                        pass
                elif len(self.arguments) > 1:
                    #check if from age is in the format "from-to"
                    from_age = self.arguments[1]
                    if "-" in from_age.strip():
                        parts = from_age.split("-")
                        try:
                            data['from_age'] = int(parts[0].strip())
                        except:
                            pass
                        try:
                            data['to_age'] = int(parts[1].strip())
                        except:
                            pass

                if len(self.arguments) > 3:
                    data['location'] = self.arguments[3].strip()

            return data
        except Exception as e:
            print 'error passing args %s' % str(e)
            pass

        return None

    def next(self):

        key = "last_search.%s" % self.sender_phone
        print "Getting next result: %s" % key
        result = redis_db.hgetall(key)
        print "Result :%s" % type(result)
        if result is not None and len(result)>0:
            total = int(result['total'])
            next_index = int(result['next'])
            q = result['q']
            if next_index >= total or next_index >= 10:
                self.message = q
                self.find()
            else:
                temp_result =  json.loads(result['result'])
                #print "Temp result: %s" % temp_result
                #temp_result = json.loads(temp_result)
                next_result = temp_result['result'][next_index]
                print "Next result: %s" % next_result
                redis_db.hmset(key, dict(result=result['result'], q=self.message, next=next_index+1, total=total))
                self.success=True
                self.reply = self.display_user_profile(next_result['_source'])




    def find(self):
        print "find with args: %s" % self.arguments
        if not self.user_exists(self.sender_phone):
            print 'user not found'
            self.success = True
            self.reply = WhookAppResponse.SHOULD_REGISTER
            return None
            # find gender age_from age_to location
        if self.arguments is not None and len(self.arguments) > 0:
            search_args = self.get_search_arguments()
            print ("Search args: %s" % search_args)
            if search_args is None:
                self.success = True
                self.reply = None # WhookAppResponse.FIND_HELP_DOC
            elif isinstance(search_args, dict) and len(search_args) == 4:
                #gender, from_age, to_age, location = tuple(search_args.values())
                results = None
                if search_args['gender'] is not None:
                    results = self.search_with_query(self.get_query(gender=search_args['gender'],
                                                                    from_age=search_args['from_age'],
                                                                    to_age=search_args['to_age'],
                                                                    location=search_args['location']),size=10)

                if results is not None:
                    found = results['hits']['hits']
                    user_search_key = "last_search.%s" % self.sender_phone
                    redis_db.hmset(user_search_key, dict(result=json.dumps({'result':found}), q=self.message, next=1, total=results['hits']['total']))
                    if len(found) > 0:
                        user = found[0]['_source']
                        self.success = True
                        self.reply = "Found: %s \n\n%s" % (
                            str(results['hits']['total']), self.display_user_profile(user))
                    else:
                        self.reply = 'No hookups matches your criteria. Try again.'
                        self.success = True
                else:
                    pass

    def f(self):
        self.find()

    def search_with_query(self, query, size=100):
        print ("Searching with query: %s" % query)
        try:
            result = es.search(index=WhookApp.ES_INDEX_NAME, doc_type=WhookApp.ES_DOC_USER, body=dict(query=query), params={'size':size})
            return result
        except:
            pass
        return None

    def get_query(self, gender, from_age=None, to_age=None, location=None):
        query = dict()
        query['filtered'] = dict(query=dict(match=dict(gender=gender)))
        must_not = [dict(term=dict(phone=self.sender_phone))]
        must = []
        if from_age or to_age:
            if from_age and to_age:
                age = {'from': from_age, 'to': to_age}
                must.append(dict(range=dict(age=age)))
            elif from_age:
                age = {'gte': from_age}
                must.append(dict(range=dict(age=age)))
            elif to_age:
                age = {'lte': to_age}
                must.append(dict(range=dict(age=age)))

        if location:
            must.append(dict(term=dict(location=str(location))))

        query['filtered']['filter'] = dict(bool=dict(must_not=must_not, must=must))
        return query

# Redundant search methods
    def find_by_gender(self, gender):
        return self.search_with_query(self.get_query(gender=gender))

    def find_by_gender_age_from(self, gender, from_age):
        query = self.get_query(gender=gender, from_age=from_age)
        return self.search_with_query(query)

    def find_by_gender_age_from_to(self, gender, from_age, to_age):
        return self.search_with_query(self.get_query(gender=gender, from_age=from_age, to_age=to_age))

    def find_by_gender_age_from_to_with_location(self, gender, from_age, to_age, location):
        return self.search_with_query(
            self.get_query(gender=gender, from_age=from_age, to_age=to_age, location=location))
