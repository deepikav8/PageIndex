import os
from pageindex import PageIndexClient
import pageindex.utils as utils
from dotenv import load_dotenv

load_dotenv()

PAGEINDEX_API_KEY = os.getenv("PAGEINDEX_API_KEY2")

pi_client = PageIndexClient(api_key=PAGEINDEX_API_KEY)

def submit_pdf(pdf_path: str) -> str:
    return pi_client.submit_document(pdf_path)["doc_id"]

def is_ready(doc_id: str) -> bool:
    return pi_client.is_retrieval_ready(doc_id)

def get_tree(doc_id: str):
    return pi_client.get_tree(doc_id, node_summary=True)["result"]

def clean_tree(tree):
    return utils.remove_fields(tree, ["text"])

def create_node_map(tree):
    return utils.create_node_mapping(tree)
