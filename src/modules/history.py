import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

import os
import streamlit as st
from streamlit_chat import message
import base64
import re

class ChatHistory:
    
    def __init__(self):
        self.history = st.session_state.get("history", []) # 세션 상태에서 'history' 키의 값을 가져오고, 없으면 빈 리스트로 초기화
        st.session_state["history"] = self.history

        # 상품명 버튼을 위한 idx
        self.b_idx = 0

    def default_greeting(self):
        # 유저의 기본 인사 메시지
        return "안녕! Save Mate! 👋"

    def image_to_base64(self, image_path): 
        # 이미지 파일을 base64로 인코딩하여 HTML에서 표시할 수 있도록 변환
        with open(image_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode("utf-8")
        return encoded_string

    def default_prompt(self, topic):
        # 챗봇의 기본 프롬프트 메시지 생성
        # 유저에게 상세한 가이드라인 제공 위함
            # 일반 채팅 모드 : 사이드 바에 유저아이디 미제공 및 금융상품종류 미입력시 일반 채팅 모드 실행(게스트 모드)
        # 상담시 유의 사항 
        # 서비스 소개 
            # 1. 마이데이터 (유저) 기반 금융상품 추천 기능
            # 2. 상품정보 질의응답 기능
            # 3. 금융 정보 질의응답 기능
        # 질문 에시와 대화 가이드라인 

        image_path = "./src/modules/img_folder/free-icon-golden-retriever-5374233.png"
        #image_path = "./src/modules/img_folder/how_to_chat.png"
        encoded_image = self.image_to_base64(image_path)

        prompt_text =  f"""사이드바에서 유저아이디/금융상품종류를 입력해주세요. 입력하지 않으면 게스트모드/일반채팅모드로 실행이 됩니다.

        정확한 정보를 안내해 드리기 위해 열심히 학습하고 있지만, 가끔은 실수를 할 수도 있습니다. 
        현재 상담 시점에서 충족하시는 조건을 고려해 상품을 안내드리고 있어요. 저와 상담하신 후에 충족되는 조건은 고려할 수 없습니다. 

        <br><br>
        <img src="data:image/png;base64,{encoded_image}" alt="Financial Image" style="width:150px;"><br>
        가이드라인을 참고하세요.<br><br>

        [마이데이터 기반 예금/적금상품 추천 기능]
        1. 유저아이디를 사이드바에서 입력하세요. 
        2. 채팅창에 내 계좌정보 알려줘를 입력해주세요.
        3. 이후, 원하시는 조건 + 상품 추천해줘를 입력해주세요.
        4. 원하시는 조건의 예시로는 군인, 20대, 50대가 있습니다.
        5. 마이데이터에서 계좌잔액, 주거래은행 등의 정보를 반영해서 예금자보호법에 따라 상품을 추천합니다.

        [상품정보 검색 기능]
        1. 채팅창에 원하시는 상품명 + 궁금한 내용을 입력하세요.
        2. 현재 10여개 은행의 50여개의 상품정보가 준비되어 있습니다.
        3. 상품명 예시: 우리 SUPER주거래 정기적금, 급여하나 월복리 적금, 행복knowhow 연금예금, NH장병내일준비적금

        [금융정보 기능]
        1. 궁금하신 금융정보를 채팅창에 자유롭게 물어보세요.
        2. 금융정보 예시: 복리, 예금자보호법, 인플레이션

        
        질문 예시
        당신의 금융 목표와 선호도에 대해 더 자세히 알려주시면 더 정확한 상품 추천을 드릴 수 있습니다. 
        1. 어떤 금융 목표를 달성하고 싶으신가요? (예: 목돈 모으기, 주택 구매, 여행 자금 등) 
        2. 예금 또는 적금에 얼마나 많은 금액을 투자하고 싶으신가요? 
        3. 예금 또는 적금의 기간은 어느 정도로 생각하고 계신가요? (예: 단기, 중기, 장기) 
        4. 우대금리를 받기 위해 어떤 조건을 충족하실 수 있으신가요? (예: 급여 이체, 카드 이용, 마케팅 동의 등)
 
        고객님, 어떤게 궁금하신가요? 🤗 """

        return prompt_text
    
    def extract_product_names(self, response):
        """
        챗봇 응답에서 상품명을 추출하는 함수.
        상품명은 '은행명 + 상품명' 형태나 '상품명: {상품명}' 형태로 되어 있다고 가정하고, 이를 정규 표현식으로 추출.
        """
        # 상품명 추출을 위한 정규 표현식 (은행명 + 상품명 혹은 '상품명: {상품명}' 형태)
        product_pattern = re.compile(r"(은행명\s*:\s*(.*?)\n)?상품명\s*:\s*(.*?)\n")
        matches = product_pattern.findall(response)

        # 추출된 상품명 반환 (은행명이 있으면 결합, 없으면 상품명만)
        product_names = [match[2] if not match[1] else f"{match[1]} {match[2]}" for match in matches]

        return product_names
    
    def process_assistant_response(self, response_text):
        """
        챗봇이 중간에 생성한 응답을 처리하고, 상품명이 포함되어 있으면 버튼을 생성.
        """
        # 상품명을 추출
        product_names = self.extract_product_names(response_text)

        # 어시스턴트 응답 표시
        st.markdown(f"""
        <div style="background-color: #001F3F; padding: 10px; border-radius: 10px; color: white;">
            {response_text}
        </div>
        """, unsafe_allow_html=True)

        # user_message 초기화. 상품 버튼 누를 시에만 값 업데이트
        user_message = None

        if product_names:
            st.write("상품 정보를 클릭해 추가 정보를 확인하세요.")
            for idx, product in enumerate(product_names):
                if st.button(product, key=f"product_button_{idx + self.b_idx}"):  # 고유한 key 값 추가
                    # 버튼 클릭 시, 유저의 메시지를 추가하고 화면에 즉시 반영
                    user_message = f"{product} 상품을 확인하고 싶어"

                    ## 2024-10-13 수정
                    #st.session_state["user"].append(user_message)  # 유저 메시지를 기록에 추가
                    #self.history.append("user", user_message) # 유저 입력을 기록에 추가

                    
                    #st.experimental_rerun()  # 페이지를 새로고침하여 즉시 화면에 반영
            # 질문이 거듭되어도 매번 unique button id가 필요
            self.b_idx += 10

        return user_message


    def initialize_user_history(self):
        st.session_state["user"] = [self.default_greeting()] # 유저의 기본 인사 메시지를 세션 상태에 저장


    def initialize_assistant_history(self, topic):
        # 기본 프롬프트를 세션 상태에 저장
        st.session_state["assistant"] = [self.default_prompt(topic)] 

    def initialize(self, topic):
        if "assistant" not in st.session_state: # 세션 상태에 "assistant" 키가 없으면 초기화
            print('assistant session state')
            self.initialize_assistant_history(topic)
        if "user" not in st.session_state: # 세션 상태에 "user" 키가 없으면 초기화
            print('user session state')
            self.initialize_user_history()

    def reset(self, topic):
        """ 기록 초기화 함수 """
        st.session_state["history"] = [] # 채팅 기록
        
        self.initialize_user_history() # 유저 기록
        self.initialize_assistant_history(topic) # 어시스턴트 기록
        st.session_state["reset_chat"] = False

    def append(self, mode, message):
        # 유저 또는 어시스턴트의 메시지를 세션 상태에 추가
        print('history append method')
        st.session_state[mode].append(message)

    def generate_messages(self, container):       

        # user_message 초기화
        user_message = None

        if st.session_state["assistant"]: # 세션 상태에 "assistant" 기록이 있으면 해당 메시지를 표시
            with container:
                for i in range(len(st.session_state["assistant"])):
                    # 유저의 메시지 표시
                    message(
                        st.session_state["user"][i],
                        is_user=True,
                        key=f"history_{i}_user",
                        avatar_style="big-smile",
                    )
                    # 어시스턴트의 메시지 표시
                    message(st.session_state["assistant"][i], key=str(i), avatar_style="identicon")

                    # 어시스턴트 메시지 (HTML로 이미지와 텍스트 포함)
                    #assistant_message = st.session_state["assistant"][i]
                    #st.markdown(f"""
                    #<div style="background-color: #001F3F; padding: 10px; border-radius: 10px;">
                    #    {assistant_message}
                    #</div>
                    #""", unsafe_allow_html=True)

                    # 어시스턴트의 메시지 표시 및 상품 정보 확인 후 버튼 생성
                    #assistant_message = st.session_state["assistant"][i]
                    #user_message = self.process_assistant_response(assistant_message)
        # return something
        ## 무엇인가를 리턴하여 SaveMate-chat에서의 try 문이 문제없이 돌아가도록 한다
        
            #self.product_simulation()
        #return user_message
    
                    

    def load(self):
        # 파일에 기록된 채팅 기록을 로드 (파일이 존재하는 경우)
        if os.path.exists(self.history_file):
            with open(self.history_file, "r") as f:
                self.history = f.read().splitlines()

    def save(self):
        # 채팅 기록을 파일에 저장
        with open(self.history_file, "w") as f:
            f.write("\n".join(self.history))
