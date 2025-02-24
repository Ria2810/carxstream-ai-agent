from utils.add_car import get_user_cars
from langchain_openai import ChatOpenAI
from config.index import OPENAI_API_KEY

# Initialize gpt-4o-mini
gpt4_mini_model = ChatOpenAI(temperature=0, model="gpt-4o-mini", openai_api_key=OPENAI_API_KEY)

def handle_media_and_car_selection(latest_message, phone_number, session_data):
    """
    Handles media detection, prompts user for action, and manages car image uploads and car selection together.
    """
    def generate_response(prompt):
        """Helper function to generate AI response."""
        try:
            result = gpt4_mini_model.generate([prompt])  # Generate response
            return result.generations[0][0].text  # Extract the content
        except Exception as e:
            print("Error generating response:", str(e))
            return "An error occurred while generating a response."

    if latest_message.get("type") == "media" or latest_message.get("messageType") == "media":
        print("Fetching car details")
        cars = get_user_cars(phone_number)
        if not cars:
            # If no cars exist, ask to upload a car
            prompt = "You do not have any cars listed. Would you like to upload a car first?"
            session_data["type"] = "car_upload_prompt"
            ai_response = generate_response(prompt)
            return {
                "message": ai_response,
                "source": None,
                "data": {},
                "type": "car_upload_prompt",
            }

        # Present car options to the user
        car_options = "\n".join(
            [f"{idx + 1}. {car['attributes']['make']} {car['attributes']['model']} ({car['vin']})"
             for idx, car in enumerate(cars)]
        )
        prompt = f"Do you wish to add these images to your car details?\nWhich car would you like to add these images to?\n{car_options} Give the details of cars in response as well."
        session_data["type"] = "car_selection"
        session_data["cars"] = cars
        ai_response = generate_response(prompt)
        return {
            "message": ai_response,
            "source": None,
            "type": "car_selection_prompt",
        }

    # Handle car selection
    if session_data.get("type") == "car_selection" and "cars" in session_data:
        try:
            selected_index = int(latest_message["content"]) - 1
            if 0 <= selected_index < len(session_data["cars"]):
                selected_car = session_data["cars"][selected_index]
                vin = selected_car["vin"]

                # Confirm image upload
                prompt = f"Images have been successfully added to your car: {selected_car['attributes']['make']} {selected_car['attributes']['model']} ({vin})."
                session_data["type"] = "image_upload"
                ai_response = generate_response(prompt)
                return {
                    "message": ai_response,
                    "source": None,
                    "data": {"vehicle_number": vin},
                    "type": "image_upload",
                }
            else:
                prompt = "Invalid selection. Please choose a valid option."
                ai_response = generate_response(prompt)
                return {
                    "message": ai_response,
                    "source": None,
                    "data": {},
                    "type": "car_selection_error",
                }
        except ValueError:
            prompt = "Invalid input. Please enter a number corresponding to your choice."
            ai_response = generate_response(prompt)
            return {
                "message": ai_response,
                "source": None,
                "data": {},
                "type": "car_selection_error",
            }

    return None
