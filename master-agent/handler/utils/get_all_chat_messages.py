from config.index import ELK_AGENT_ENGINE
from utils.elastic import client
from config.index import ELK_AGENT_ENGINE
import json
from datetime import datetime


def get_all_chat_messages(query):
    # Default size for pagination
    print("loine 8",query)
    size = int(query.get("size", 5))
    fromValue = int(query.get("from", 0))
    timestamp=query.get("timestamp","")
   

    # Build the query
    search_query=""
    
    
    if fromValue >= size:
            if  query["type"] == "v2":
                # Extract just the date
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
                                "from":fromValue,
                                "size": 5,
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
                 print("chalega")
                 search_query = {
                    "_source": False,
                    "query": {
                    "bool": {
                    "must": [
                        {
                        "match": {
                            "number": str(query.get("number"))
                        }
                        }
                    ],
                    "filter": [
                        {
                        "nested": {
                            "path": "messages",
                            "query": {
                            "match_all": {}
                            },
                            "inner_hits": {
                            "from": fromValue,
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
                }
            
                }
                
   
    
    elif query["type"] == "v2":
       
        search_query={
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
                                    "date_histogram": {
                                        "field": "messages.timestamp",
                                        "calendar_interval": "day",  "order": {
                                        "_key": "desc" 
                                        }
                                    },
                                    "aggs": {
                                        "messages_per_date": {
                                            "top_hits": {
                                                "from": fromValue,
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
        search_query = {
                  
                    "_source": False,
                    "query": {
                    "bool": {
                    "must": [
                        {
                        "match": {
                            "number": str(query.get("number"))
                        }
                        }
                    ],
                    "filter": [
                        {
                        "nested": {
                            "path": "messages",
                            "query": {
                            "match_all": {}
                            },
                            "inner_hits": {
                            "from": 0,
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
                }
            
                }
        

    
    
    print("loine 48",search_query)
    


    # Perform search using Elasticsearch client
    try:
        res = client.search(
            index=ELK_AGENT_ENGINE,
            body=search_query,
            _source=True,  # Adjust this to include/exclude specific fields or just use True
        )
        print("resasdadd",res)


        if fromValue >= size and query.get("type") == 'v2':
              # Extract and format the messages per day
            messages_per_day = []
            nested_messages = res["aggregations"]["nested_messages"]["group_by_date"]
           
            results=[]
           # Process the messages within the 'messages_per_date' aggregation
            if "messages_per_date" in nested_messages:
                    for hit in nested_messages["messages_per_date"]["hits"]["hits"]:
                        message = hit["_source"]
                        results.append({
                            "message_id": message.get("message_id"),
                            "role": message.get("role"),
                            "intent": message.get("intent", None),  # Optional field
                            "data": message.get("data", None),  # Optional field
                            "type": message.get("type", None),  # Optional field
                            "url": message.get("url", None),  # Optional field
                            "content": message.get("content"),
                            "timestamp": message.get("timestamp"),
                            "messageType": message.get("messageType",""),
                            "voiceUrl": message.get("voiceUrl",""),
                            "urls": message.get("urls",[]),
                            "message_source": message.get("message_source") if message.get("message_source") else message.get("source")
                        })

                # Extract the date (use `date_part` if needed, or infer from the messages)
                    # if results:
                    #      # Extract the date portion
                    #     messages_per_day.append(results[::-1])
                        

            return {
                "statusCode": 200,
                "body": json.dumps({
                    "messages":  results[::-1]
                }),
                "headers": {
                        "Content-Type": "application/json",
                        "Access-Control-Allow-Origin": "*",
                },
            }

        elif query["type"] == "v2":
         
             # Extract and format the messages per day
            messages_per_day = []
            nested_messages = res["aggregations"]["nested_messages"]["group_by_date"]
           

            for bucket in res["aggregations"]["nested_messages"]["group_by_date"]["buckets"]:
                date = bucket["key_as_string"]
                messages = []
                for hit in bucket["messages_per_date"]["hits"]["hits"]:
                    message = hit["_source"]
                    messages.append({
                            "message_id": message.get("message_id"),
                            "role": message.get("role"),
                            "intent": message.get("intent", None),  # Optional field
                            "data": message.get("data", None),  # Optional field
                            "type": message.get("type", None),  # Optional field
                            "url": message.get("url", None),  # Optional field
                            "content": message.get("content"),
                            "timestamp": message.get("timestamp"),
                            "messageType": message.get("messageType",""),
                            "voiceUrl": message.get("voiceUrl",""),
                             "urls": message.get("urls",[]),
                            "message_source": message.get("message_source") if message.get("message_source") else message.get("source")
                    })
                
                
                if len(messages)>0:
                    messages_per_day.append({
                        "date": date,
                        "messages": messages[::-1]
                    })
                    
                    

            return {
                "statusCode": 200,
                "body": json.dumps({
                    "messages":  messages_per_day
                }),
                "headers": {
                        "Content-Type": "application/json",
                        "Access-Control-Allow-Origin": "*",
                },
            }
        else:
                  # Extract and process the results
            inner_hits = (
                res["hits"]["hits"][0]["inner_hits"]["messages"]["hits"]["hits"]
                if res["hits"]["hits"]
                else []
            )
            messages = [item["_source"] for item in inner_hits][::-1]
            return {
                "statusCode": 200,
                "body": json.dumps({
                    "messages":  messages
                }),
                "headers": {
                        "Content-Type": "application/json",
                        "Access-Control-Allow-Origin": "*",
                },
            }
           
            # Extract and process the results
            # inner_hits = (
            #     res["hits"]["hits"][0]["inner_hits"]["messages"]["hits"]["hits"]
            #     if res["hits"]["hits"]
            #     else []
            # )
            # messages = [item["_source"] for item in inner_hits]
            
            
            

    except Exception as e:
        print(f"Error performing search: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)}),
            "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
            },
        }
