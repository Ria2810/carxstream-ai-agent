import boto3
import json
from datetime import datetime
from utils.elastic import client
from uuid import uuid4
from utils.add_user import add_user
from config.index import ELK_AGENT_ENGINE, ELK_USER_ENGINE,CURRENT_ENV
from elasticsearch import NotFoundError,BadRequestError


# Initialize AWS Lambda client
lambda_client = boto3.client('lambda',
        region_name = "ap-south-2" if CURRENT_ENV == "dev" else "ap-south-1" # Specify the AWS region
    )

def get_messages(phone_number, user_message,message_source,message_type,voice_url,media_urls,timestamp, car_id, action_type):
    agent_exists = False
    messages = []

    # Fetch existing messages from Elasticsearch
 
    # Query parameters
    query = {
        "number": phone_number  # Replace with the actual number filter value
    }
    size = 10  # Adjust the size of results as needed
    from_offset = 0  # Adjust the offset for pagination
    
    search_query=""

    if timestamp != "":
        date_part = timestamp.split("T")[0]
        print("part", date_part)
        search_query=     {
        "query": {
            "bool": {
            "must": [
                {
                "match": {
                        "number": str(query.get("number"))
                    }
                    }
                ]
                }
            },
            "aggs": {
                "nested_messages": {
                "nested": {
                    "path": "messages"
                },
                "aggs": {
                    "group_by_date": {
                    "filter": {
                        "range": {
                        "messages.timestamp": {
            "gte": f"{date_part}T00:00:00",
            "lte": f"{date_part}T23:59:59"
                        }
                        }
                    },
                    "aggs": {
                        "messages_per_date": {
                        "top_hits": {
            "from":from_offset,
            "size": size,
            "sort": [
            {
                "messages.timestamp": {
                "order": "desc"
                }
            }
            ]
                        }
                        }
                    }
                    }
                }
                }
            },
            "size": 0
            }
    else:
        search_query=  {
                "query": {
                    "bool": {
                    "must": [
                        {
                        "match": {
                            "number":str(query.get("number")) 
                        }
                        },
                        {
                        "nested": {
                            "path": "messages",
                            "query": {
                            "match_all": {}
                            },
                            "inner_hits": {
                            "from": from_offset,
                            "size": size,
                            "sort": [
                                {
                                "messages.timestamp": {
                                    "order": "desc"
                                }
                                }
                            ]
                            }
                        }
                        }
                    ]
                    }
                },
            "_source": False
            }
        # Perform the search using the Elasticsearch client
    response = client.search(
        index=ELK_AGENT_ENGINE,
        body=search_query,
        _source=["number"] # Adjust to include/exclude specific fields
    )
    print("message_response",response)
    # Extract messages from the search response
      

    messages=[]

    if timestamp != "":
        for bucket in response["aggregations"]["nested_messages"]["group_by_date"]["messages_per_date"]["hits"]["hits"]:
            message = bucket["_source"]
            messages.append(message)

            messages = messages[::-1]
    else:
        hits = response.get("hits", {}).get("hits", [])
        # Assuming you're extracting inner hits from the first document
        if hits:
            messages = [
                        item["_source"]
                        for item in hits[0].get("inner_hits", {})
                                            .get("messages", {})
                                            .get("hits", {})
                                            .get("hits", [])
                    ][::-1]
        else:
            messages = []
        # response = client.get(index=ELK_AGENT_ENGINE, id=phone_number, _source_includes=["messages"])

        print("userMe",messages)

        
        
    if len(messages) > 0:
            agent_exists = True
       
           
            
            
    try:
        # Try to fetch the document
        user_response = client.get(
                index=ELK_AGENT_ENGINE,
                id=phone_number,
                _source_includes=["number"]  # Fetch only the fields you need
            )
            # Document exists, process the response
        print("User exists:", user_response["_source"])
    except NotFoundError:
        # Document does not exist
        print(f"User with phone number {phone_number} does not exist.")
        print("User not exists adding")
        current_time = datetime.now()  # Get the current UTC time
        iso_time = current_time.isoformat()
        new_user = {
                            "number": phone_number,
                            "messages": [],
                            "createdAt": iso_time,
                            "updatedAt": iso_time,
                            "24hWindowActive": True if message_source == "whatsapp" else False,
                            "last_customer_message_time": iso_time,
                        }
        print("new_user", new_user)

        response = client.index(index=ELK_AGENT_ENGINE, id=phone_number, body=new_user)
        print("Agent created successfully.")   
        agent_exists = True    
        
 

    # Fetch user data from Elasticsearch
    user_query = {
        "match": {
            "number": phone_number
        }
    }

    try:
        user_response = client.search(index=ELK_USER_ENGINE, body={
            "query": user_query,
            "_source": ["role", "dealerName", "firstName", "lastName", "email","role"]
        })
    except Exception as e:
        print("Error fetching user data:", e)
        return {
            "statusCode": 500,
            "body": json.dumps({"message": "Error fetching user data"}),
             "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
            },
        }

    hits = user_response['hits']['hits']
    print("User data:", hits)

    user_name = "Unknown"
    user_role="user"
    email = ""

    if len(hits) > 0:
        user = hits[0]['_source']
        role = user.get('role', '')
        email = user.get('email', '')
        user_role = user.get('role', 'user')

        if role == "dealer":
            dealer_name = user.get('dealerName', '')
            if dealer_name:
                user_name = dealer_name
            elif user.get('firstName') and user.get('lastName'):
                user_name = f"{user['firstName']} {user['lastName']}"
        elif role == "user":
            first_name = user.get('firstName', '')
            last_name = user.get('lastName', '')
            if first_name and last_name:
                user_name = f"{first_name} {last_name}"
            elif first_name:
                user_name = first_name
            elif last_name:
                user_name = last_name
    else:
        user_res = add_user(phone_number)
        print("Added new user:", user_res)
   

    print("User name:", user_name)
    current_time = datetime.now()  # Get the current local time
    iso_time = current_time.isoformat() 
    # Add new user message
    user_new_message = {
        "message_id": str(uuid4()),
        "role": "user",
        "content": user_message,
        "timestamp": iso_time,
        "message_source":message_source,
        'messageType':message_type,
        'voiceUrl':voice_url,
        'urls': media_urls,
        'action_type':action_type,
        'car_id':car_id
    }

    messages.append(user_new_message)
    print("messages user",messages)
    return messages,agent_exists,user_name,user_role



def add_messages(assistant_response, agent_exists, phone_number, user_name, user_new_message, message_source):
    current_time = datetime.now()  # Get the current UTC time
    iso_time = current_time.isoformat()  # Get the ISO format timestamp for Elasticsearch
    new_messages = [
        {
            "message_id": str(uuid4()),
            "role": "assistant",
            "content": assistant_response["message"],
            "timestamp": iso_time,
            "data": assistant_response.get("data"),
            "type": assistant_response.get("type"),
            "url": assistant_response.get("url"),
            "intent": assistant_response.get("intent"),
            'message_source': message_source,
            'messageType': 'text',
            'voiceUrl': '',
        }
    ]

    # Insert the user's new message at the start of the messages list
    new_messages.insert(0, user_new_message)
    print("New Messages:", new_messages)

    try:
        if agent_exists:
            print("Updating document...")
            # Elasticsearch update script
            update_script = """
            // Ensure 'messages' is initialized as an empty array if it does not exist
            if (!ctx._source.containsKey('messages')) {
                ctx._source.messages = [];
            }

            // Add new messages if 'new_message' is provided
            if (params.new_message != null) {
                for (message in params.new_message) {
                    ctx._source.messages.add(message);
                }
            }

            // Update the 'updatedAt' field if the timestamp is provided
            if (params.updatedAt != null) {
                ctx._source.updatedAt = params.updatedAt;
            }

            // Ensure 'last_message_source' is set
            if (params.source != null) {
                ctx._source.last_message_source = params.source;
            }

            // Ensure 'last_customer_message_time' is set only for WhatsApp messages
            if (params.source == "whatsapp") {
                ctx._source.last_customer_message_time = params.updatedAt;
            }

            // Calculate if the 24-hour window is active based on the last customer message time
            if (ctx._source.containsKey('last_customer_message_time') && params.updatedAt != null) {
                if (params.source == "whatsapp") {
                    // Use DateTimeFormatter to parse the timestamp with microseconds
                    def formatter = DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm:ss.SSSSSS");
                    def last_message_time = LocalDateTime.parse(ctx._source.last_customer_message_time, formatter);
                    def current_time = System.currentTimeMillis(); // Get current time in milliseconds

                    // Calculate the time difference in milliseconds
                    def last_message_time_in_millis = last_message_time.atZone(ZoneId.systemDefault()).toInstant().toEpochMilli();
                    def time_difference = current_time - last_message_time_in_millis;

                    // Check if the 24-hour window has expired
                    def window_expired = time_difference > (24 * 60 * 60 * 1000); // 24 hours in milliseconds
                    ctx._source['24hWindowActive'] = !window_expired;  // Only update if it's whatsapp
                }
            }

            // Initialize 'last_message_time' if the message is from WhatsApp
            if (params.source == "whatsapp" && params.updatedAt != null) {
                ctx._source.last_message_time = params.updatedAt;
            }

            // Initialize '24hWindowActive' if it does not exist, but for all message sources (initialize as true for WhatsApp)
            if (!ctx._source.containsKey('24hWindowActive')) {
                ctx._source['24hWindowActive'] = (params.source == "whatsapp") ? true : false;  // true for WhatsApp, false for others
            }
        """

        # Add the current message timestamp and other params to the script
            response = client.update(
                index=ELK_AGENT_ENGINE,
                id=phone_number,
                body={
                    "script": {
                        "source": update_script,
                        "params": {
                            "new_message": new_messages,
                            "user_name": user_name,
                            "updatedAt": iso_time,
                            "source": message_source  # Can be "App", "Web", or "WhatsApp"
                        }
                    },
                    "upsert": {
                    "messages": new_messages,
                    "user_name": user_name if user_name != "Unknown" else None,
                    "updatedAt": iso_time,
                    "last_customer_message_time": iso_time, 
                    "last_message_source": message_source 
                }
            }
        )

            
            print("Updated agent message successfully.")
        else:
            # Add a new agent document if one does not exist
            current_time = datetime.now()  # Get the current UTC time
            iso_time = current_time.isoformat()
            print("Adding new document...")
            new_user = {
                "number": phone_number,
                "messages": new_messages,
                "createdAt": iso_time,
                "updatedAt": iso_time,
                "24hWindowActive":False,
                "24hWindowActive": True if message_source == "whatsapp" else False,
                "last_customer_message_time": iso_time,
            }
            print("new_user", new_user)

            response = client.index(index=ELK_AGENT_ENGINE, id=phone_number, body=new_user)
            print("Agent created successfully.")
    except BadRequestError as e:
        # If it's an Elasticsearch-specific exception, print detailed info
        print("Error adding/updating message:")
        print("Error type:", type(e).__name__)
        print("Error details:", e)
        if hasattr(e, 'info'):
            print("Error info:", e.info)  # Detailed response from Elasticsearch
        if hasattr(e, 'meta'):
            print("Error metadata:", e.meta)  # HTTP response metadata, like status code
        if hasattr(e, 'status_code'):
                print("HTTP status code:", e.status_code)
    except Exception as e:
        # Catch all other exceptions
        print("An unexpected error occurred:")
        print("Error type:", type(e).__name__)
        print("Error details:", e)





def add_payment_message(phone_number,message,package_id):
    current_time = datetime.now()  # Get the current UTC time
    iso_time = current_time.isoformat() 
    new_messages = [
        {
            "message_id": str(uuid4()),
            "role": "assistant",
            "content": message,
            "timestamp": iso_time,
            "data":  None,
            "type":  None,
            "url": None,
            "intent": "payment",
            'message_source': '',
            'voiceUrl':'',
            'messageType':'text',
        }
    ]


    print("New Messages:", new_messages)

    try:
        
        print("Updating document...")
        update_script = """
                if (ctx._source.messages == null) {
                    ctx._source.messages = [];
                }

                // Update old messages with the matching packageId
                for (message in ctx._source.messages) {
                    // Ensure message.data is an object and packageId exists
                    if (message.data != null && message.data instanceof Map && message.data.containsKey('packageId') && message.data.packageId == params.packageId) {
                        message.data.isPaid = true;  // Set isPaid to true for the matching packageId
                    }
                }

                // Add new messages to the array
                for (message in params.new_message) {
                    ctx._source.messages.add(message);
                }

                ctx._source.updatedAt = params.updatedAt;

            """
            
        print("packageId",{
                    "new_message": new_messages,
                    "updatedAt": iso_time,
                    "packageId": package_id,
                })
        current_time = datetime.now()  # Get the current UTC time
        iso_time = current_time.isoformat() 
        response = client.update(index=ELK_AGENT_ENGINE, id=phone_number, body={
            "script": {
                "source": update_script,
                "params": {
                    "new_message": new_messages,
                    "updatedAt": iso_time,
                    'packageId': package_id
                }
            },
            "upsert": {
                "messages": new_messages,
                "updatedAt": iso_time
            }
        })
        print("Updated agent message successfully.")
        
        return {
            "statusCode": 200,
            "body": json.dumps({
                
            }),
            "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
            },
        }
        
        
       
    except Exception as e:
        print("Error adding/updating message:", e)
          
        return {
            "statusCode": 500,
            "body": json.dumps({
                
            }),
            "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
            },
        }
