# ------------------ CONFIG ------------------
debug=True
RESET = False
MAP_JSON = True
MAX_TOKENS = 80000

MAX_FILE_SIZE = 2 * 1024 * 1024  # 2MB limit for file size


# --------------------------------------------
extn_valid_xls = ['xlsx']
extn_valid_pdf = ['pdf']
extn_valid = extn_valid_pdf+extn_valid_xls

# File path to local PDF or Excel
BASE_PATH="/home/azureuser/doc_proc/"
LOCAL_PATH = BASE_PATH+"samples/"
LOCAL_PATH_JSON = BASE_PATH+"json/"
LOCAL_PATH_INP = LOCAL_PATH+"din/" #Directory for input
LOCAL_PATH_EXT = LOCAL_PATH+"ext/"
LOCAL_PATH_OUT = LOCAL_PATH+"out/"
LOCAL_PATH_TMP = LOCAL_PATH+"tmp/"
LOCAL_PATH_TMPL = LOCAL_PATH+"tmpl/"
XL_TEMPLATE=BASE_PATH+"template-v2.xlsx"

# Azure Blob Storage
BLOB_CONN_STR = "<your-blob-connection-string>"
BLOB_CONTAINER_NAME = "uploads"

#Azure API Details
PAVIN_COGN_API_URL="https://pavindocintai.cognitiveservices.azure.com/"
PAVIN_COGN_API_KEY1=""

# Azure OpenAI
PAVIN_OPENAI_API_URL="https://pavingptai.openai.azure.com/openai/deployments/gpt-4o"
PAVIN_OPENAI_API_KEY1=""

# Azure Document Intelligence & OpenAI
FORM_RECOGNIZER_ENDPOINT = PAVIN_COGN_API_URL #"https://<your-fr-resource>.cognitiveservices.azure.com/"
FORM_RECOGNIZER_KEY = PAVIN_COGN_API_KEY1 #"<your-form-recognizer-key>"

OPENAI_ENDPOINT = PAVIN_OPENAI_API_URL
OPENAI_API_KEY = PAVIN_OPENAI_API_KEY1
OPENAI_DEPLOYMENT = "gpt-4o " #"gpt-35-turbo"
OPENAI_API_VER = "2024-10-21"

std_format_json="\"Expenses\": {\n\"Cost of Sales\": {\n\"24-25\": 402.91,\n\"25-26\": 443.25,\n\"26-27\": 473.93\n}.... "
base_prompt_json_prefix = f"""You are a financial document analyst. 
From the Content of financial document attached, 
extract and map all the possible fields with values mentioned in json below"""
base_prompt_json1 = f"""
If found multiple values such as yearly projections, put them in corresponding array with heading.
Provide the output in a clean structured format using content below.

If there is any mention of units like "INR in Lakhs", "Rs in Lakhs", or "INR in Crores", convert the numerical values accordingly:
- "INR in Lakhs": multiply value by 100000
- "INR in Crores": multiply value by 10000000

For example, 24.13 Lakhs → 2413000, and 3.5 Crores → 35000000.

Also, remove any formatting like commas in the values.
Dont provide any suggestions, key notes, explainations.

Keep the output format matching to below format
{std_format_json}
"""
# --------------------------------------------
