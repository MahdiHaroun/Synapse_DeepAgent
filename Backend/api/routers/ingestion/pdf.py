from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

class PdfProcessor:
    def __init__(self):
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50,
            separators=["\n\n", "\n", " ", ""]
        )

    def load_and_chunk(self, path: str) -> list[Document]:
        loader = PyPDFLoader(path)
        pages = loader.load()

        docs = []
        for i, page in enumerate(pages):
            text = self._clean(page.page_content)
            if len(text) < 50:
                continue

            docs.extend(
                self.splitter.create_documents(
                    [text],
                    metadatas=[{
                        "page": i + 1,
                        "source": path
                    }]
                )
            )
        return docs

    def _clean(self, text: str) -> str:
        text = " ".join(text.split())
        text = text.replace("ﬁ", "fi").replace("ﬂ", "fl")
        return text




