# Define the lambdas
lambdas = ["ai-agent-handler-sell", "ai-agent-handler-search"]

def get_lambda_intent(intent):
    if intent == "sell":
        return lambdas[0]
    elif intent == "buy":
        return lambdas[1]
    else:
        return ""
