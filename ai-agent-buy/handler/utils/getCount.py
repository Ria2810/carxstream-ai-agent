from utils.elastic import elasticsearch_client, store
from config.Constants import ES_INDEX,CURRENT_ENV,PROD_URL,DEV_URL


def get_total_count():
    """
    Perform a search query and return the total count of matching documents.
    """
    try:
        # Construct the Elasticsearch query using fields from your data structure
        search_query = {
                "query": {
                    "bool": {
                        "filter": [
                            {"term": {"sold": False}},  # Only include unsold cars
                            {"term": {"visible": True}}  # Only include visible cars
                        ]
                    }
                }
            }

        # Perform the count query
        response = elasticsearch_client.count(index=ES_INDEX, body=search_query)

        # Extract and return the count
        count = response.get("count", 0)
        return count

    except ValueError as ve:
        print(f"Query error: {ve}")
        return 0
    except Exception as e:
        print(f"Error retrieving count by query: {e}")
        return 0

def get_count_by_query(query):
    """
    Perform a search query and return the total count of matching documents.
    """
    try:
        # Construct the Elasticsearch query using fields from your data structure
        search_query = {
                "query": {
                    "bool": {
                        "must": [
                        {
                            "multi_match": {
                                "query": query,
                                "fields": ["make", "model", "body_style", "fuel_type", "engine", "page_content"],
                                "operator": "or"
                            }
                        }
                        ],
                        "filter": [
                            {"term": {"sold": False}},  # Only include unsold cars
                            {"term": {"visible": True}}  # Only include visible cars
                        ]
                    }
                }
            }

        # Perform the count query
        response = elasticsearch_client.count(index=ES_INDEX, body=search_query)

        # Extract and return the count
        count = response.get("count", 0)
        return count

    except ValueError as ve:
        print(f"Query error: {ve}")
        return 0
    except Exception as e:
        print(f"Error retrieving count by query: {e}")
        return 0


if __name__ == "__main__":
    total = get_total_count()
    count = get_count_by_query("I want a car")
    print(f"Total: {total}\nCount by query: {count}")