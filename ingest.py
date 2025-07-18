
import os
import chromadb
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader
from llama_index.vector_stores.chromadb import ChromaDB

def ingest_documents():
    """
    Ingests documents from the 'data' directory into a ChromaDB vector store.
    """
    data_dir = "data"
    db_dir = "chroma_db"

    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        print(f"Created '{data_dir}' directory. Please add your documents here and run the script again.")
        return

    # initialize client, setting path to where Chroma is stored
    db = chromadb.PersistentClient(path=db_dir)

    # create collection
    chroma_collection = db.get_or_create_collection("esi_collection")

    # load documents
    documents = SimpleDirectoryReader(data_dir).load_data()

    # set up the vector store
    vector_store = ChromaDB(chroma_collection=chroma_collection)

    # create the index
    index = VectorStoreIndex.from_documents(
        documents, vector_store=vector_store
    )

    print(f"Successfully ingested {len(documents)} documents into ChromaDB.")

if __name__ == "__main__":
    ingest_documents()
