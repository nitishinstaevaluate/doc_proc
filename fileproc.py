#pip install openai==0.28 #to install compatible version
import shutil
from app_config import *
import os
import json 
import re
from json_repair import repair_json
from azure.storage.blob import BlobServiceClient, ContentSettings
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
import openai
from azure.ai.inference import ChatCompletionsClient
from PyPDF2 import PdfReader, PdfWriter
from pathlib import Path
import pandas as pd
from openpyxl import load_workbook
import pandas as pd
import warnings

# Suppress specific warnings from openpyxl
warnings.filterwarnings("ignore", category=UserWarning, message="Print area cannot be set to Defined name: None")

#---------------------
def log(msg):
    if(debug): print(msg)

def get_extn(file_path):
    return Path(file_path).suffix.lower()[1:]

#---------------------Analyze via Form Recognizer (Local & Blob)
def analyze_document_from_file(file_path):
    extn = get_extn(file_path)
    if(not extn in extn_valid):
            raise Exception(f"Not a valid file {file_path}")

    if(extn in extn_valid_pdf):
        return analyze_document_from_pdf(file_path)
    elif(extn in extn_valid_xls):
        return analyze_document_from_xls(file_path)

def analyze_document_from_pdf(file_path):
    #log(f"Document analysis with pdf")
    client = DocumentAnalysisClient( endpoint=FORM_RECOGNIZER_ENDPOINT,
        credential=AzureKeyCredential(FORM_RECOGNIZER_KEY))
    
    with open(file_path, "rb") as f:
        poller = client.begin_analyze_document(model_id="prebuilt-layout", document=f)
        result = poller.result()

    text_content = ""
    for page in result.pages:
        for line in page.lines:
            text_content += line.content + "\n"

    return text_content

def analyze_document_from_xls(file_path):
    return analyze_document_from_xls_pd(file_path)    

def analyze_document_from_xls_pd(file_path):
    #log(f"Document analysis with pandas")
    try:
        excel_file = pd.ExcelFile(file_path)
        output_text = ""
        for sheet_name in excel_file.sheet_names:
            df = pd.read_excel(file_path, sheet_name=sheet_name, dtype=str)
            output_text += f"\nSheet: {sheet_name}\n"
            for row_idx, row in df.iterrows():
                for col_idx, value in enumerate(row):
                    header = df.columns[col_idx]
                    val = str(value).strip() if pd.notna(value) else ""
                    if val and val.lower() != "nan":
                        #output_text += f"{header}: {val}\n"
                        output_text += f"{val}\n"
        return output_text
    except Exception as e:
        log(f"Error reading Excel file: {e}")
        return ""

#---------------------Prompt OpenAI for Financial + Balance Sheet Extraction
def map_financial_data_with_openai(json, content):
    #log(f"Mapping Data to JSON")
    return map_json(json, content)

def estimate_tokens(text: str) -> int:
    return len(text) // 3

def map_json(json: str, content: str) -> str:
    base_prompt = f"""{base_prompt_json_prefix}
        {json}
        {base_prompt_json1}
        Attached Financial document Content contains data extracted from excel file:
        """
    return call_openai(base_prompt, content)

def call_openai(base_prompt: str, content: str, sys_prompt: str = None):
    if(not sys_prompt):
        sys_prompt = "You are a financial document parser."
    content_tokens = estimate_tokens(base_prompt+content)
    
    if content_tokens <= MAX_TOKENS:
        prompt = f"""{base_prompt}
        {content}"""

        json_msg=[
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": prompt}
        ]
        return call_openai_api(json_msg)
    
    log(f"Total content tokens: {content_tokens}, splitting into chunks...")
    chunks = []
    current_chunk = ""
    lines = content.split('\n')
    
    prompt_template = base_prompt
    reserved_tokens = estimate_tokens(prompt_template)
    available_tokens = MAX_TOKENS - reserved_tokens
    
    for line in lines:
        line_tokens = estimate_tokens(line)
        current_chunk_tokens = estimate_tokens(current_chunk)
        
        if current_chunk_tokens + line_tokens > available_tokens:
            if current_chunk:
                chunks.append(current_chunk)
            current_chunk = line
        else:
            current_chunk += line + '\n'
    
    if current_chunk:
        chunks.append(current_chunk)
    
    log(f"Split content into {len(chunks)} chunks")
    
    all_results = []
    for i, chunk in enumerate(chunks):
        chunk_tokens = estimate_tokens(chunk)
        log(f"Processing chunk {i+1}/{len(chunks)} with {chunk_tokens} tokens...")
        prompt = f"""{base_prompt}
        {chunk}"""

        json_msg=[
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": prompt}
        ]
        chunk_result = call_openai_api(json_msg)
        all_results.append(chunk_result)
    
    return "\n".join(all_results)

def call_openai_api(json_msg) -> str:
    openai.api_type = "azure"
    openai.api_base = OPENAI_ENDPOINT
    openai.api_version = OPENAI_API_VER
    openai.api_key = OPENAI_API_KEY

    client = ChatCompletionsClient(
        endpoint=OPENAI_ENDPOINT,
        credential=AzureKeyCredential(OPENAI_API_KEY)
    )

    payload = {
    "messages": json_msg,
    "temperature": 1,
    "top_p": 1,
    "stop": []
    }
    response = client.complete(payload)
    str_response = response['choices'][0]['message']['content']
    return str_response

   
def split_pdf(input_pdf, output_dir, max_pages=5):
    reader = PdfReader(input_pdf)
    total_pages = len(reader.pages)
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    for start in range(0, total_pages, max_pages):
        writer = PdfWriter()
        for page in range(start, min(start + max_pages, total_pages)):
            writer.add_page(reader.pages[page])
        
        out_path = os.path.join(output_dir, f"split_{start//max_pages + 1}.pdf")
        with open(out_path, "wb") as f_out:
            writer.write(f_out)
    
    return [os.path.join(output_dir, f) for f in os.listdir(output_dir) if f.endswith(".pdf")]

def analyze_file(file_path):
    full_text = ""
    extn = get_extn(file_path)
    
    if(os.path.isdir(file_path) and os.listdir(file_path)):
        files = os.listdir(file_path)
        for file in files:
            if(os.path.isdir(file_path+"/"+file)):
                continue
            full_text += "\n"+analyze_file(file_path+"/"+file) 
    elif(is_too_large(file_path) and extn in extn_valid_pdf): 
        output_dir = LOCAL_PATH_TMP+Path(file_path).name
        if(extn in extn_valid_pdf):
            split_files = split_pdf(file_path, output_dir, max_pages=3)
        log("Splitting and collecting file...")
        full_text = analyze_file(output_dir) 
    else:
        full_text = analyze_document_from_file(file_path)
    return full_text

def has_valid_excel_signature(file_path):
    with open(file_path, "rb") as f:
        signature = f.read(4)
    return signature == b'PK\x03\x04'

def is_too_large(file_path, limit_mb=4):
    return os.path.getsize(file_path) > (limit_mb * 1024 * 1024)

def extract_file_contents(in_file, out_file):
    extracted_text = ""
    if not out_file == None and os.path.exists(out_file):
        log(f"Extract read from file {out_file}")
        with open(out_file) as ifile:
            extracted_text=ifile.read()
    else:
        log(f"Processing file Using file upload: {in_file}")
        extracted_text = analyze_file(in_file)

        if(extracted_text==None):
            extracted_text=""
        if(not out_file==None):
            write_to_file(out_file, extracted_text)
            log("Extract saved to file "+out_file)
    #delete tmp folder
    shutil.rmtree(LOCAL_PATH_TMP+Path(in_file).name, ignore_errors=True)
    return extracted_text

def extract_particulars(obj):
    results = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "particulars":
                v = re.sub(r"^\([^)]+\)\s*", "", v)
                if(len(v) > 1):
                    results.append(v)
            else:
                results.extend(extract_particulars(v))
    elif isinstance(obj, list):
        for item in obj:
            results.extend(extract_particulars(item))
    return results

def json_extract(json_file):
    with open(json_file, 'r') as f:
        data = json.load(f)

    particulars_list = extract_particulars(data)
    #iterate through the list and generate a simple json object
    final_json="{"
    for i in range(len(particulars_list)):
        if(i != len(particulars_list)-1):
            final_json += f"\"{particulars_list[i]}\":\"\","
        else:
            final_json += (f"\"{particulars_list[i]}\":\"\""+"}")
    return final_json

def merge_jsons(strjson1, strjson2):
    json1 = json.loads(strjson1)
    json2 = json.loads(strjson2)

    merged_json = {**json1, **json2}
    return json.dumps(merged_json, indent=4)

def list_json(json_path:str):
    json_files = []
    if(os.path.isdir(json_path) and os.listdir(json_path)):
        for file in os.listdir(json_path):
            if file.endswith(".json"):
                json_files.append(os.path.join(json_path, file))
    else:
        json_files.append(json_path)

    return json_files

def list_json_extract(json_path:str):
    json_files = list_json(json_path)
    json1 = "{}"
    for filename in json_files:
        if filename.lower().endswith(".json"):
            json2=json_extract(filename)
            json1 = merge_jsons(json1, json2)
    return json1

json_tmpl=""

def get_json_tmpl():
    global json_tmpl
    if(not json_tmpl):
        json_path=LOCAL_PATH_JSON
        json = list_json_extract(json_path)
        print(f"Using JSON Mapping {LOCAL_PATH_JSON}")
        #write_to_file(LOCAL_PATH_OUT+"JSON.txt", json)
        json_tmpl = json
    return json_tmpl

def write_to_fileb(out_file_path: str, str_data: bytes):
    with open(out_file_path, "wb") as file:
        file.write(str_data)

def write_to_file(out_file_path: str, str_data: str, append: bool = False):
    mode = "a" if append else "w"
    with open(out_file_path, mode) as file:
        file.write(str_data)

def extract_data_map(in_file_path: str, out_dir: str, purge_ext_file=False) -> str:
    file_name = Path(in_file_path).name 
    ext_file = out_dir+file_name+"_ext.txt"
    map_file = out_dir+file_name+"_map.txt"
    if(purge_ext_file == True): ext_file=None
    
    extracted_text = extract_file_contents(in_file_path, ext_file)
    json_tmpl = get_json_tmpl()
    mapresult = map_financial_data_with_openai(json_tmpl, extracted_text)
    if "```json" in mapresult:  
        mapresult = mapresult.split("```json", 1)[1]
        if "```" in mapresult:  
            mapresult = mapresult.split("```", 1)[0]
    #mapresult=repair_json(mapresult)
    write_to_file(map_file, mapresult)
    return map_file

