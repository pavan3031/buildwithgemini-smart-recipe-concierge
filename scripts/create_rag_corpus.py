import vertexai
from vertexai.preview import rag
from vertexai.preview.rag.utils import resources as rr

PROJECT_ID = "qwiklabs-gcp-02-16632a3e3848"
LOCATION = "us-central1"  # Serverless RAG is supported in us-central1
GCS_PATH = "gs://smart-recipe-assets-qwiklabs-gcp-02-16632a3e3848/rag/pg49513.txt"

PARSING_PROMPT = (
    "Extract the individual useful facts, remedies, and herbal recipes described in this text. "
    "Ignore and omit all metadata, Project Gutenberg legal boilerplate, and index numbers. "
    "Output clean, self-contained prose."
)

def create_and_index_corpus():
    vertexai.init(project=PROJECT_ID, location=LOCATION)

    print("Step 1: Setting RAG managed DB to serverless mode...")
    cfg = f"projects/{PROJECT_ID}/locations/{LOCATION}/ragEngineConfig"
    try:
        rag.update_rag_engine_config(
            rag_engine_config=rag.RagEngineConfig(
                name=cfg,
                rag_managed_db_config=rag.RagManagedDbConfig(mode=rr.Serverless()),
            )
        )
        print("Serverless mode configured successfully.")
    except Exception as e:
        print(f"Warning during update_rag_engine_config: {e}")

    print("\nStep 2: Creating serverless RAG corpus...")
    corpus = rag.create_corpus(
        display_name="herbal-medical-guide-corpus",
        embedding_model_config=rag.EmbeddingModelConfig(
            publisher_model="publishers/google/models/text-embedding-005"
        ),
    )
    print(f"✅ RAG Corpus created! Name: {corpus.name}")

    print("\nStep 3: Importing, chunking, and indexing document from GCS...")
    resp = rag.import_files(
        corpus_name=corpus.name,
        paths=[GCS_PATH],
        transformation_config=rag.TransformationConfig(
            chunking_config=rag.ChunkingConfig(chunk_size=512, chunk_overlap=100)
        ),
        llm_parser=rag.LlmParserConfig(
            model_name="gemini-1.5-flash-002",
            custom_parsing_prompt=PARSING_PROMPT,
        ),
    )
    print(f"✅ Import complete! Imported {resp.imported_rag_files_count} file(s).")
    print(f"\nUSE THIS CORPUS NAME IN AGENT CODE:\n{corpus.name}")

if __name__ == "__main__":
    create_and_index_corpus()
