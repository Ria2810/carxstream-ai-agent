from string import Template
from langchain import PromptTemplate

def rephrase_follow_up(chat_history, follow_up_question):
    template = """Given the following conversation and a follow up question, rephrase the follow up question to be a standalone question, in its original language.

    Chat history:
    {% for dialogue_turn in chat_history -%}
    {% if dialogue_turn.type == 'human' %}Question: {{ dialogue_turn.content }}{% elif dialogue_turn.type == 'ai' %}Response: {{ dialogue_turn.content }}{% endif %}
    {% endfor -%}

    Follow Up Question: {{ follow_up_question }}
    Standalone question:
    """

    # Create the PromptTemplate, specifying the input variables used in the template
    prompt_template = PromptTemplate(
        input_variables=["chat_history", "follow_up_question"],
        template=template,
    )
    
    # Format the chat history by checking if each message is human or AI
    chat_history_formatted = "\n".join(
        f"Question: {turn.content}" if turn.type == 'human' else f"Response: {turn.content}"
        for turn in chat_history
    )

    print("chat_history_formatted",chat_history_formatted)
    formatted_prompt = prompt_template.format(
        chat_history=chat_history_formatted,
        follow_up_question=follow_up_question
    )
    return formatted_prompt









def generate_answer_template(question, docs, chat_history):
    # Prepare the main template structure
    template = Template("""
Use the following passages and chat history to answer the user's question. 
Each passage has a NAME which is the title of the document. After your answer, leave a blank line and then give the source name of the passages you answered from. Put them in a comma separated list, prefixed with SOURCES:.

Example:

Question: What is the meaning of life?
Response:
The meaning of life is 42.

SOURCES: Hitchhiker's Guide to the Galaxy

If you don't know the answer, just say that you don't know, don't try to make up an answer.

----

$passages
----
Chat history:
$chat_history

Question: $question
Response:
    """)
    
    # Format passages
    passages = "\n".join([
        f"---\nNAME: {doc.metadata['make']}  {doc.metadata['model']}  {doc.metadata['trim']}\nPASSAGE:\n{doc.page_content}\n---"
        for doc in docs
    ])
    
    # Format chat history
    chat_lines = []
    for turn in chat_history:
        if turn['type'] == 'human':
            chat_lines.append(f"Question: {turn['content']}")
        elif turn['type'] == 'ai':
            chat_lines.append(f"Response: {turn['content']}")
    formatted_chat_history = "\n".join(chat_lines)
    
    # Substitute values into the template
    filled_template = template.substitute(
        passages=passages,
        chat_history=formatted_chat_history,
        question=question
    )
    
    return filled_template
