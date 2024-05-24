import os
from langchain_core.messages import HumanMessage
from langchain_openai import AzureChatOpenAI
from servicenow import configure_servicenow
from langchain_core.prompts import PromptTemplate


from dotenv import load_dotenv
load_dotenv()


model = AzureChatOpenAI(
    openai_api_version=os.environ["AZURE_OPENAI_API_VERSION"],
    azure_deployment=os.environ["AZURE_OPENAI_CHAT_DEPLOYMENT_NAME"],
)



def openAIFunction(name: str):

    template = """You are an AI assistant designed to classify user queries. Your task is to determine whether a given query is a normal conversation or a ServiceDesk conversation. 
    A normal conversation includes everyday, casual, or non-service-related topics. Examples include discussing hobbies, plans, general inquiries, and personal matters.
    A ServiceDesk conversation involves requests for assistance, support issues, troubleshooting, or inquiries related to IT services, technical support, or customer service.
    For each query, respond with either "Conversation" if it is a normal conversation or "ServiceDesk" if it is a ServiceDesk conversation.
    Examples:
    Query: "How was your weekend?"
    Classification: Conversation
    
    Query: "I'm having trouble logging into my email."
    Classification: ServiceDesk
    
    Query: "What's your favorite movie?"
    Classification: Conversation
    
    Query: "Can you help me reset my password?"
    Classification: ServiceDesk
    
    Query: {query}
    Classification: 
    """
    prompt_template = PromptTemplate(template=template, input_variables=["query"])
    chain = prompt_template | model
    response = chain.invoke({"query": name})

    if(response.content == 'ServiceDesk'):
        return ServiceDesk_Function(question=name)
    else:
        return Conversational_Function(question=name)


def Conversational_Function(question):
    message = HumanMessage(
        content=question
    )
    answer=model.invoke([message])
    response = {"content": answer.content, "response_detail": "general_ai_response"}
    return response


def ServiceDesk_Function(question):
    similar_catalog_items = configure_servicenow.get_similar_catalog_item(question)
    return similar_catalog_items
