import requests
import os
from langchain.docstore.document import Document
from langchain_openai import AzureOpenAIEmbeddings, AzureChatOpenAI 
from langchain_chroma import Chroma
from langchain.schema import HumanMessage
import json


from dotenv import load_dotenv
load_dotenv()


user = 'pankajj@hexaware.com'
pwd = 'Pankaj@123'
headers = {"Content-Type":"application/json","Accept":"application/json"}

embedding_function = AzureOpenAIEmbeddings(model="Text-embedding")

model = AzureChatOpenAI(
    openai_api_version=os.environ["AZURE_OPENAI_API_VERSION"],
    azure_deployment=os.environ["AZURE_OPENAI_CHAT_DEPLOYMENT_NAME"],
)



def get_catalog_item():
    url = 'https://hexawaretechnologiesincdemo8.service-now.com/api/now/table/sc_cat_item?sysparm_query=active%3Dtrue&sysparm_limit=500'
    response = requests.get(url, auth=(user, pwd), headers=headers )
    if response.status_code != 200: 
        data = {'result':{'sys_id': "", 'sys_name': "",'short_description':"",'description':""}, 'Status': response.status_code, 'Headers': response.headers, 'Error Response':response.json()}
    data = response.json()
    return data


def get_catalog_item_variables(sys_id):
    url = f'https://hexawaretechnologiesincdemo8.service-now.com/api/sn_sc/servicecatalog/items/{sys_id}/variables'
    response = requests.get(url, auth=(user, pwd), headers=headers )
    if response.status_code != 200: 
        print('Status:', response.status_code, 'Headers:', response.headers, 'Error Response:',response.json())
    data = response.json()
    return data


def add_to_cat_item(final_result, sys_id):
    url = 'https://hexawaretechnologiesincdemo8.service-now.com/api/sn_sc/servicecatalog/items/'+sys_id+'/add_to_cart'
    response = requests.post(url, auth=(user, pwd), headers=headers ,data=str(final_result))
    if response.status_code != 200: 
        print('Status:', response.status_code, 'Headers:', response.headers, 'Error Response:',response.json())
    data = response.json()
    return data

def submit_order(cart_id):
    url = 'https://hexawaretechnologiesincdemo8.service-now.com/api/sn_sc/servicecatalog/cart/submit_order?cart_id='+cart_id
    response = requests.post(url, auth=(user, pwd), headers=headers )
    if response.status_code != 200: 
        print('Status:', response.status_code, 'Headers:', response.headers, 'Error Response:',response.json())
    data = response.json()
    return data


def loadJSONFile(data):
    docs=[]
    for catalog_item in data['result']:
        metadata = {"sys_id":catalog_item['sys_id'], "sys_name":catalog_item['sys_name']}
        content = catalog_item['sys_name'] \
            +", "+catalog_item['short_description'] \
            +", "+catalog_item['description']
        docs.append(Document(page_content=content, metadata=metadata))
    return docs 



def get_similar_catalog_item(query):
    response = {}
    
    main_docs = loadJSONFile(data=get_catalog_item())
    db = Chroma.from_documents(main_docs, embedding_function)
    answer = db.similarity_search_with_relevance_scores(query, k=4)
    # print(answer)
    detailedList = []
    response = {}
    for document in answer:
        similarity_score = document[1]
        if(similarity_score > 0.2):
            value = document[0]
            answerlist = {}
            answerlist['content'] = value.page_content
            answerlist['sys_id'] = value.metadata['sys_id']
            answerlist['sys_name'] = value.metadata['sys_name']
            detailedList.append(answerlist)
    response = {'result': detailedList, 'response_detail':'similar_catalog_items'}
    return response

#[{'content':'sysname+shortdescription_description', 'sys_id'='234567890', 'sys_name'='name of the catalog item'}]


def function_calling_catVar(catalog_variables):
    custom_functions = [
    {
        'name': 'extract_catalog_variables',
        'description': 'Get the user query from the body of the input text',
        'parameters': {
            'type': 'object',
            'properties': {}
        }
    }
    ]
    for variable_info in catalog_variables['result']:
        inner_json = {}
        inner_json['type'] = 'string'
        inner_json['description'] = "If "+variable_info['name']+" not mentioned in user query then give the default value as "+"'"+variable_info["displayvalue"]+"'"
        custom_functions[0]['parameters']['properties'][variable_info['name']] = inner_json
    return custom_functions


def mandatory_var_not_added(catalog_variables, json_info):
    mandatory_variable_not_added = []
    for variable_info in catalog_variables["result"]:
        if not json_info.get(variable_info['name'], ""):
            if(variable_info["mandatory"] == True):
                print(variable_info['name'])
                #if(variable_info["read_only"] == False):
                mandatory_variable_not_added.append(variable_info['name'])
    return mandatory_variable_not_added
                

def get_additional_var_fromUser(mandatory_variable_not_added):
    pass


def get_variable_from_query(user_query, sys_id):
    catalog_variables = get_catalog_item_variables(sys_id=(sys_id.strip()))
    #print(catalog_variables)
    custom_function = function_calling_catVar(catalog_variables=catalog_variables)
    message = model.predict_messages(
        [HumanMessage(content=user_query)],
        functions = custom_function
    )
    print(type(message))
    print(message)
    print(json.dumps(message.__dict__))

    if hasattr(message, 'additional_kwargs'):
        print("The 'additional_kwargs' attribute exists.")
    
    parse_variable_details = json.loads(message.additional_kwargs["function_call"]["arguments"])

    mandatory_variable_not_added = mandatory_var_not_added(catalog_variables, parse_variable_details)
    response = {"existing_variables": parse_variable_details, "missing_variables": mandatory_variable_not_added}
    return response    

    # final_result = get_additional_var_fromUser(mandatory_variable_not_added)
    # return final_result


    

