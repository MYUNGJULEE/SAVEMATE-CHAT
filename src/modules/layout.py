import streamlit as st

class Layout:

    def show_api_key_missing(self):
        """
        Displays a message if the user has not entered an API key
        """
        st.markdown(
            """
            <div style='text-align: center;'>
                <h4> System Error : Set up your API key in the .env file to start chatting</h4>
            </div>
            """,
            unsafe_allow_html=True,
        )
    
    def show_header(self, product_names):
        """
        앱의 헤더를 표시하는 메서드
        """
        st.markdown(
            f"""
            <h1 style='text-align: center; color: lightblue;'> Save Mate에게 {product_names} 추천받으세요! 😁</h1>
            """,
            unsafe_allow_html=True,
        )


    def prompt_form(self):
        """
         프롬프트 폼을 표시하는 메서드
        """
        with st.form(key="my_form", clear_on_submit=True):
            # 텍스트 영역 생성: 유저가 질문을 입력할 수 있는 영역을 생성
            user_input = st.text_area(
                "Query:",
                placeholder="자유롭게 질문하세요",
                key="input",
                label_visibility="collapsed",
            )
            # 사용자 입력 제출 버튼 생성
            submit_button = st.form_submit_button(label="Send")

            # 제출 버튼이 눌렸는지와 유저의 입력 내용을 출력
            print("submit_button:",submit_button)
            print('user_input:',user_input)
            
            # 버튼이 눌렸는지를 `is_ready` 변수에 저장
            is_ready = submit_button 

        return is_ready, user_input
    
