import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

import os
import tempfile
from langchain_upstage import UpstageEmbeddings
from langchain_community.document_loaders import PyPDFLoader, CSVLoader, TextLoader
from langchain_community.vectorstores import Chroma
from langchain.text_splitter import RecursiveCharacterTextSplitter
from dotenv import load_dotenv

class Embedder:

    def __init__(self, input_folder="pdf_folder", output_folder_base="embeddings"):
        
        # 현재 파일의 경로를 기준으로 상대 경로 설정
        base_path = os.path.dirname(os.path.abspath(__file__))
        self.input_folder = os.path.join(base_path, input_folder)
        self.output_folder_base = os.path.join(base_path, output_folder_base)

        # 환경 변수 파일 로드
        load_dotenv()
        UPSTAGE_API_KEY = os.getenv("UPSTAGE_API_KEY")
        
        if UPSTAGE_API_KEY is None:
            raise ValueError("UPSTAGE_API_KEY environment variable not found.")
        
        # UpstageEmbeddings에 API 키 전달 
        self.embeddings = UpstageEmbeddings(model="solar-embedding-1-large", 
                                            upstage_api_key=UPSTAGE_API_KEY)

    def get_embedding_function(self):
        """ UpstageEmbeddings 객체를 반환하는 함수 """
        return self.embeddings

    def create_embeddings_dir(self, product_type):
        """ Chroma DB 파일을 저장할 디렉토리 생성 함수 """
        path = os.path.join(self.output_folder_base, product_type)
        if not os.path.exists(path):
            os.makedirs(path)
        return path

    def store_doc_embeds(self, file, original_filename, selected_type):
        """ Solar Pro와 Chroma DB를 사용하여 문서 임베딩 저장 함수 """
        with tempfile.NamedTemporaryFile(mode="wb", delete=False) as tmp_file:
            tmp_file.write(file)
            tmp_file_path = tmp_file.name
        
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=2000,
            chunk_overlap=100,
            length_function=len,
        )

        file_extension = os.path.splitext(original_filename)[1].lower()

        if file_extension == ".csv":
            loader = CSVLoader(file_path=tmp_file_path, encoding="utf-8", csv_args={'delimiter': ','})
            data = loader.load()
        elif file_extension == ".pdf":
            loader = PyPDFLoader(file_path=tmp_file_path)
            data = loader.load_and_split(text_splitter)
        elif file_extension == ".txt":
            loader = TextLoader(file_path=tmp_file_path, encoding="utf-8")
            data = loader.load_and_split(text_splitter)
        else:
            raise ValueError(f"Unsupported file extension: {file_extension}")

        print(f"Loaded data for {original_filename} ({selected_type}): {len(data)} chunks loaded.")

        os.remove(tmp_file_path)

        # 선택한 상품 타입에 맞는 임베딩 저장
        persist_path = self.create_embeddings_dir(selected_type)
        
        vector_store = Chroma.from_documents(
            documents=data,
            ids=[doc.page_content for doc in data],
            embedding=self.get_embedding_function(),
            persist_directory=persist_path  # 저장할 경로를 타입별로 분리
        )
        vector_store.persist()

    def store_embeddings_from_folder(self, product_type):
        # 이미 존재하는 임베딩이 있으면 생성하지 않도록 설정
        #persist_path = self.create_embeddings_dir(product_type)
        #if os.listdir(persist_path):  # 해당 디렉토리가 비어 있지 않으면
        #    print(f"Embeddings already exist for {product_type}. Skipping embedding generation.")
        #    return

        """ 입력 폴더에 있는 모든 PDF 파일에 대한 임베딩 저장 함수 """
        product_folders = []

        # 예금 & 적금의 경우, 두 개의 폴더를 합쳐서 처리
        if product_type == '예금 & 적금':
            product_folders.append(os.path.join(self.input_folder, '예금'))
            product_folders.append(os.path.join(self.input_folder, '적금'))
        else:
            product_folders.append(os.path.join(self.input_folder, product_type))

        # 선택된 폴더에서 파일을 읽고 임베딩 생성
        for folder in product_folders:
            if not os.path.exists(folder):
                print(f"Folder {folder} does not exist.")
                continue

            for filename in os.listdir(folder):
                file_path = os.path.join(folder, filename)

                if filename.lower().endswith(".pdf"):
                    with open(file_path, "rb") as file:
                        file_content = file.read()
                        self.store_doc_embeds(file_content, filename, product_type)

    def get_retriever(self, product_type= '예금 & 적금'):
        """ 문서 임베딩을 기반으로 하는 리트리버 반환 함수 """
        persist_path = os.path.join(self.output_folder_base, product_type)
        vector_store = Chroma(
            persist_directory=persist_path,
            embedding_function=self.get_embedding_function()  # 임베딩 함수 사용
        )      
        retriever = vector_store.as_retriever()
        print(f"Retriever for {product_type}: {retriever}")
        return retriever

    def list_embeddings(self, product_type):
        """ 디버깅을 위한 모든 저장된 임베딩 목록 출력 """
        persist_path = os.path.join(self.output_folder_base, product_type)
        print(f"Listing stored embeddings in {persist_path}:")
        for root, dirs, files in os.walk(persist_path):
            for file in files:
                print(f"File: {file}, Path: {os.path.join(root, file)}")


# 해당 파일이 직접 실행될 때만 사용되는 코드
if __name__ == "__main__":
    # 입력 폴더 및 출력 폴더 정의
    base_path = os.path.dirname(os.path.abspath(__file__))
    input_folder = os.path.join(base_path, "pdf_folder")
    output_folder = os.path.join(base_path, "embeddings")

    # Embedder 인스턴스 생성
    embedder = Embedder(input_folder=input_folder, output_folder_base=output_folder)

    # 입력 폴더의 모든 PDF 파일에 대한 임베딩 저장
    embedder.store_embeddings_from_folder('예금')  # 예금 폴더에 대해 임베딩 생성
    embedder.store_embeddings_from_folder('적금')  # 적금 폴더에 대해 임베딩 생성
    embedder.store_embeddings_from_folder('예금 & 적금')  # 예금 & 적금 폴더 모두에서 임베딩 생성

    # 저장된 모든 임베딩을 확인하기 위해 출력
    embedder.list_embeddings('예금')
    embedder.list_embeddings('적금')
    embedder.list_embeddings('예금 & 적금')
