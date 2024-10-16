import os
import pandas as pd
from langchain_upstage import ChatUpstage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.output_parsers import PydanticOutputParser
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from langchain_upstage import UpstageGroundednessCheck
from pydantic import BaseModel, Field 
from string import Template
import yaml  
from typing import Optional



load_dotenv()

class Chatbot:
    """
    통합 금융 챗봇 구현
    사용자의 게좌 정보 조회
    맞춤형 금융 상품 추천 및 이자 계산 
    금융 상식 질의문답 수행
    """
    UPSTAGE_API_KEY = os.getenv('UPSTAGE_API_KEY')

    # 유효한 은행명과 상품명을 정의하여 Hallucination 방지 
    predefined_valid_banks = ["NH농협은행", "하나은행", "우리은행", "KB국민은행", "토스은행", "신한은행", "카카오뱅크", "SBI저축은행", "K뱅크"]
    predefined_valid_products = ["행복 knowhow 연금예금", "트래블로그 여행 적금", "정기예금", "급여하나 월복리 적금", "NH직장인월복리적금", "NH장병내일준비적금", "NH올원e예금", "NH더하고나눔정기예금", "NH내가Green초록세상예금", 
                                 "WON플러스 예금", "WON 적금", "N일 적금(31일)", "우리 SUPER주거래 적금", "우리 첫거래우대 정기예금", "KB 국민 UP 정기예금", "KB 내맘대로적금", "KB 스타적금", "KB 장병내일준비적금", "직장인우대적금", 
                                 "KB Star 정기예금", "토스뱅크 굴비 적금", "토스뱅크 먼저 이자 받는 정기예금", "토스뱅크 자유 적금", "토스뱅크 키워봐요 적금", "Tops CD연동정기예금", "쏠편한 정기예금", "신한 My플러스 정기예금", 
                                 "미래설계 장기플랜 연금예금", "미래설계 크레바스 연금예금", "카카오뱅크 정기예금", "희망정기적금", "적립식예금", "희망정기적금", "회전정기예금", "정기적금", "정기예금", "자유적립예금", "적립식예금", 
                                 "자유적금", "손주사랑정기적금", "거치식예금", "코드K정기예금", "코드K 자유적금", "주거래우대자유적금"]

    # 불용어 목록 추가 (예: '정기')
    ignore_words = ['정기']

    def __init__(self, retriever_예금, retriever_적금, retriever_예금_적금, data=None): 
        """
        Chatbot 클래스의 초기화 함수
        """
        
        # 기본 설정 및 초기화 
        ## 💡 UPSTAGE CHAT MODEL 💡 ##
        self.llm= ChatUpstage(api_key = self.UPSTAGE_API_KEY, temperature= 0.0)
        self.base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.prompts_path = os.path.join(self.base_path, 'src', 'modules', 'prompts')

        # 상품 종류별 리트리버 설정 
        ## 더 정확한 리트리브를 위함 
        self.retriever_예금 = retriever_예금
        self.retriever_적금 = retriever_적금
        self.retriever_예금_적금 = retriever_예금_적금
        self.retriever = None

        # 유효한 은행명과 상품명에서 공백 제거 후 저장
        self.valid_banks = {self.clean_text(b) for b in self.predefined_valid_banks}
        self.valid_products = {self.clean_text(p) for p in self.predefined_valid_products}
        
        
       # 데이터 로드 (mydata_dummy.csv 활용)
        if data is None:
            self.data_path = os.path.join(self.base_path, 'src', 'data', 'mydata_dummy.csv')
        else:
            self.data_path = os.path.join(self.base_path, data)
        
        self.user_data = pd.read_csv(self.data_path)

     # qa_system_prompt 설명
            # 사용자의 상품 및 서비스, 추천 관련 질문 답변 프로픔트
            # 가장 적합한 금융 상품 추천할때의 지침 
            # 역할 정의 : 서비스 / 상품에 대한 질문 답변 & 상품 추천
            # 응답 : 한국어, 친절하고 간결한 bullet points로 답변
            # 특정 상활별 응답 
                # - 예금, 적금은 각 관련 PDF만 참고, 모호한 질문은 두 항목 모두 참조
                # - 금액 미지정 : 해당 상품에 적용 가능한 최대 금액 적용
                # - 특정 상품면 언급 시 : 해당 상품 PDF만 참조 
            # 상품 추천 답변 형식 

        # QA 시스템 프롬프트 초기화 (YAML 파일 로드)
        self.qa_system_template_path = os.path.join(self.prompts_path, 'qa_system.yaml')
        self.qa_system_template = self.load_yaml(self.qa_system_template_path)['template']
        self.qa_system_prompt = Template(self.qa_system_template)
        self.first_message_displayed = False  # Streamlit, 첫 메시지가 한 번만 출력되도록 설정
        
        
        # 이자 계산을 위한 few_shot_example & CoT prompt
        # 각 이자 계산 방식을 명확히 설명:
            # 단리 (Simple Interest)
                # 원금에 대해서만 이자를 계산하는 방식
                # 만기 금액 = 원금 * (1 + 연이자율 * 기간)
                # 예시: 원금 1,000,000원, 연이자율 5%, 기간 2년 -> 만기 금액 1,100,000원
        
            # 월복리 (Monthly Compound Interest)
                # 매달 예치 원금과 이전에 누적된 이자에 대해 매달 다시 이자가 붙는 방식
                # 만기 금액 = sum_{m=1}^{M} 월 예치금 * (1 + 월 이자율)^{M-m}
                # 예시: 매달 200,000원 예치, 연이자율 4.55%, 기간 24개월
        
            # 연복리 (Annual Compound Interest)
                # 원금과 그동안 누적된 이자에 대해 매년 복리로 이자가 붙는 방식
                # 만기 금액 = 원금 * (1 + 연이자율)^기간
                # 예시: 원금 5,000,000원, 연이자율 3.5%, 기간 2년 -> 만기 금액 계산
        
            # 자유적금/적립 (Flexible Savings)
                # 자유롭게 금액과 날짜를 선택해 입금하며, 이에 따른 이자가 매일 붙는 방식
                # 만기 금액 = 입금액 * (1 + (연이자율 / 365) * 일수)
                # 예시: 특정 날짜에 200,000원을 예치하고, 연이자율 4.1%, 만기까지 307일
              
        # 이자 계산을 위한 few-shot 예제 로드
        self.few_shot_template_path = os.path.join(self.prompts_path, 'few_shot_template.yaml')
        self.few_shot_examples = self.load_yaml(self.few_shot_template_path)
        
   
        # Pydantic 파서 설정
        ## Pydantic은 데이터의 구조와 유효성을 검사하는 데 유용
        ## 사용자가 특정 금융 상품을 추천해달라고 할 때, 
        ## 응답에 은행 이름, 이자율, 만기 금액 등 필요한 정보가 빠짐없이 포함되도록 함
        self.parser = PydanticOutputParser(pydantic_object=BankProductDetail)



    def clean_text(self, text):
        """ 
        공백 제거 및 불용어 삭제 
        """
        cleaned_text = ''.join(text.split())  # 모든 공백 제거
        for word in self.ignore_words:
            cleaned_text = cleaned_text.replace(word, '')  # 불용어 제거
        return cleaned_text     

    def get_user_details(self, user_id):
        """
        주어진 user_id에 해당하는 사용자 은행 정보 추출
        맞춤형 추천에 사용 
        """
        user_details = self.user_data[self.user_data['User ID'] == user_id]
        return user_details

    def load_yaml(self, path):
        """ 
        (프롬프트) YAML 파일을 로드  
        """
        try:
            with open(path, 'r', encoding='utf-8') as file:
                return yaml.safe_load(file)
        except FileNotFoundError:
            print(f"Error: {path} 경로에 파일이 없습니다.")
            return {}

    def get_few_shot_prompt_examples(self):
        """ 
        few-shot 예시를 반환 
        """

        print("few_shot_examples 반환")
        examples = self.few_shot_examples.get('examples', [])
        formatted_examples = ""
        for example in examples:
            formatted_examples += f"질문: {example['question']}\n답변: {example['answer']}\n\n"
        return formatted_examples


    def generate_responses(self, question, context, chat_history, user_id=None, product_type=None, max_retries=3):
        """
        사용자가 입력한 질문에 대한 응답 생성 (상품 및 은행명 검증 포함)
        계좌 상태 확인, 상품 추천 여부 및 상품 유형에 따라 이자 계산 방식 처리 방식을 다르게 적용 

        question (str): 사용자 쿼리
        context (str): 관련 PDF 내용 추출
        chat_history (list): 이전 대화 내용
        user_id (str, optional): 사용자의 ID. Defaults to None.
        product_type (str, optional): 금융 상품 종류
        max_retries (int, optional): 응답 생성 실패 시 재시도 횟수. Defaults to 3

        returns: 생성된 응답
        
        """

        # 1. 유효한 은행명과 상품명에서 모든 공백 문자(띄어쓰기, 탭, 줄바꿈 포함) 제거
        valid_banks = {''.join(b.split()) for b in self.predefined_valid_banks}
        valid_products = {''.join(p.split()) for p in self.predefined_valid_products}

        retry_count = 0 # groundedness check 시도 횟수
        gc_result = None # goundedness check result default to None
        
        
        # 2. 계좌 상태 관련 질문 확인 
        is_account_status_query = self.check_account_status_query(question)

        if is_account_status_query:
            if user_id:
                # 사용자 계좌 상태 프롬프트 활용
                response = self.build_account_status_prompt(user_id)
                print("Account Status Response:", response)
                return response
            else:
                return "사용자 ID를 제공해 주세요."

        # 3. 추천 관련 질문 확인 
        is_recommendation = self.check_recommendation(question) 
        
        # 4. 만기 금액 계산 활용을 위한 특정 키워드 추출 및 이자 계산 필요성 확인 
        is_simple_interest, is_compound_interest, is_period_interest = self.check_interest_calculation(context)
        is_interest_calculation = is_simple_interest or is_compound_interest or is_period_interest

        # 5. 금융 상식용 답변 처리 
        if is_recommendation != True and is_interest_calculation != True: 
            full_prompt = self.build_prompt(context, question, user_id, product_type, is_interest_calculation)
            qa_prompt = self.create_qa_prompt(full_prompt, chat_history)
            response = self.get_response_from_chain(qa_prompt, question, context, chat_history)
            return response
        
        # 6. 추천 또는 이자 계산 관련 처리 프로픔트 (재시도 루프 시작)
        while retry_count < max_retries: #groundedness max를 초과하지 않을 경우 

            full_prompt = self.build_prompt(
                     context, 
                     question, 
                     user_id, 
                     product_type, 
                     is_interest_calculation)   
                        
            # QA Prompt 생성 및 응답 받기 
            qa_prompt = self.create_qa_prompt(full_prompt, chat_history)
            response = self.get_response_from_chain(qa_prompt, question, context, chat_history)

            # 응답의 유효성 확인 (은행명과 상품명 포함 여부)
            if not self.is_response_valid(response, valid_banks, valid_products):
                print("Response contains invalid bank or product. Retrying...")
                retry_count += 1
                continue  # 유효하지 않은 경우 재시도

            # 추천과 관련된 질문일 경우 groundedness 확인
            # DB 외 상품 추천 방지 위함
            if is_recommendation:
                gc_result = self.check_groundedness(context=context, response=response)
                print("GC check result: ", gc_result)

                if gc_result == "grounded":
                    # 응답이 근거에 기반한 경우, 응답을 반환
                    print("qa_prompt", qa_prompt) 
                    return response
                
                # 응답이 근거에 기반하지 않은 경우, 재시도
                retry_count += 1
                print(f"Response not grounded. Retrying... ({retry_count}/{max_retries})")
                
                 # 다음 시도를 위해 프롬프트를 수정
                full_prompt += "\nPlease make sure your response is based on the provided context.\n"
                qa_prompt = self.create_qa_prompt(full_prompt, chat_history)
                response = self.get_response_from_chain(qa_prompt, question, context, chat_history)

            else: # 추천 질문이 아닌 경우, 즉시 응답을 반환
                print("qa_prompt", qa_prompt)
                return response

       # 7. 최대 재시도 횟수 도달 시 기본 메시지 반환
        print("qa_prompt", qa_prompt)  
        return response if gc_result == "grounded" else "아직까지 적절한 상품을 찾지 못했어요. 조금만 질문을 구체화해주실 수 있나요?"
    
    def build_prompt(self, context, question, user_id, product_type, is_interest_calculation=False):
        """
        사용자의 질문과 상황별 프롬프트를 생성

        사용자 ID, 이자 계산 여부 등 다양한 조건을 반영하여 프롬프트를 동적으로 생성
        맞춤형 추천을 위해 사용자의 은행 잔액 정보 및 예금자 보호 한도를 고려하고
        이자 계산 시에는 few shot 프롬프트를 이용하여 추가하여 모델 답변 생성에 도움
        """

        print(product_type, "selected")    

        if user_id is None:
             # 사용자 ID가 제공되지 않은 경우, 기본 프롬프트를 사용
             full_prompt = self.qa_system_prompt.safe_substitute(
             format=self.parser.get_format_instructions(),
             context=''
         )  
            
        else:
            print("user_id:", user_id)
            # 사용자 ID가 제공된 경우 해당 사용자의 계좌 정보를 가져옴
            user_details = self.get_user_details(user_id) 
            user_bank_balances = user_details[['Bank Name', 'Balance']]

            print("user_bank_balances:", user_bank_balances)

            # 사용자의 잔액 한도를 확인하여 은행 리스트를 필터링
            # 예금자 보호 적용 확인용
            user_bank_balances = user_bank_balances.groupby('Bank Name')['Balance'].sum().reset_index()
            banks_with_high_balance = user_bank_balances[user_bank_balances['Balance'] >= 50000000]['Bank Name'].tolist()
                
            print("do_not_bank", banks_with_high_balance) # 예금자 보호 한도 초과 은행 출력

            # 사용자가 현재 이용 중인 은행을 우선적으로 추천 
            # 맞춤형 추천용
            prioritized_banks = user_bank_balances['Bank Name'].tolist()

            # 사용자 은행 잔액 정보를 문자열로 변환
            user_bank_balances_str = user_bank_balances.to_dict(orient='records')
            user_bank_balances_str = str(user_bank_balances_str).replace("{", "{{").replace("}", "}}")

            # 전체 프롬프트 생성
            full_prompt = self.qa_system_prompt.safe_substitute(
                                    format=self.parser.get_format_instructions(),
                                    context=context
                                )  
            full_prompt += f"\nUser's Banks and Balance is {user_bank_balances_str}\n"

            # 상품 추천과 관련된 규칙 설정
            full_prompt += "\nRules:\n"

            # 규칙 1: 예금자 보호 한도 초과 시 경고 메시지 출력 및 대안 상품 제시
            full_prompt += (
                f"- If the recommended product is from a bank where the user's balance exceeds 49,999,999, "
                f"or from any of the following banks: {banks_with_high_balance},\n"
                f"  **Inform** the user with: "
                f"'예금자 보호법에 따라 {banks_with_high_balance} 은행 외의 상품을 추천드립니다.'\n"
                f"  Provide an alternative product from another bank, if applicable.\n"
            )

            # 규칙 2: 객관적인 비교를 통해 단 하나의 최적 상품 추천
            full_prompt += (
                f"- **Compare all available products objectively** and choose **one best fitting product** "
                f"based on interest rates, bonuses, or other key features.\n"
                f"Try to recommend only **one** product."
            )

            # 규칙 3: 사용자가 이미 이용 중인 은행 상품을 우선적으로 추천
            full_prompt += (
                f"- If a product from one of the user's banks ({prioritized_banks}) is a good fit, "
                f"recommend it. If not, explain why another bank's product is a better choice, but still recommend **one** product.\n"
            )
            # 규칙 4: 항상 추천 이유를 명확하게 설명
            full_prompt += (
                "- Provide an **objective and persuasive explanation** when suggesting a product, especially if it's not from the user's bank.\n"
            )

            # 규칙 5: 필수 정보가 누락된 경우 경고 메시지 제공
            full_prompt += (
                "- If any required information is missing, say: "
                "'해당 정보가 제공된 문서에 포함되어 있지 않습니다. 추가 정보가 필요합니다.'\n"
            )

            # 문서의 컨텍스트 추가

            full_prompt += f"\nContext:\n{context}"

       # 이자 계산이 필요한 경우 few-shot 예제 추가
        if is_interest_calculation:
            print("is_interest_calculation TRUE : 이자 계산 필요")
            full_prompt += "\nPlease provide a step-by-step reasoning for calculating the interest based on the identified type (단리, 복리, 기간별 이자, 자유 적금). Apply the appropriate formula and provide the maturity amount.\n"
            
            # few-shot 예제를 프롬프트에 추가하여 사용자의 이해를 돕도록 구성
            full_prompt += self.get_few_shot_prompt_examples()
        
        #print(full_prompt)
        return full_prompt + f"\n질문: {question} 특히 {product_type}을 선호해\n응답:"

    def check_recommendation(self, question):
        """ 
        추천 관련 질문 확인 
        """
        recommendation_keywords = ["추천", "recommend", "추천해", "추천해줘", "추천해 주세요", "추천 해줘"]
        return any(keyword in question for keyword in recommendation_keywords)
    
    def check_interest_calculation(self, context):
        """ 
        만기 금액 계산 활용을 위한 키워드 추출
        """
        simple_interest_keywords = ["단리"]
        compound_interest_keywords = ["복리", "연복리", "월복리"]
        period_interest_keywords = ["가입기간별 기본이자율"]
        
        # 각 이자 계산 유형에 해당하는 키워드가 포함되어 있는지 확인
        is_simple_interest = any(keyword in context for keyword in simple_interest_keywords)
        is_compound_interest = any(keyword in context for keyword in compound_interest_keywords)
        is_period_interest = any(keyword in context for keyword in period_interest_keywords)

        return is_simple_interest, is_compound_interest, is_period_interest

    def create_qa_prompt(self, full_prompt, chat_history):
        """
        QA 프롬프트 생성
        """

        return ChatPromptTemplate.from_messages([
            ("system", full_prompt),
            MessagesPlaceholder("chat_history"), # 대화 기록이 추가될 공간을 예약
            ("human", "{input}")
        ])
    
    def get_response_from_chain(self, qa_prompt, question, context, chat_history, is_recommendation=False):
        """  
        주어진 프롬프트를 사용하여 챗봇의 응답을 생성
        추천 질문인 경우 Pydantic 파서를 사용하여 응답을 구조화,
        일반 텍스트 응답인 경우 StrOutputParser를 사용
        """
        
        # 추천 질문 여부에 따라 적절한 파서 선택
        if is_recommendation:
            # 추천 관련 질문의 경우 Pydantic 파서를 사용
            chain = qa_prompt | self.llm | self.Parser # Pydantic 파서 사용
        else:
            chain = qa_prompt | self.llm | StrOutputParser() # 일반 텍스트 파서 사용

        # 프롬프트와 질문을 기반으로 응답 생성
        response = chain.invoke({
            "input": question,
            "Context": context,
            "chat_history": chat_history
        })

        # 추천 질문의 경우 응답을 파싱하여 반환
        if is_recommendation:
            try:
                parsed_response = self.parser.parse(response)
                print(f"Bank Name: {parsed_response.bank_name}")  # 파싱된 은행명 출력
                return parsed_response
            except Exception as e:
                print(f"Parsing Error: {str(e)}")
                print(f"Invalid JSON Output: {response}")
                return "추천 정보 처리에 오류가 발생했습니다. 다시 시도해 주세요."
        else:
            # 일반 텍스트 응답인 경우
            return response

                    
    def retrieve_documents(self, query, product_type='적용안함', top_k=1):            
        """
        사용자가 입력한 쿼리를 기반으로 관련 문서 검색

        금융상품 종류(예금, 적금 등)에 맞는 리트리버(retriever)를 설정
        사용자의 질문에 가장 적합한 문서를 검색하고 내용 추출
        """

        print(f"Query: {query}")

        # 1. 상품 종류에 따라 리트리버 설정
        self.set_retriever_by_product_type(product_type)

        # 2. 리트리버가 설정되었는지 확인 (디버깅용)
        if self.retriever:
            print(f"Using retriever for product type: {product_type}")
        else:
            print(f"Retriever for {product_type} is not set. Check the configuration.")
            return None

        print(f"Query: {query} | Product Type: {product_type}")


        try:
            # 3. 사용자의 쿼리를 기반으로 문서 검색 수행
            search_result = self.retriever.invoke(query, top_k=top_k)

            # 4. 검색 결과가 없는 경우 처리
            if not search_result:
                print(f"No documents retrieved for the query '{query}' with product type '{product_type}'.")
                return None
            else:
                print(f"Number of documents retrieved: {len(search_result)}")

            # 5. 검색된 각 문서의 내용을 추출
            extracted_texts = []
            for search in search_result:
                soup = BeautifulSoup(search.page_content, "html.parser") # HTML 파싱
                text = soup.get_text(separator="\n") # 문서 텍스트 추출
                extracted_texts.append(text)

            # 6. 추출된 텍스트를 하나의 문자열로 합치기
            context = "\n".join(extracted_texts)
            print(f"Context extracted for product type '{product_type}':\n{context[:500]}...")  # 첫 500글자만 출력
            return context
        
        except Exception as e:
            # 7. 예외 발생 시 오류 메시지 출력 및 None 반환
            print(f"Error while retrieving documents: {str(e)}")
            return None
    
    def check_groundedness(self, context, response):
        """ 
        응답의 근거성(groundedness) 검사 

        응답이 주어진 문맥(context)과 일치하는지를 확인,
        챗봇의 응답이 근거 없는 내용(hallucination)을 포함하지 않도록 유도
        """
        groundedness_check = UpstageGroundednessCheck() ## 💡 UPSTAGE MODEL 💡##
        gc_result = groundedness_check.invoke({"context": context, "answer": response})
        return gc_result
 
    def check_account_status_query(self, question):
        """ 
        사용자가 계좌 상태 관련 질문 여부 확인
        """
        account_keywords = ["내 계좌", "계좌 상태", "계좌 잔액", "잔액 알려줘", "내 계좌상태 알려줘", "계좌 현황", "계좌정보", "계좌 정보"]
        return any(keyword in question for keyword in account_keywords)

    def build_account_status_prompt(self, user_id):
        """
        사용자 계좌 상태를 요약하는 프롬프트를 생성
        """
        # 사용자 계좌 정보 가져오기
        user_details = self.get_user_details(user_id)
        user_bank_balances = user_details[['Bank Name', 'Balance']]

        print("user_bank_balances:", user_bank_balances)

        # 예금자 보호 한도 초과 은행 필터링
        user_bank_balances = user_bank_balances.groupby('Bank Name')['Balance'].sum().reset_index()
        banks_with_high_balance = user_bank_balances[user_bank_balances['Balance'] >= 50000000]['Bank Name'].tolist()

        print("do_not_bank", banks_with_high_balance)

        # 은행 및 잔액 문자열 생성
        bank_balance_str = "\n".join(
            "%s : %s원" % (row['Bank Name'], format(row['Balance'], ','))
            for _, row in user_bank_balances.iterrows()
        )

        # 사용자가 이용 중인 은행 리스트 생성
        prioritized_banks = user_bank_balances['Bank Name'].tolist()

        # 최종 프롬프트 구성 
        account_status_prompt = """
        다음은 사용자의 계좌 상태입니다:

        **은행 및 잔액:**
        %s

        - 잔액이 50,000,000원 이상인 은행: %s
        - 현재 이용 중인 은행: %s

        **주의:** 예금자 보호 한도를 초과한 은행에 주의하세요.
        """ % (bank_balance_str, banks_with_high_balance, prioritized_banks)

        return account_status_prompt


    def is_response_valid(self, response, valid_banks, valid_products):
        """
        응답에 포함된 은행명과 상품명이 유효성 검증
        """
        print(f"Validating response")

        #응답내의 은행명, 상품명 검증
        for line in response.splitlines():
            if "은행명" in line:
                bank = (line.split(":")[1].strip())
                print(f"Bank found in response: {bank}")

                # 비교를 위한 clean_text를 사용하여 처리
                bank_revised = self.clean_text(bank)  # 은행명 별도 변수로 처리
                if bank_revised not in valid_banks:
                    print(f"Invalid bank found: {bank_revised}")
                    return False
                    
            if "상품명" in line:
                product = line.split(":")[1].strip()
                print(f"Product found in response: {product}")
                
                # 비교를 위한 clean_text를 사용하여 처리
                product_revised = self.clean_text(product)
                if product_revised not in valid_products:
                    print(f"Invalid product found: {product_revised}")
                    return False
        return True
    
    def set_retriever_by_product_type(self, product_type):
            """ 
            금융 상품 종류에 맞는 리트리버를 설정
            """
            if product_type == '예금':
                self.retriever = self.retriever_예금
            elif product_type == '적금':
                self.retriever = self.retriever_적금
            else:
                self.retriever = self.retriever_예금_적금  # 예금 & 적금 혹은 기타


class BankProductDetail(BaseModel):
    """ 
    PydanticOutParser 활용하여 필요한 정부 추출
    """
    bank_name: str = Field(description="은행명")
    product_name: str = Field(description="상품명")
    subscription_period: Optional[int] = Field(None, description="가입 기간 (개월)")
    amount: Optional[int] = Field(None, description="가입 금액 (원)")
    base_interest_rate: Optional[float] = Field(None, description="기본 금리 (%)")
    bonus_interest_rate: Optional[float] = Field(None, description="우대 금리 (%)")
    amount_with_base_interest: Optional[int] = Field(None, description="기본 금리 만기 금액 (원)")
    amount_with_bonus_interest: Optional[int] = Field(None, description="우대 금리 만기 금액 (원)")
    requirements_1: str = Field("우대 금리, 이자율을 적용받기 위해 필요한 우대 조건 1")
    requirements_2: str = Field("우대 금리, 이자율을 적용받기 위해 필요한 우대 조건 2")
    requirements_3: str = Field("우대 금리, 이자율을 적용받기 위해 필요한 우대 조건 3")
