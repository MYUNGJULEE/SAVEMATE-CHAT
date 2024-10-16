import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

import os
import pandas as pd
import streamlit as st
import pdfplumber

#from langchain_community.vectorstores import Chroma
from modules.chatbot import Chatbot
from modules.embedder import Embedder

from dotenv import load_dotenv

class Utilities:

    @staticmethod
    def load_api_key():
        # 환경 변수 파일 로드
        ## .env 파일의 UPSTAGE_API_KEY 반환 위함

        if not hasattr(st.session_state, "api_key"):
            st.session_state.api_key = None
            print('os.path:', os.path)
        
        # key 가져오기
        load_dotenv()
        user_api_key = os.getenv("UPSTAGE_API_KEY")
        return user_api_key

    
    # 이거 안쓰지 않나? 안쓰면 삭제하도록 2024-10-13
    #@staticmethod
    #def handle_upload(file_types):
    #    """
    #    업로드된 파일을 처리하고 화면에 표시하는 함수
    #    file_types: 수용 가능한 파일 유형 리스트 (예: ["csv", "pdf", "txt"])
    #    # 추후 기업에서 활용시 제안 코드
    #    """

    #    print("handle_upload")

    #    uploaded_file = st.sidebar.file_uploader("upload", type=file_types, label_visibility="collapsed")
    #    if uploaded_file is not None:

    #        def show_csv_file(uploaded_file):
    #            file_container = st.expander("Your CSV file :")
    #            uploaded_file.seek(0)
    #            shows = pd.read_csv(uploaded_file)
    #            file_container.write(shows)

    #        def show_pdf_file(uploaded_file):
    #            file_container = st.expander("Your PDF file :")
    #            with pdfplumber.open(uploaded_file) as pdf:
    #                pdf_text = ""
    #                for page in pdf.pages:
    #                    pdf_text += page.extract_text() + "\n\n"
    #            file_container.write(pdf_text)
            
    #        def show_txt_file(uploaded_file):
    #            file_container = st.expander("Your TXT file:")
    #            uploaded_file.seek(0)
    #            content = uploaded_file.read().decode("utf-8")
    #            file_container.write(content)
            
    #        def get_file_extension(uploaded_file):
    #            return os.path.splitext(uploaded_file)[1].lower()
            
    #        file_extension = get_file_extension(uploaded_file.name)

            # Show the contents of the file based on its extension
    #        if file_extension == ".csv" :
    #            show_csv_file(uploaded_file)
    #        if file_extension== ".pdf" : 
    #            show_pdf_file(uploaded_file)
    #        elif file_extension== ".txt" : 
    #            show_txt_file(uploaded_file)

    #    else:
    #        st.session_state["reset_chat"] = True

    #    print(uploaded_file.name)
        
    #    return uploaded_file

    @staticmethod
    def setup_chatbot():
        """
        업로드된 파일을 기반으로 챗봇을 설정하는 함수
        """
        embeds = Embedder()
        
        # 각 금융상품에 맞는 리트리버 생성
        retriever_예금 = embeds.get_retriever('예금')
        retriever_적금 = embeds.get_retriever('적금')
        retriever_예금_적금 = embeds.get_retriever('예금 & 적금')
        
        print('Go to Chatbot __init__')

        # 금융상품별 리트리버를 전달하여 Chatbot 인스턴스 생성
        chatbot = Chatbot(retriever_예금, retriever_적금, retriever_예금_적금)
        
        # 챗봇이 준비되었다는 세션 상태 표시
        st.session_state["ready"] = True

        print("st.session_state['ready'] : ", st.session_state['ready'])

        return chatbot
