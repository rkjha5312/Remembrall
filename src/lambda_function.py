import boto3
import json
import decimal
from datetime import datetime
import inflect
from boto3.dynamodb.conditions import Key, Attr


inflect = inflect.engine()
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('Remembrall')


def lambda_handler(event, context):
    if event['request']['type'] == 'LaunchRequest':
        return launch_request_handler(event['request'], event['session'])
    elif event['request']['type'] == 'IntentRequest':
        return intent_handler(event['request'], event['session'])
    elif event['request']['type'] == 'SessionEndedRequest':
        return handle_session_end_request()


def launch_request_handler(request_info, session_info):
    # LaunchIntent function
    session_attributes = {}
    card_title = "Remembrall"
    speech_output = "Hi Welcome to Remembrall. How can I be of help?"
    reprompt_text = ""
    should_end_session = False
    return build_response(session_attributes, build_speechlet_response(
        card_title, speech_output, reprompt_text, should_end_session))


def intent_handler(request_info, session_info):
    # IntentRequest handler
    if request_info['intent']['name'] == 'StoreIntent':
        return store_intent_handler(request_info, session_info)
    elif request_info['intent']['name'] == 'AMAZON.NoIntent':
        return handle_session_end_request()
    elif(request_info['intent']['name'] == 'AMAZON.YesIntent'):
        return handle_yes_intent()
    elif request_info['intent']['name'] == 'RetrieveItemIntent':
        return retrieve_item_intent_handler(request_info, session_info)
    elif request_info['intent']['name'] == 'RetrieveLocationIntent':
        return retrieve_location_intent_handler(request_info, session_info)
    elif request_info['intent']['name'] == 'AMAZON.HelpIntent' :
        return handle_help_request()
    elif request_info['intent']['name'] == 'AMAZON.CancelIntent' or request_info['intent']['name'] == 'AMAZON.StopIntent':
        return handle_session_end_request()


def store_intent_handler(request_info, session_info):
    # StoreIntent handler
    session_attributes = {}
    card_title = "Remembrall"
    speech_output = "I have noted it down. Do you want me to note anything else"
    reprompt_text = ""
    should_end_session = False
    try:
        request_info['intent']['slots']['item']['value']
    except:
        return build_dialog_response("I am sorry. Can you repeat the item?", dialog_elicit_slot_item(request_info))
    try:
        request_info['intent']['slots']['location']['value']
    except:
        return build_dialog_response("I am sorry. Can you repeat the location?", dialog_elicit_slot_location(request_info))
    table_write(request_info, session_info)
    return build_response(session_attributes, build_speechlet_response(
        card_title, speech_output, reprompt_text, should_end_session))


def continue_intent_handler(request_info, session_info):
    # ContinueIntent handler
    try:
        request_info['intent']['slots']['false']['value']
        return handle_session_end_request()
    except:
        request_info['intent']['slots']['false']['value']
        store_intent_handler(request_info, session_info)


def retrieve_item_intent_handler(request_info, session_info):
    try:
        request_info['intent']['slots']['item']['value']
        item = table_read_item(request_info, session_info)
        if(len(item) != 0):
            item = item[0]
            if (item['itemBool']):
                session_attributes = {}
                card_title = "Remembrall"
                speech_output = "It is " + item['location'] + '. Do you want to find anything else?'
                reprompt_text = ""
                should_end_session = False
            else:
                session_attributes = {}
                card_title = "Remembrall"
                speech_output = 'They are '  + item['location'] + ' .Do you want to find anything else?'
                reprompt_text = ""
                should_end_session = False
            return build_response(session_attributes, build_speechlet_response(
                    card_title, speech_output, reprompt_text, should_end_session))
        else:
            session_attributes = {}
            card_title = "Remembrall"
            speech_output = 'Sorry, I do not have any details about it ' + ' .Do you want to find anything else?'
            reprompt_text = ""
            should_end_session = False
            return build_response(session_attributes, build_speechlet_response(
                    card_title, speech_output, reprompt_text, should_end_session))
    except:
        return build_dialog_response("I am sorry. Can you repeat the item?", dialog_elicit_retrieve_item())


def retrieve_location_intent_handler(request_info, session_info):
    try:
        item = table_read_location(request_info, session_info)
        if(len(item) != 0):
            session_attributes = {}
            card_title = "Remembrall"
            speech_output = 'The items list. '
            for i in item :
                speech_output += (i['itemName'] + '. ')
            speech_output += '. Do you want to find anything else'
            reprompt_text = ""
            should_end_session = False
            return build_response(session_attributes, build_speechlet_response(
                    card_title, speech_output, reprompt_text, should_end_session))
        else:
            session_attributes = {}
            card_title = "Remembrall"
            speech_output = 'There is no item in the specified location .Do you want to find anything else?'
            reprompt_text = ""
            should_end_session = False
            return build_response(session_attributes, build_speechlet_response(
                    card_title, speech_output, reprompt_text, should_end_session))
    except:
        return build_dialog_response("I am sorry. Can you repeat the location?", dialog_elicit_retrieve_location())


def handle_session_end_request():
    session_attributes = {}
    card_title = "Remembrall"
    speech_output = 'Bye'
    reprompt_text = ""
    should_end_session = True
    return build_response(session_attributes, build_speechlet_response(card_title, speech_output, reprompt_text, should_end_session))


def handle_help_request():
    session_attributes = {}
    card_title = "Remembrall"
    speech_output = "Welcome to the Alexa Remembrall skill. " \
                    "You can store information about items you handle by just telling what item and where you placed them" \
                    "Or you can ask me for information about items already you stored by simply framing a where question" \
                    "Or you can ask for the list of items at a particular location."
    reprompt_text = "Please ask me for information about items about you previously stored or store new information"
    should_end_session = False
    return build_response(session_attributes, build_speechlet_response(
        card_title, speech_output, reprompt_text, should_end_session))


def handle_yes_intent():
    session_attributes = {}
    card_title = "Remembrall"
    speech_output = "How can I help you further?"
    reprompt_text = ""
    should_end_session = False
    return build_response(session_attributes, build_speechlet_response(
        card_title, speech_output, reprompt_text, should_end_session))
        
        
def table_write(request, session):
    # items is false item is true
    bool = False
    item = request['intent']['slots']['item']['value']
    if inflect.singular_noun(item) is False:
        bool = True
    location = request['intent']['slots']['location']['value']
    loc = []
    if 'my' in location.split(' '):
        for i in location.split(' '):
            if i != 'my':
                loc.append(i)
            else:
                loc.append('your')
        location = ' '.join(loc)
    table.put_item(
        Item={
            'userID': session['user']['userId'].split('.')[-1],
            'itemName': item,
            'itemBool': bool,
            'location': location,
            'loggedTime': str(datetime.utcnow().time()),
            'loggedDate': str(datetime.utcnow().date())
        }
    )


def table_read_item(request, session):
    item = request['intent']['slots']['item']['value']
    response = table.scan(FilterExpression=Attr('userID').eq(session['user']['userId'].split('.')[-1]) & Attr('itemName').eq(item))
    item = response['Items']
    return(item)


def table_read_location(request, session):
        item = request['intent']['slots']['location']['value']
        response = table.scan(FilterExpression=Attr('userID').eq(session['user']['userId'].split('.')[-1]) & Attr('location').eq(item))
        item = response['Items']
        return(item)


def build_speechlet_response(title, output, reprompt_text, should_end_session):
    # builds the speechlet response
    return {
        "outputSpeech": {
            "type": "PlainText",
            "text": output,
            "ssml": "<speak>" + output + "</speak>"
        },
        "card": {
            "type": "Simple",
            "title": title,
            "content": output,
        },
        "reprompt": {
            "outputSpeech": {
                "type": "PlainText",
                "text": reprompt_text,
            }
        },
        "shouldEndSession": should_end_session
    }


def dialog_elicit_slot_item(request):
    return [
                {
                    "type": "Dialog.ElicitSlot",
                    "slotToElicit": "item",
                    "updatedIntent": {
                        "name": "StoreIntent",
                        "confirmaitonStatus": "NONE",
                        "slots":{
                            "location": {
                                "name": "location",
                                "value": request['intent']['slots']['location']['value'],
                                "confirmaitonStatus": "NONE"
                            },
                            "item":{
                                "name":"item",
                                "confirmaitonStatus":"NONE"
                            }
                        }
                    }
                }
            ]
   
    
def dialog_elicit_slot_location(request):
    return [
                {
                    "type": "Dialog.ElicitSlot",
                    "slotToElicit": "location",
                    "updatedIntent": {
                        "name": "StoreIntent",
                        "confirmaitonStatus": "NONE",
                        "slots":{
                            "item": {
                                "name": "item",
                                "value": request['intent']['slots']['item']['value'],
                                "confirmaitonStatus": "NONE"
                            },
                            "location":{
                                "name":"location",
                                "confirmaitonStatus":"NONE"
                            }
                        }
                    }
                }
            ]


def dialog_elicit_retrieve_item():
    return [
                {
                    "type": "Dialog.ElicitSlot",
                    "slotToElicit": "item",
                    "updatedIntent": {
                        "name": "RetrieveItemIntent",
                        "confirmaitonStatus": "NONE",
                        "slots":{
                            "item":{
                                "name":"item",
                                "confirmaitonStatus":"NONE"
                            }
                        }
                    }
                }
            ]


def dialog_elicit_retrieve_location():
    return [
                {
                    "type": "Dialog.ElicitSlot",
                    "slotToElicit": "location",
                    "updatedIntent": {
                        "name": "RetrieveLocationIntent",
                        "confirmaitonStatus": "NONE",
                        "slots":{
                            "location": {
                                "name": "location",
                                "confirmaitonStatus": "NONE"
                            }
                        }
                    }
                }
            ]
            
            
def build_response(session_attributes, speechlet_response):
    # returns the response json
    return {
        "version": "1.0",
        "sessionAttributes": session_attributes,
        "response": speechlet_response
    }


def build_dialog_response(output, directives):
    # returns the response json
    return {
        "version": "1.0",
        "sessionAttributes": {},
        "response": {
            "outputSpeech": {
                "type": "PlainText",
                "text": output
            },
            "shouldEndSession": False,
            "directives": directives
        }
    }
