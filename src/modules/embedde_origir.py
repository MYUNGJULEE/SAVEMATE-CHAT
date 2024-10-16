import os
import tempfile
from langchain_upstage import UpstageEmbeddings
from langchain_community.document_loaders import PyPDFLoader, CSVLoader, TextLoader
from langchain_community.vectorstores import Chroma
from langchain.text_splitter import RecursiveCharacterTextSplitter
from dotenv import load_dotenv
import getpass

class Embedder:

    def __init__(self, input_folder="pdf_folder", output_folder="embeddings"):
        
        # 현재 파일의 경로를 기준으로 상대 경로 설정
        base_path = os.path.dirname(os.path.abspath(__file__))
        self.input_folder = os.path.join(base_path, input_folder)
        self.PATH = os.path.join(base_path, output_folder)

        # 환경 변수 파일 로드
        ## .env 파일의 UPSTAGE_API_KEY 반환 위함
        load_dotenv()
        
        UPSTAGE_API_KEY = os.getenv("UPSTAGE_API_KEY")
        
        # 디버깅용 API 키 출력 (필요 시 사용)
        # print(f"Using Upstage API Key: {UPSTAGE_API_KEY}")
        
         # API 키가 없을 경우 오류 발생
        if UPSTAGE_API_KEY is None:
            raise ValueError("UPSTAGE_API_KEY environment variable not found.")
        
        ## 💡 UPSTAGE CHAT MODEL 💡 ##
        # UpstageEmbeddings에 API 키 전달 
        self.embeddings = UpstageEmbeddings(model="solar-embedding-1-large", 
                                                upstage_api_key=UPSTAGE_API_KEY)

    def create_embeddings_dir(self):
        """ Chroma DB 파일을 저장할 디렉토리 생성 함수 """
        # 경로에 디렉토리 없을 시 새로 생성
        if not os.path.exists(self.PATH):
            os.makedirs(self.PATH)

    def store_doc_embeds(self, file, original_filename):
        """ Solar Pro와 Chroma DB를 사용하여 문서 임베딩 저장 함수 """
        # 임시 파일 생성
        with tempfile.NamedTemporaryFile(mode="wb", delete=False) as tmp_file:
            tmp_file.write(file)
            tmp_file_path = tmp_file.name

        
        def get_file_extension(uploaded_file):
            """ 파일 확장자 확인 함수 """
            return os.path.splitext(uploaded_file)[1].lower()
        
        # 텍스트를 일정 크기로 나누는 TextSplitter 설정
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=2000,
            chunk_overlap=100,
            length_function=len,
        )

        # 파일 확장자 가져오기
        file_extension = get_file_extension(original_filename)

        # 파일 확장자에 따라 해당 파일 로더 선택
        # 기업에서의 다양한 파일 형식 지원용 (csv, pdf, txt 파일 수용가능)
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

        # 로드된 데이터의 내용 출력 (처음 3개의 청크 200글자 확인용으로 출력)
        print(f"Loaded data for {original_filename}:")
        for doc in data[:3]:  
            print(doc.page_content[:200])  

        # 임시 파일 삭제 
        os.remove(tmp_file_path)

        # Chroma DB를 사용하여 임베딩 저장
        vector_store = Chroma.from_documents(
            documents=data,
            ids=[doc.page_content for doc in data],
            embedding=self.embeddings,
            persist_directory=self.PATH  
        )
        vector_store.persist()


    def store_embeddings_from_folder(self):
        """ 입력 폴더에 있는 모든 PDF 파일에 대한 임베딩 저장 함수 """
        for filename in os.listdir(self.input_folder):
            file_path = os.path.join(self.input_folder, filename)

            # 파일이 PDF인지 확인 (필요에 따라 다른 파일 형식 추가 가능)
            if filename.lower().endswith(".pdf"):
                with open(file_path, "rb") as file:
                    file_content = file.read()
                    self.store_doc_embeds(file_content, filename)

    def get_retriever(self):
        """ 문서 임베딩을 기반으로 하는 리트리버 반환 함수 """
        vector_store = Chroma(
            persist_directory= self.PATH,
            embedding_function= self.get_embedding_function()
        )      
        # 벡터 스토어를 리트리버로 변환
        retriever = vector_store.as_retriever()
        print('retriever:,',retriever)
        return retriever

    def get_embedding_function(self):
        return self.embeddings

    def list_embeddings(self):
        """ 디버깅을 위한 모든 저장된 임베딩 목록 출력 """
        print("Listing stored embeddings:")
        for root, dirs, files in os.walk(self.PATH):
            for file in files:
                print(f"File: {file}, Path: {os.path.join(root, file)}")


# 해당 파일이 직접 실행될 때만 사용되는 코드
## 디렉토리 이동 후 python3 embedder.py
if __name__ == "__main__":
    # 입력 폴더 및 출력 폴더 정의
    base_path = os.path.dirname(os.path.abspath(__file__))
    input_folder = os.path.join(base_path, "pdf_folder")
    output_folder = os.path.join(base_path, "embeddings")

    # Embedder 인스턴스 생성
    embedder = Embedder(input_folder=input_folder, output_folder=output_folder)

    # 입력 폴더의 모든 PDF 파일에 대한 임베딩 저장
    embedder.store_embeddings_from_folder()

    # 저장된 모든 임베딩을 확인하기 위해 출력
    embedder.list_embeddings()
