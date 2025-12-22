from src.embedding.embedding import titan_embed_v1 
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
import os 

embedding = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2" , model_kwargs={"device": "cpu"})


class VectorStoreManager:
    def __init__(self, base_dir="/app/faiss"):
        self.embeddings = embedding
        self.base_dir = base_dir
        os.makedirs(base_dir, exist_ok=True)

    def save(self, docs, file_id, thread_id):
        for d in docs:
            d.metadata["file_id"] = file_id
            d.metadata["thread_id"] = thread_id

        db = FAISS.from_documents(docs, self.embeddings)
        path = f"{self.base_dir}/{thread_id}"
        db.save_local(path)
        



