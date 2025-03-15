import os
from dotenv import load_dotenv
from azure.ai.inference import ChatCompletionsClient
from azure.ai.inference.models import SystemMessage, UserMessage
from azure.core.credentials import AzureKeyCredential

# 加载.env文件中的环境变量
load_dotenv()

# 从环境变量中获取配置
endpoint = os.getenv("AZURE_ENDPOINT")
model_name = os.getenv("AZURE_MODEL_NAME")
api_key = os.getenv("AZURE_API_KEY")

client = ChatCompletionsClient(
    endpoint=endpoint,
    credential=AzureKeyCredential(api_key),
)

response = client.complete(
    messages=[
        SystemMessage(content="You are a helpful assistant."),
        UserMessage(content="I am going to Paris, what should I see?")
    ],
    max_tokens=2048,
    model=model_name
)

print(response.choices[0].message.content)