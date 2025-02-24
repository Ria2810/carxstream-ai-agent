from config.index import OPENAI_API_KEY
from openai import OpenAI

client = OpenAI(api_key=OPENAI_API_KEY)

def check_message(text):
    data=[]
    # Add a text entry
    data = add_dynamic_entry(data, "text", text)

    # Add an image entry
    #data = add_dynamic_entry(data, "image", "https://example.com/image.png")


    
    response = client.moderations.create(
    model="omni-moderation-latest",
    input=data,
    )
    # Check if the data is safe
    data_is_safe = is_data_safe(response)
    print(data_is_safe) 
    return data_is_safe



def add_dynamic_entry(data_list, data_type, content):
    """
    Adds a text or image entry to the data list dynamically based on the type.
    
    Parameters:
        data_list (list): The list to append the new entry to.
        data_type (str): The type of entry ('text' or 'image').
        content (str): The content for the entry (text or URL).

    Returns:
        list: Updated data list with the new entry.
    """
    if data_type == "text":
        data_list.append({"type": "text", "text": content})
    elif data_type == "image":
        data_list.append({
            "type": "image_url",
            "image_url": {
                "url": content
            }
        })
    else:
        raise ValueError("Invalid data type. Supported types are 'text' or 'image'.")
    return data_list




def is_data_safe(response):
    try:
        # Iterate over the results
        for result in response.results:  # Access the 'results' attribute
            # Iterate over the categories and check if any are flagged as True
            for category, value in result.categories.__dict__.items():  # Use __dict__ to get all attributes
                if value:  # If the category is flagged (True)
                    return True  # Return False (indicating error)
        return False  # Return True if no flagged categories are found
    except AttributeError as e:
        print(f"Error accessing categories: {e}")
        return False  # Return False if there is any error accessing the category data
