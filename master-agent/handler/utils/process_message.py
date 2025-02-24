import json
import uuid
import boto3
from config.index import CAR_CERTIFIED_IMAGE_URL, CAR_FEATURED_IMAGE_URL, CAR_POPULAR_IMAGE_URL, CURRENT_ENV, S3_URL
from utils.add_car import add_car_offer
from utils.generate_payment_link import generate_payment_link
from utils.add_direct_deal import add_direct_deal,start_convo,send_convo,end_convo
from utils.add_wishlist import add_wishlist
import requests
from datetime import datetime
from utils.chat import add_messages, get_messages
from config.index import TEST_ENV
from utils.add_car import add_car,remove_car,add_car_images
from agents.master import master_agent
from utils.transcribe_audio_from_s3 import transcribe_audio_from_s3


lambda_client = boto3.client("lambda",
    region_name = "ap-south-2" if CURRENT_ENV == "dev" else "ap-south-1"
)

def process_message(data):
    try:
        message_type = data.get("type", "text")
        voice_url = ""
        phone_number = data.get("user")

        if not phone_number:
            raise ValueError("Missing 'user' key in the input data.")
        media_urls= data.get("urls", [])
        file_name = data.get("fileName","")
        timestamp=data.get("timestamp", "")
        car_id = data.get("car_id", "")
        action_type=data.get("action_type","")
        user_message = data.get("message")
        message_source=data.get("source")
        voice_id= data.get("voiceId",""),
        data=None


     # Check if the message is a voice type (WhatsApp scenario)
        if message_type == "voice":
            try:
                    # Transcribe the audio file from S3
                res = transcribe_audio_from_s3(file_name)
                print("Transcription Result:", json.dumps(res, indent=2))
                user_message = res
                voice_url = S3_URL + file_name
            except Exception as audio_error:
                print("Audio Error:", str(audio_error))
                return {
                        "statusCode": 200,
                        "body": json.dumps({
                            "message": "Couldn't hear properly. Please try again.",
                            
                        }),
                        "headers": {
                                "Content-Type": "application/json",
                                "Access-Control-Allow-Origin": "*",
                        },
                    }


        # Retrieve messages and agent info
        messages, agent_exists, user_name, user_role = get_messages(phone_number, user_message,message_source,message_type,voice_url,media_urls,timestamp=timestamp, car_id=car_id, action_type=action_type)
        
        user_role = "Dealer"
        env = "PROD"
        print(f"\nuser_role: {user_role}\n")
        print(f"\nEnv: {env}\n")
        
        if message_source == "whatsapp" and message_type =="text" and "end" in user_message.lower():
            print("called")
            convo_exists,person = end_convo(phone_number)
            
            if convo_exists:
                 return {
                    "statusCode": 200,
                    "body": json.dumps({
                        "user":phone_number,
                        "person":person,
                        "type": "end_convo",
                    }),
                    "headers": {
                            "Content-Type": "application/json",
                            "Access-Control-Allow-Origin": "*",
                    },
            }
        elif message_source == "whatsapp":
            convo_exists,convo_id=send_convo(phone_number)
            print("convo_extists",convo_id,convo_exists)
            if convo_exists:
                 return {
                    "statusCode": 200,
                    "body": json.dumps({
                        "message": user_message,
                        "convoId": convo_id,
                        "user": phone_number,
                        "type": "convo",
                        "message_type": message_type,
                        "voice_url": voice_url,
                        "media_urls": media_urls,
                        "voiceId":voice_id
                    }),
                    "headers": {
                            "Content-Type": "application/json",
                            "Access-Control-Allow-Origin": "*",
                    },
            }


        current_time = datetime.now()  # Get the current local time
        iso_time = current_time.isoformat() 
        # Create a new message entry
        user_new_message = {
            "message_id": str(uuid.uuid4()),
            "role": "user",
            "content": user_message,
            "timestamp": iso_time,
            "message_source": message_source,
            'messageType': message_type,
            'voiceUrl':  voice_url,
            'urls': media_urls
        }

        assistant_response = None
        intent = ""

        # Handle local environment
        if TEST_ENV == "LOCAL":
            response = requests.post(
                "http://host.docker.internal:3000/agent/chat/sell",
                json={
                    "messages": messages,
                    "phoneNumber": phone_number,
                    "message": user_message
                }
            )
            assistant_response = response.json()
        else:
            # Get intent from the user's message
            # intent = get_intent(user_message, messages)
            # print("intent:", intent)
            # user_new_message["intent"] = intent

            # if not intent:
            #     message = "Sorry unable to process. Do you want to buy or sell?"
            #     # Update agent conversation history
            #     add_messages(message, agent_exists, phone_number, user_name, user_new_message)
            #     return {
            #         "statusCode": 200,
            #         "body": json.dumps({
            #             "message": message,
            #             "source": data.get("source")
            #         })
            #     }

            # # Invoke the appropriate Lambda function based on intent
            # lambda_name = get_lambda_intent(intent)
            # print("lambdaName:", lambda_name)

            # params = {
            #     "FunctionName": lambda_name,
            #     "InvocationType": "RequestResponse",
            #     "Payload": json.dumps({
            #         "messages": messages,
            #         "phoneNumber": phone_number,
            #         "message": user_message
            #     })
            # }

            # response = lambda_client.invoke(**params)
            print("line 80")

            response = master_agent(messages, phone_number, user_role, env)
            print("response",response)
        #     response_payload = json.loads(response["Payload"].read())
        #     print("responsePayload:", response_payload)

        #     body = json.loads(response_payload.get("body", "{}"))
        #     print("body:", body)
            assistant_response = response

#make offer with price
            # assistant_response=       {
            #         "message": "You have chosen to make an offer of 2 lakhs for the Maruti Vitara Brezza from the year 2023. I will now connect you to the seller.",
            #         "message_source": "web",
            #         "data": {},
            #         "url": "",
            #         "intent": "",
            #         "type": "car_offer",
            #         "AI request": "",
            #         "vin": "TS07JC9694",
            #         "price": "2 lakhs",
            #         "messageType": "text",
            #         "voiceType": ""
            #         }
            #assistant_response={'message': 'Images have been successfully added to your car: Hyundai Verna (2019) - VIN: MH21CB2765.', 'source': None, 'data': {'vin': 'MH21CB2765', 'attributes': {'make': 'Hyundai', 'model': 'Verna', 'trim': 'LX', 'year': 2019}, 'carId': '85cf2e9c-95de-4283-b2ff-3cfb189c68c41733576623'}, 'intent': 'image_handler_tool', 'type': 'image_upload'}
            # assistant_response={'message': "Sure, I am connecting you to the seller of the Honda Unicorn. This car is from 2008, it's black in color and has a VIN of MH03AP6722. The car has a mileage of 12396 and uses CNG as its fuel type. It's currently located in Mumbai, MH and is priced at 900000.",
            #                     'source': None, 'data': [
            #                         {'locationData':
            #                             {'country': 'IN', 
            #                             'zipCode': '400083',
            #                             'address': '333, Seth Govindram Jolly Marg, Sona Intp Colony, Tagore Nagar, Vikhroli,',
            #                             'city': 'Mumbai', 
            #                             'state': 'MH'}, 
            #                          'bidsStartingPrice': '',
            #                          'year': 2008,
            #                          'trim': 'HDHDB',
            #                          'price': 900000,
            #                          'vin': 'UP23CN1987',
            #                          'model': 'UNICORN',
            #                          'car_id': 'a576be5c-3e71-4d4b-b108-931d07e7b5e71733852984',
            #                          'make': 'HONDA',
            #                          'bidsEnabled': False,
            #                          'image': 'https://dp7pp8go7lr8i.cloudfront.net/carimages/MH03AP6722/17115405649094.jpg', 
            #                          'sold': False, 
            #                          'visible': True,
            #                          'url': 'https://www.carxstream.in/products/buy/2008-HONDA-UNICORN-Mumbai-MH-400083-48d9741a-493a-4b30-835e-a27676e384c81711540517400'}], 
            #                          'URL': '', 
            #                          'intent': 'buy_tool', 
            #                          'type': 'connect'}
            print("assistantResponse:", assistant_response)
            data= assistant_response.get("data",None)
            url = ""

            # Handle car upload scenario
            if assistant_response.get("type") == "car_upload":
                print("car_data:", assistant_response.get("data"))
                resp,urlValue = add_car(assistant_response["data"], phone_number,user_role)
                print("urlValue",urlValue)
                if resp['success'] == False:
                    print("resp",resp)
                    assistant_response = {
                        **assistant_response,
                        'message': resp['message']
                    }
                else: 
                    data = {
                        **{key: value for key, value in assistant_response["data"].items() if key != "location"}, 
                        "carLocation": assistant_response["data"].get("location") 
                    }
                    print("line 118",data)
               
                    assistant_response = {
                        **assistant_response,
                        'data': data
                    }
                    print("line 123",assistant_response)
                    assistant_response["message"] = assistant_response["message"] +  f"\n\nYou can see your uploaded car here {urlValue}"
                   

                #work on this
                # car_body = json.loads(resp["body"])
                # url = car_body["Item"]["url"]
                # print("car upload url:", url)
                #if car exists please response wioth error
                url = urlValue if urlValue is not None else ""
                
            elif assistant_response.get("type") == "shortlisted":
                print("shortlist_data",assistant_response.get("data"))
                #resp= 
                resp = add_direct_deal(assistant_response["data"],phone_number)
                
                data=assistant_response.get("data")
                    
                print("car upload url:", url)
            elif assistant_response.get("type") == "wishlist":
                print("wishlist_data",assistant_response.get("data"))
                data=assistant_response.get("data")
                resp = add_wishlist(assistant_response["data"],phone_number)
                print("added to wishlist",resp)
            elif assistant_response.get("type") == "car_upgrade":
                data = assistant_response.get("data")
                resp = generate_payment_link(amount=assistant_response.get("data")["price"] ,vehicle_number=assistant_response.get("data")["vehicle_number"],user_role=user_role,phone_number=phone_number,source=message_source)
                if resp['success'] == False:
                    print("resp",resp)
                    assistant_response = {
                        **assistant_response,
                        'message': resp['message'],
                    }

                else:
                    print("resp",resp)
                    if message_source == 'app':
                        assistant_response = {
                            **assistant_response,
                            'message': resp['message'],
                            'data':{
                                'checksum': resp['checksum'],    
                                'base64Encoded': resp['base64Encoded'],
                                'price':data['price'], 
                                'carId':resp['carId'],
                                'packageId': resp['packageId'],
                                'isPaid': False
                            },


                        }
                        data={
                            'checksum': resp['checksum'],    
                            'base64Encoded': resp['base64Encoded'],
                            'price':data['price'],
                            'carId':resp['carId'],
                            'packageId': resp['packageId'],
                            'isPaid': False     
                        }
                    else:
                        url= resp['url']
                        assistant_response = {
                            **assistant_response,
                            'message': resp['message'],
                            'url': resp['url'],
                            'data':{
                                'price':data['price'], 
                                'carId':resp['carId'],
                                'packageId': resp['packageId'],
                                'isPaid': False     
                            },    
                        }
                        data={
                            'carId':resp['carId'],
                            'packageId': resp['packageId'],
                            'isPaid': False  
                        }
                            
                    
            elif assistant_response.get("type") == "car_upgrade_showing":
                    data={
                        **assistant_response["data"],
                        'packages': [
                            f"{S3_URL}{CAR_FEATURED_IMAGE_URL}",
                            f"{S3_URL}{CAR_POPULAR_IMAGE_URL}"
                        ]
                    }
                    assistant_response = {
                        **assistant_response,
                        'message': assistant_response['message'],
                        'data':data

                    }
                
            elif assistant_response.get("type") == "delete_car":
                    print("delete_car")
                    if assistant_response.get('vehicle_number'):  # Check if 'data' exists and 'vehicle_number' is present
                        resp = remove_car(vehicle_number=assistant_response["vehicle_number"], phone_number=phone_number)
                        print("resp",resp)
                        if resp['success'] == False:

                            assistant_response = {
                                **assistant_response,
                                'message': resp['message'],
                            }
                        else:
                            assistant_response = {
                                **assistant_response,
                                'message': resp['message'],
                                'data': data
                            }
                
            elif assistant_response.get("type") == "image_upload":
                resp=add_car_images(assistant_response["data"],phone_number)
                if resp['success'] == False:
                    print("resp",resp)
                    assistant_response = {
                        **assistant_response,
                        'message': resp['message']
                    }
                    
              
            elif assistant_response.get('type') == 'browse':
                data = [] if assistant_response.get("data") == {} else assistant_response.get("data")
                
  
            elif assistant_response.get('type') == 'connect':
                print("data",data)
                resp,urlValue = start_convo(car_id=data[0]["car_id"],phone_number=phone_number)
            
            elif assistant_response.get('type') == 'car_offer':
                resp = add_car_offer(vin=assistant_response.get("vin"),price=assistant_response.get("price"),phone_number=phone_number)
                if resp['success'] == False:
                    print("resp",resp)
                    assistant_response = {
                        **assistant_response,
                        'message': resp['message']
                }
                else: 
                    data={
                        'offerId':resp["offerId"],
                    }
                    assistant_response = {
                        **assistant_response,
                        'message': resp['message'],
                        'data': data
                    }  

            elif assistant_response.get('type') == 'test_drive_home':
                return {
                            "statusCode": 200,
                            "body": json.dumps({
                                "message":assistant_response.get("message"),
                                "message_source": message_source,
                                "data": data,
                                "url": url,
                                "intent": intent,
                                "type": assistant_response.get("type") if "type" in assistant_response else "",
                                "date": assistant_response.get("date",""),
                                "time": assistant_response.get("time",""),
                                "location": assistant_response.get("location",""),
                                "vin": assistant_response.get("vin",""),
                                'messageType':'text',
                                'voiceType':''
                            }),
                            "headers": {
                                    "Content-Type": "application/json",
                                    "Access-Control-Allow-Origin": "*",
                            },
                        }

            elif assistant_response.get('type') == 'test_drive_seller':
                return {
                            "statusCode": 200,
                            "body": json.dumps({
                                "message":assistant_response.get("message"),
                                "message_source": message_source,
                                "data": data,
                                "url": url,
                                "intent": intent,
                                "type": assistant_response.get("type") if "type" in assistant_response else "",
                                "date": assistant_response.get("date",""),
                                "time": assistant_response.get("time",""),
                                "vin": assistant_response.get("vin",""),
                                'messageType':'text',
                                'voiceType':''
                            }),
                            "headers": {
                                    "Content-Type": "application/json",
                                    "Access-Control-Allow-Origin": "*",
                            },
                        }
            
            elif assistant_response.get('type') == 'car_loan':
                return {
                            "statusCode": 200,
                            "body": json.dumps({
                                "message":assistant_response.get("message"),
                                "message_source": message_source,
                                "data": data,
                                "url": url,
                                "intent": intent,
                                "type": assistant_response.get("type") if "type" in assistant_response else "",
                                "amount": assistant_response.get("amount",""),
                                "vin": assistant_response.get("vin",""),
                                'messageType':'text',
                                'voiceType':''
                            }),
                            "headers": {
                                    "Content-Type": "application/json",
                                    "Access-Control-Allow-Origin": "*",
                            },
                        }

            elif assistant_response.get('type') == 'connect_seller':
                return {
                            "statusCode": 200,
                            "body": json.dumps({
                                "message":assistant_response.get("message"),
                                "message_source": message_source,
                                "url": url,
                                "intent": intent,
                                "type": assistant_response.get("type") if "type" in assistant_response else "",
                                "car_id": assistant_response.get("car_id", None),
                                'messageType':'text',
                                'voiceType':''
                            }),
                            "headers": {
                                    "Content-Type": "application/json",
                                    "Access-Control-Allow-Origin": "*",
                            },
                        }


        # # Update the agent conversation history
            add_messages(
                assistant_response,
                agent_exists,
                phone_number,
                user_name,
                user_new_message, 
                message_source,
            )

        return {
            "statusCode": 200,
            "body": json.dumps({
                "message":assistant_response.get("message"),
                "message_source": message_source,
                "data": data,
                "url": url,
                "intent": intent,
                "type": assistant_response.get("type") if "type" in assistant_response else "",
                'messageType':'text',
                'voiceType':''
            }),
            "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
            },
        }
        

    except Exception as error:
        print("error:", error)
        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": "Sorry, couldn't understand. Please try again.",
               
            }),
             "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
            },
        }