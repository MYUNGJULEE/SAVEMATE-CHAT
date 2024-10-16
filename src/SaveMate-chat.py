import os
import streamlit as st
from modules.history import ChatHistory
from modules.layout import Layout
from modules.utils import Utilities
from modules.sidebar import Sidebar

from langchain_core.messages import HumanMessage, AIMessage

# 로컬에서 모듈 업데이트 시 바로 반영되도록 리로드 기능 정의 (r 키를 눌러 새로 고침)
def reload_module(module_name):
    import importlib
    import sys
    if module_name in sys.modules:
        importlib.reload(sys.modules[module_name])
    return sys.modules[module_name]

# 필요한 모듈을 리로드하고 새로 가져옴
history_module = reload_module('modules.history')
layout_module = reload_module('modules.layout')
utils_module = reload_module('modules.utils')
sidebar_module = reload_module('modules.sidebar')

# 리로드한 모듈에서 클래스 불러오기
ChatHistory = history_module.ChatHistory
Layout = layout_module.Layout
Utilities = utils_module.Utilities
Sidebar = sidebar_module.Sidebar

# Streamlit 페이지 설정: 레이아웃은 'wide', 페이지 아이콘과 제목 설정
st.set_page_config(layout="wide", page_icon="💬", page_title="금융상품 추천해주는 | Save Mate")

layout, sidebar, utils = Layout(), Sidebar(), Utilities() # 메인 컴포넌트 인스턴스 생성
layout.show_header("금융상품을") # 페이지 헤더를 표시


Sidebar.get_user_id() # 진행 전 사이드바에서 유저 ID를 가져옴

Sidebar.get_product_type() # 진행 전 사이드바에서 유저 ID를 가져옴

user_api_key = utils.load_api_key()

# 초기화 전에 user_message를 session_state에 저장
if "user_message" not in st.session_state:
    st.session_state["user_message"] = None

if not user_api_key:
    layout.show_api_key_missing()
else:
    os.environ["UPSTAGE_API_KEY"] = user_api_key

    # 종료 등 할 때 사용하기
    chat_flag = True
    user_message = st.session_state["user_message"]

    if chat_flag:

        # 사이드바 구성 설정
        sidebar.show_options()
        

        # 채팅 기록 초기화
        history = ChatHistory()
        try:

            # 매번 챗봇 초기화하는 것은 비효율적임
            if "chatbot" not in st.session_state:
                print('try to set up chatbot')

                chatbot = utils.setup_chatbot() # 챗봇 초기화 및 설정
                st.session_state["chatbot"] = chatbot # 세션 상태에 챗봇 저장
            else:
                chatbot = st.session_state["chatbot"]

            if st.session_state["ready"]:
                # 채팅 응답 및 사용자 입력을 표시할 컨테이너 생성
                response_container, prompt_container = st.container(), st.container()

                print("1")

                with prompt_container:

                    # 프롬프트 폼 표시: 사용자 입력 및 제출 버튼 생성
                    is_ready, user_input = layout.prompt_form()
                    history.initialize("topic")

                    # 채팅 리셋 버튼이 눌리면 기록을 초기화
                    if st.session_state["reset_chat"]:
                        history.reset("topic")
                        print('Reset')

                    print('it is ready;', is_ready)


                    # 제출 버튼이 눌리고 입력이 준비된 경우
                    if is_ready == True:
                
                        print('if is_ready')

                        # 채팅 기록 업데이트 및 메시지 표시
                        user_id = st.session_state.get("user_id", None)
                        print(f"Debug: user_id from session state: {user_id}")
                        if not user_id: # 유저 아이디가 없다면 
                             st.warning("No User ID provided. Continuing in Guest Mode.")
                        
                        history.append("user", user_input) # 유저 입력을 기록에 추가

                        # 금융상품 종류 가져오기
                        product_type = st.session_state.get("product_type", '적용안함')
                        print(f"Debug: product_type from session state: {product_type}")
                        if product_type == '적용안함' : # 상품 적용 안했다면
                             st.warning("금융상품 종류가 입력되지 않았습니다. 기본 채팅모드로 진행합니다")

                        print('before output')
                        
                        question = user_input # 챗봇을 통한 사용자 질문 및 응답 생성
                        query = f"{question.lower()}"

                        # 사용자 질문을 기반으로 문서 검색
                        context = st.session_state["chatbot"].retrieve_documents(query)

                        # 이전 채팅 기록 가져오기
                        chat_history = st.session_state.get("history", [])

                        # 챗봇이 응답을 생성 (질문, 문맥, 이전 대화 기록, 유저 ID, 금융상품 타입 사용)
                        output = st.session_state["chatbot"].generate_responses(question, context, st.session_state["history"], user_id=user_id, product_type=product_type) 

                        # 질문과 답변 저장
                        st.session_state["history"] += [HumanMessage(query), AIMessage(output)]
                        print('after output')

                        # 어시스턴트 응답을 채팅 기록에 추가
                        history.append("assistant", output)

                        # 여기에서 생성된 버튼의 클릭을 처리 
                        ### 상품 정보를 간단하게 처리하고 싶음
                        if st.session_state.get("product_button_click"):
                            # 사용자가 상품 버튼을 클릭한 경우, 자동으로 메시지 추가
                            print("상품 정보 확인 버튼")
                            history.append("user", st.session_state["product_button_click"])
                            st.session_state["product_button_click"] = None  # 상태를 초기화

                # 생성된 메시지를 화면에 표시
                #user_message = history.generate_messages(response_container)
                history.generate_messages(response_container)

                #if user_message: # None이 아닌 경우에만 실행
                #    print("user_message:", user_message)
                #    # history.append("user", user_message) # 유저 입력을 기록에 추가
                #    st.session_state["user_message"] = user_message

        except Exception as e:
            # 예외가 발생할 경우 에러 메시지 표시
            st.error(f"Error: {str(e)}")
