import os
import pandas as pd
#import streamlit as st
from langchain_upstage import ChatUpstage
#from langchain_core.prompts import PromptTemplate
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
#from langchain_community.vectorstores import Chroma
#from langchain_upstage import UpstageEmbeddings
from langchain_core.output_parsers import StrOutputParser
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from langchain_upstage import UpstageGroundednessCheck

load_dotenv()

class Chatbot:
    #load_dotenv()
    UPSTAGE_API_KEY = os.getenv('UPSTAGE_API_KEY')

    # 유효한 은행명과 상품명을 클래스 변수로 정의
    predefined_valid_banks = ["신한은행", "KB국민은행", "NH농협은행", "하나은행", "우리은행"]
    predefined_valid_products = ["신한 My플러스 정기예금", "KB국민ONE 정기예금", "NH농협 정기적금"]


    #10.14 수정
    def __init__(self, retriever_예금, retriever_적금, retriever_예금_적금, data=None): 
        """Chatbot 클래스의 초기화 함수"""
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        # 리트리버를 금융상품별로 받음
        self.retriever_예금 = retriever_예금
        self.retriever_적금 = retriever_적금
        self.retriever_예금_적금 = retriever_예금_적금
        
        # 사용자가 선택한 금융상품 종류에 따라 리트리버 선택
        self.retriever = None
        
        # data 폴더에 있는 mydata_dummy.csv 활용
        if data is None:
            self.data_path = os.path.join(base_path, 'src', 'data', 'mydata_dummy.csv')
        else:
            self.data_path = os.path.join(base_path, data)
        self.user_data = pd.read_csv(self.data_path)
        self.llm = ChatUpstage(api_key=self.UPSTAGE_API_KEY) ## 💡 UPSTAGE CHAT MODEL ##

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

        #10.14 추가: only in the context. (자꾸 없는 상품 가상으로 만들어서 넣음)
        self.qa_system_prompt = """

        You are a bank chatbot, where you answer questions about products & services.
        You will also recommend the best products for the user. 

        You will only generate answers based on the following context.

        Your answers should be in Korean.
        You are kind and nice, and if you are not sure of the question, ask the user to rephrase the question.
        Your answers should be refined into bullet points. 

        When a user asks about "예금" (deposit accounts), only refer to PDFs related to 예금 (deposit accounts).
        When a user asks about "적금" (installment savings), only refer to PDFs related to 적금 (installment savings).
        If the question is general or unclear, refer to both types of PDFs to provide the most relevant information.

        If the user does not have a specific amount per month, apply the maximum available appliable for the product. 
        Additionally, if a user mentions a specific product name, you must only refer to the PDF containing information about that product.


        ** When recommending a single or multiple product **, use the bullet-point format below:
            - 은행명 : (bank name)
            - 상품명: (product name)
            - 희망 가입 기간: (desired subscription period)
            - 가입 금액 : (amount per month)
            - 상품 기본 금리: (base interest rate)
            - 우대 금리: (bonus interest rate)
            - 상품 최대 금리: (maximum interest rate)
            - 기본 금리 만기 금액: (amount at maturity with base interest rate)
            - 우대 금리 만기 금액: (amount at maturity with maximum bonus interest rate)
            
            - 우대 조건 (1) : bonus interest rate requirements
            - 우대 조건 (2) : bonus interest rate requirements
            - 우대 조건 (3) : bonus interest rate requirements
        
        ---
        Context: {context}
        """
        
        self.first_message_displayed = False  # Streamlit, 첫 메시지가 한 번만 출력되도록 설정




#10.14추가
    def is_response_valid(self, response, valid_banks, valid_products):
        """
        응답에 포함된 은행명과 상품명이 유효한지 검증하는 함수
        """
        #디버그
        print(f"Validating response:\n{response}\nAgainst valid banks: {valid_banks}\nAnd valid products: {valid_products}")

        for line in response.splitlines():
            if "은행명" in line:
                bank = line.split(":")[1].strip()
                print(f"Bank found in response: {bank}")
                if bank not in valid_banks:
                    print(f"Invalid bank found: {bank}")
                    return False
            if "상품명" in line:
                product = line.split(":")[1].strip()
                # 모든 공백 제거 (띄어쓰기, 탭, 줄바꿈 포함)
                product_cleaned = ''.join(product.split())
                valid_products_cleaned = {''.join(p.split()) for p in valid_products}

                print(f"Product found in response: {product}")
                if product not in valid_products:
                    print(f"Invalid product found: {product}")
                    return False
        return True




    def get_user_details(self, user_id):
        """
        주어진 user_id에 해당하는 사용자 은행 정보 추출 함수
        개인 맞춤형 추천을 하기 위함 
        """
        user_details = self.user_data[self.user_data['User ID'] == user_id]
        return user_details

    # 2024-10-13
    ## generate_responses -> 6개 매서드로 나눠서 호출
    ## 1. check_recommendation : 특정 키워드(추천)가 포함되어 있는지 확인
    ## 2. check_interest_calculation : 이자 계산에 활용하기 위해 특정 키워드를 추출
    ## 3. get_few_shot_prompt_examples : 3에서 호출해서 사용함. 특정 경우에 full_prompt에 few_shot을 추가하기 위해 사용
    ## 4. build_prompt : 사용자 정보를 바탕으로 챗봇이 응답을 생성하기 위한 프롬프트를 구성 (user_id 기반 정보, question, context, product_type 사용
    ## 5. create_qa_prompt : 챗봇에게 구조화된 prompt 제공하기 위해 qa_prompt를 생성
    ## 6. get_response_from_chain : 질문을 위한 chain 생성 (qa_prompt 활용)
    def generate_responses(self, question, context, chat_history, user_id=None, product_type=None, max_retries=3):
        """
        사용자가 입력한 질문에 대한 응답 생성 함수(상품 및 은행명 검증 포함)
        가장 적합한 금융 상품을 추천, 이자 계산에 대한 단계별 설명을 제공 프롬프트 포함

        question (str): 사용자 쿼리
        context (str): 관련 PDF 내용 추출
        chat_history (list): 이전 대화 내용
        user_id (str, optional): 사용자의 ID. Defaults to None.
        max_retries (int, optional): 응답 생성 실패 시 재시도 횟수. Defaults to 3

        returns: 생성된 응답
        
        """
        # 문서에서 추출된 정보를 결합하여 유효한 은행명과 상품명을 반환하지 않고, 미리 제공된 값을 사용
        #valid_banks = set(self.predefined_valid_banks)
        #valid_products = set(self.predefined_valid_products)
        # 유효한 은행명과 상품명에서 모든 공백 문자(띄어쓰기, 탭, 줄바꿈 포함) 제거
        valid_banks = {''.join(b.split()) for b in self.predefined_valid_banks}
        valid_products = {''.join(p.split()) for p in self.predefined_valid_products}



        retry_count = 0 # groundedness check 시도 횟수
        gc_result = None # goundedness check result default to None
        
        # 추천 질문 및 이자 계산을 식별하기 위한 키워드 정의
        #recommendation_keywords = ["추천", "recommend", "추천해", "추천해줘", "추천해 주세요", "추천 해줘"]
        #simple_interest_keywords = ["단리"]
        #compound_interest_keywords = ["복리", "연복리", "월복리"]
        #period_interest_keywords = ["가입기간별 기본이자율"]
        # 수정
        

        # 질문에 추천 관련 키워드가 포함 확인
        is_recommendation = self.check_recommendation(question) #any(keyword in question for keyword in recommendation_keywords)
        
        # 컨텍스트에서 유효한 은행명과 상품명 추출
        #valid_banks, valid_products = self.extract_valid_info_from_context(context)
        
        # 1. 문서에서 추출된 정보를 결합하여 유효한 은행명과 상품명을 반환
     #   try:
     #       # valid_banks와 valid_products를 추출
     #       valid_banks, valid_products = self.extract_valid_banks_and_products(
     #           context, self.predefined_valid_banks, self.predefined_valid_products
     #       )
     #   except Exception as e:
     #       print(f"Error extracting valid banks and products: {str(e)}")
     #       valid_banks, valid_products = set(), set()  # 기본값으로 빈 집합 사용



        # 이자 계산 유형 확인
        #is_simple_interest = any(keyword in context for keyword in simple_interest_keywords)
        #is_compound_interest = any(keyword in context for keyword in compound_interest_keywords)
        #is_period_interest = any(keyword in context for keyword in period_interest_keywords)
        is_simple_interest, is_compound_interest, is_period_interest = self.check_interest_calculation(context)
        is_interest_calculation = is_simple_interest or is_compound_interest or is_period_interest


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
        
            # 세금 고려 사항까지 포함 
        #few_shot_prompt_examples = self.get_few_shot_prompt_examples()

        while retry_count < max_retries: #groundedness max를 초과하지 않을 경우 

            full_prompt = self.build_prompt(context, question, user_id, product_type, is_interest_calculation)

            qa_prompt = self.create_qa_prompt(full_prompt, chat_history)

            response = self.get_response_from_chain(qa_prompt, question, context, chat_history)

            ## 아래의 내용은 위의 3줄로 대체
            #if user_id is None:
                # 사용자 ID가 제공되지 않은 경우, 기본 프롬프트를 사용
            #    full_prompt = self.qa_system_prompt.format(context=context)
            #else:
            #    print("user_id:", user_id)
                # 사용자 ID가 제공된 경우, 아래 내용 추가
            #    user_details = self.get_user_details(user_id) # 사용자 계좌 정보 
            #    user_bank_balances = user_details[['Bank Name', 'Balance']]

            #    print("user_bank_balances:", user_bank_balances)

                # 사용자의 잔액 한도를 확인하여 은행 리스트를 필터링
                # 예금자 보호 적용 확인용
            #    user_bank_balances = user_bank_balances.groupby('Bank Name')['Balance'].sum().reset_index()
            #    banks_with_high_balance = user_bank_balances[user_bank_balances['Balance'] >= 50000000]['Bank Name'].tolist()
                
            #    print("do_not_bank", banks_with_high_balance)


                # 사용자가 이미 이용 중인 은행을 우선적으로 추천
                # 고객 맞춤형 추천용
            #    prioritized_banks = user_bank_balances['Bank Name'].tolist()

                # 사용자 은행 잔액 정보를 문자열로 변환
            #    user_bank_balances_str = user_bank_balances.to_dict(orient='records')
                
                # 중괄호를 이스케이프하여 문자열 포매팅 오류를 방지
            #    user_bank_balances_str = str(user_bank_balances_str).replace("{", "{{").replace("}", "}}")

                # 위의 내용이 반영된 전체 프롬프트를 구성
            #    full_prompt = self.qa_system_prompt.format(context=context)
            #    full_prompt += f"\nUser's Banks and Balance is {user_bank_balances_str}\n"
            #    full_prompt += f"Try starting the recommendation by indicating the current bank & balance when responding"
            #    full_prompt += "\nRules:\n"
            #    full_prompt += f"- If the recommended product belongs to a bank where the user's balance exceeds 49,999,999, or in {banks_with_high_balance}"
            #    full_prompt += f"  Must indicate the user that \'예금자 보호법에 따라 {banks_with_high_balance} 은행 외의 상품을 추천드립니다.\'\n  and try to recommend products beside the banks in {banks_with_high_balance}"
            #    full_prompt += f"- Prioritize recommendations of the banks the user is already using, such as {prioritized_banks}, unless the balance exceeds the limit.\n"

            #print("chat_history:", chat_history)
            

            # 요청 금융상품의 정보 분별
            #if product_type == '예금':
            #    product_type = '예금'
            #elif product_type == '적금':
            #    product_type = '적금'
            #elif product_type == '예금 & 적금':
            #    product_type = '예금 & 적금'
            #elif product_type == '적용안함':
            #    product_type = None

            #print(product_type, "selected")

            # 응답을 받아오기 위한 프롬프트 생성
            #prompt = f"질문: {question} 특히 {product_type}을 선호해\n응답:"

            # 기존 시스템 프롬프트와 새로 생성한 프롬프트를 통합
            #full_prompt += f"\n{prompt}"

            # 질문이 이자 계산과 관련된 경우, 역할 재명시 
            #if is_simple_interest or is_compound_interest or is_period_interest:
            #    full_prompt += "\nPlease provide a step-by-step reasoning for calculating the interest based on the identified type (단리, 복리, 기간별 이자, 자유 적금). Apply the appropriate formula and provide the maturity amount.\n"

            # few_shot_example 프롬프트 추가 
            #full_prompt += few_shot_prompt_examples

            # 챗봇에게 구조화된 prompt 제공
            #qa_prompt = ChatPromptTemplate.from_messages(
            #    [
            #        ("system", full_prompt),
            #        MessagesPlaceholder("chat_history"),
            #        ("human", "{input}")
            #    ]
            #)

            # 입력을 처리하는 체인을 정의
            #chain = qa_prompt | self.llm | StrOutputParser()

            # 질문과 컨텍스트를 사용하여 체인을 호출
            #response = chain.invoke(
            #    {
            #        "input": question,
            #        "Context": context,
            #        "chat_history": chat_history
            #    }
            #)

            # 응답의 유효성 검증 (직접 은행, 상품정보 제공)
            #valid_banks = {'NH농협은행', '신한은행', 'KB국민은행', '하나은행'}  # 예시 은행명
            #valid_products = {'신한 My플러스 정기예금', 'KB 정기예금'}  # 예시 상품명

            #10.14 추가
            # 응답이 유효한 은행/상품을 포함하는지 확인
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
                    return response 
                else:
                # 응답이 근거에 기반하지 않은 경우, 재시도
                    retry_count += 1
                    print(f"Response not grounded. Retrying... ({retry_count}/{max_retries})")
                    # 다음 시도를 위해 프롬프트를 수정
                    full_prompt += "\nPlease make sure your response is based on the provided context.\n"
            else:# 추천 질문이 아닌 경우, 즉시 응답을 반환
                return response

        # 최대 재시도 횟수에 도달했지만 DB에서 응답을 얻지 못한 경우, 기본 메시지를 반환
        return response if gc_result == "grounded" else "적절한 상품을 찾지 못했어요. 조금만 질문을 구체화해주실 수 있나요?"

    #10.14 추가
    #def is_response_in_context(self, response, context):
    #    """
    #    응답이 검색된 컨텍스트 내의 내용과 일치하는지 확인하는 함수
    #    """
    #    return any(part in context for part in response.splitlines())

    ## 6개 매서드 추가
    def check_recommendation(self, question):
        recommendation_keywords = ["추천", "recommend", "추천해", "추천해줘", "추천해 주세요", "추천 해줘"]
        return any(keyword in question for keyword in recommendation_keywords)
    
    def check_interest_calculation(self, context):
        simple_interest_keywords = ["단리"]
        compound_interest_keywords = ["복리", "연복리", "월복리"]
        period_interest_keywords = ["가입기간별 기본이자율"]
        
        # 이자 계산 유형 확인
        is_simple_interest = any(keyword in context for keyword in simple_interest_keywords)
        is_compound_interest = any(keyword in context for keyword in compound_interest_keywords)
        is_period_interest = any(keyword in context for keyword in period_interest_keywords)

        return is_simple_interest, is_compound_interest, is_period_interest

    def get_few_shot_prompt_examples(self):
        """
        이자 계산과 관련된 few-shot 프롬프트 반환
        """
        return """
            You are to calculate different types of interest accurately and recommend the best product for the user.
            
            ### Calculating Simple Interest (단리)
            - Simple interest is calculated only on the principal amount, not on the accumulated interest.
            - Use the formula: \\(\\text{{Maturity Amount}} = P \\times (1 + r \\times t)\\), where:
                - \\(P\\) is the principal amount.
                - \\(r\\) is the annual interest rate.
                - \\(t\\) is the time in years.

            - **Steps to calculate the maturity amount**:
                1. Identify the principal amount \\(P\\), the annual interest rate \\(r\\), and the time period \\(t\\).
                2. Apply the formula to calculate the interest.
                3. Add the interest to the principal to get the maturity amount.

            - **Example Calculation**:
                - A 2-year deposit of 1,000,000 KRW with an annual interest rate of 5%.
                - Calculate the interest as \\(1,000,000 \\times 0.05 \\times 2 = 100,000\\) KRW.
                - The maturity amount is \\(1,000,000 + 100,000 = 1,100,000\\) KRW.

            ### Calculating Monthly Compound Interest (월복리)
            - Compound interest is calculated on each monthly deposit and also on the accumulated interest over time.
            - Each monthly deposit will accumulate interest for the remaining months until the maturity period.
            - Use the formula: \\(\\text{{Maturity Amount}} = \\sum_{{m=1}}^M \\text{{Monthly Deposit}} \\times (1 + \\text{{Monthly Rate}})^{{(M - m)}}\\), where:
                - \\(M\\) is the total number of months.
                - \\(m\\) is the month index of each deposit (1 for the first month, 2 for the second, ..., M for the last month).
                - \\(\\text{{Monthly Rate}}\\) is \\(\\text{{Annual Interest Rate}} / 12\\).

            - **Steps to calculate the maturity amount**:
                1. Identify the total number of months \\(M\\) and the monthly deposit amount.
                2. Calculate the monthly interest rate as \\(\\text{{Annual Interest Rate}} / 12\\).
                3. For each month \\(m\\), calculate the accumulated value of the deposit compounded over its remaining months \\(M - m\\).
                4. Sum all accumulated values of each monthly deposit to get the final maturity amount.

            - **Example Calculation**:
                - A 2-year deposit (24 months) of 200,000 KRW per month with an annual compound interest rate of 4.55%.
                - Calculate the monthly interest rate as \\(4.55 / 12 = 0.003792\\).
                - For the first deposit made in month 1, it will accumulate interest for 23 months: \\(200,000 \\times (1 + 0.003792)^{{23}}\\).
                - For the second deposit made in month 2, it will accumulate interest for 22 months: \\(200,000 \\times (1 + 0.003792)^{{22}}\\).
                - Continue this process until the last deposit, which will only accumulate interest for 1 month.
                - Sum all accumulated values to obtain the final maturity amount.
            
            ### Calculating Annual Compound Interest (연복리)
            - Compound interest is calculated annually on the principal and any accumulated interest from previous years.
            - Use the formula: \\(\\text{{Maturity Amount}} = P \\times (1 + r)^t\\), where:
                - \\(P\\) is the principal amount.
                - \\(r\\) is the annual interest rate.
                - \\(t\\) is the number of years.

            - **Steps to calculate the maturity amount**:
                1. Identify the principal amount \\(P\\) and the annual interest rate \\(r\\).
                2. Determine the total number of years \\(t\\).
                3. Apply the formula to calculate the maturity amount.

            - **Example Calculation**:
                - A 2-year deposit of 5,000,000 KRW with an annual compound interest rate of 3.5%.
                - Calculate the maturity amount as \\(5,000,000 \\times (1 + 0.035)^2\\).

            ### Calculating Flexible Savings Interest (자유 적금, 자유 적립)

            - Flexible savings interest is calculated daily on each deposit made.
            - Each deposit will accumulate interest from the day of deposit until maturity or the end of the contract period.
            - Use the formula: \\(\\text{{Maturity Amount}} = \\text{{Deposit Amount}} \\times \\left(1 + \\frac{{\\text{{Annual Interest Rate}}}}{{365}} \\times \\text{{Number of Days}}\\right)\\), where:
                - \\(\\text{{Interest}} = \\text{{Deposit Amount}} \\times \\frac{{\\text{{Annual Interest Rate}}}}{{365}} \\times \\text{{Number of Days}}\\)
                - \\(\\text{{Deposit Amount}}\\) is the amount deposited on a particular day.
                - \\(\\text{{Number of Days}}\\) is the number of days from the deposit date to maturity.

            **Steps to calculate the total interest**:
            1. Identify each deposit made, including its date and amount.
            2. Calculate the interest for each deposit using the formula.
            3. Sum all calculated interest values for all deposits to obtain the total interest.

            **Example Calculation**:
            - **First Deposit**:  
                - Deposit Date: January 12, 2023  
                - Amount: 200,000 KRW  
                - Annual Interest Rate: 4.1%  
                - Days to Maturity: 307 days  
                - Interest: \\(\\approx 6,897 \\text{{ KRW}}\\)
            
            - **Second Deposit**:  
                - Deposit Date: March 25, 2023  
                - Amount: 500,000 KRW  
                - Annual Interest Rate: 4.1%  
                - Days to Maturity: 235 days  
                - Interest: \\(\\approx 13,199 \\text{{ KRW}}\\)

            ### Tax Considerations for Savings Products
            - Interest income is subject to taxation based on the type of product and the user's eligibility.
            - **Standard Taxation**:
                - A withholding tax of 15.4% is applied to interest income.
            - **Tax-Preferred Savings (세금우대)**:
                - For eligible individuals (over 20 years old, with a limit of 10 million KRW; senior citizens or disabled persons up to 30 million KRW), a reduced tax rate of 9.5% is applied.
                - Must be enrolled for over 1 year.
            - **Tax-Free Savings (비과세 생계형)**:
                - For eligible individuals, interest income up to 30 million KRW is exempt from taxes.
                - Since January 1, 2015, the name changed to "Tax-Free Comprehensive Savings" (비과세종합저축).
                - Maximum limit increased to 50 million KRW (including the former tax-preferred and livelihood savings).

            - **Note on Tax Law Changes**:
                - The tax rate is subject to change if relevant tax laws are amended.
                - Always verify with the nearest bank branch for precise and updated information as the calculations based on monthly compounding may differ slightly from actual product details which calculate interest on a daily basis.
            """

    def build_prompt(self, context, question, user_id, product_type, is_interest_calculation=False):

        # 요청 금융상품의 정보 분별
        ## product_type == '적용안함' 인 경우에만 바꾸고 나머지는 그대로 쓰도록 하는게 낫지 않을까?
        if product_type == '예금':
            product_type = '예금'
        elif product_type == '적금':
            product_type = '적금'
        elif product_type == '예금 & 적금':
            product_type = '예금 & 적금'
        elif product_type == '적용안함':
            product_type = None

        print(product_type, "selected")    

        if user_id is None:
            # 사용자 ID가 제공되지 않은 경우, 기본 프롬프트를 사용
            full_prompt = self.qa_system_prompt.format(context=context)
        else:
            print("user_id:", user_id)
            # 사용자 ID가 제공된 경우, 아래 내용 추가
            user_details = self.get_user_details(user_id) # 사용자 계좌 정보 
            user_bank_balances = user_details[['Bank Name', 'Balance']]

            print("user_bank_balances:", user_bank_balances)

            # 사용자의 잔액 한도를 확인하여 은행 리스트를 필터링
            # 예금자 보호 적용 확인용
            user_bank_balances = user_bank_balances.groupby('Bank Name')['Balance'].sum().reset_index()
            banks_with_high_balance = user_bank_balances[user_bank_balances['Balance'] >= 50000000]['Bank Name'].tolist()
                
            print("do_not_bank", banks_with_high_balance)

            # 사용자가 이미 이용 중인 은행을 우선적으로 추천
            # 고객 맞춤형 추천용
            prioritized_banks = user_bank_balances['Bank Name'].tolist()

            # 사용자 은행 잔액 정보를 문자열로 변환
            user_bank_balances_str = user_bank_balances.to_dict(orient='records')
                
            # 중괄호를 이스케이프하여 문자열 포매팅 오류를 방지
            user_bank_balances_str = str(user_bank_balances_str).replace("{", "{{").replace("}", "}}")

            # 위의 내용이 반영된 전체 프롬프트를 구성
            full_prompt = self.qa_system_prompt.format(context=context)
            full_prompt += f"\nUser's Banks and Balance is {user_bank_balances_str}\n"
            full_prompt += f"Try starting the recommendation by indicating the current bank & balance when responding"
            full_prompt += "\nRules:\n"
            full_prompt += f"- If the recommended product belongs to a bank where the user's balance exceeds 49,999,999, or in {banks_with_high_balance}"
            full_prompt += f"  Must indicate the user that \'예금자 보호법에 따라 {banks_with_high_balance} 은행 외의 상품을 추천드립니다.\'\n  and try to recommend products beside the banks in {banks_with_high_balance}"
            full_prompt += f"- Prioritize recommendations of the banks the user is already using, such as {prioritized_banks}, unless the balance exceeds the limit.\n"
        
        # 이자 계산 관련일 경우
        if is_interest_calculation:
            full_prompt += "\nPlease provide a step-by-step reasoning for calculating the interest based on the identified type (단리, 복리, 기간별 이자, 자유 적금). Apply the appropriate formula and provide the maturity amount.\n"
            
            # 해당 경우에만 few_shot_prompt를 추가하면 될 것이라 봄 -- 아닐 경우 if 문 밖으로 꺼내 항상 계산시 활용하도록 한다.
            full_prompt += self.get_few_shot_prompt_examples()
        
        return full_prompt + f"\n질문: {question} 특히 {product_type}을 선호해\n응답:"

    # MessagesPlaceholder("chat_history") 왜 필요한거지?
    def create_qa_prompt(self, full_prompt, chat_history):
        return ChatPromptTemplate.from_messages([
            ("system", full_prompt),
            MessagesPlaceholder("chat_history"),
            ("human", "{input}")
        ])
    
    def get_response_from_chain(self, qa_prompt, question, context, chat_history):
        # 입력을 처리하는 체인을 정의
        chain = qa_prompt | self.llm | StrOutputParser()

        # 질문과 컨텍스트를 사용하여 체인을 호출
        response = chain.invoke(
            {
                "input": question,
                "Context": context,
                "chat_history": chat_history
            }
        )
        return response

 #10.14 수정
 #추가 수정
    def retrieve_documents(self, query, product_type='적용안함', top_k=5):
        """
        사용자가 입력한 쿼리를 기반으로 관련 문서 검색 함수
        금융상품 종류에 맞는 임베딩 폴더에서 문서를 검색
        """
        
        # 상품 종류에 맞는 리트리버 설정
        self.set_retriever_by_product_type(product_type)

        # 디버그: 리트리버가 올바르게 설정되었는지 확인
        if self.retriever:
            print(f"Using retriever for product type: {product_type}")
        else:
            print(f"Retriever for {product_type} is not set. Check the configuration.")
            return None

        print(f"Query: {query} | Product Type: {product_type}")

        #디버그
        try:
            # 검색 수행
            search_result = self.retriever.invoke(query, top_k=top_k)
            if not search_result:
                print(f"No documents retrieved for the query '{query}' with product type '{product_type}'.")
                return None
            else:
                print(f"Number of documents retrieved: {len(search_result)}")
        
            extracted_texts = []
            valid_banks = set()  # 추가수정: 유효한 은행명 저장
            valid_products = set()  # 추가수정: 유효한 상품명 저장
            for search in search_result:
                soup = BeautifulSoup(search.page_content, "html.parser")
                text = soup.get_text(separator="\n")
                extracted_texts.append(text)

                # 추가수정 은행명 및 상품명 추출 디버깅 추가
#                if "은행명" in text:
#                    bank = text.split("은행명")[1].split(":")[1].strip().split()[0]  # 예시 패턴으로 은행명 추출
#                    valid_banks.add(bank)
#                    print(f"Extracted Bank Name: {bank}")
#
#                if "상품명" in text:
#                    product = text.split("상품명")[1].split(":")[1].strip().split()[0]  # 예시 패턴으로 상품명 추출
#                    valid_products.add(product)
#                    print(f"Extracted Product Name: {product}")

            # 추가수정: 디버그: 추출된 은행명과 상품명을 로그로 출력
#            print("Valid banks extracted from PDF:", valid_banks)
#            print("Valid products extracted from PDF:", valid_products)


            context = "\n".join(extracted_texts)
            print(f"Context extracted for product type '{product_type}':\n{context[:500]}...")  # 첫 500글자만 출력
            return context
        
        except Exception as e:
            print(f"Error while retrieving documents: {str(e)}")
            return None
    
    def check_groundedness(self, context, response):
        """ 응답의 근거성(groundedness) 검사 함수 """
        groundedness_check = UpstageGroundednessCheck() 
        gc_result = groundedness_check.invoke({"context": context, "answer": response})
        return gc_result
    
#10.14 수정    
    def set_retriever_by_product_type(self, product_type):
            """ 금융상품 종류에 맞는 리트리버를 설정하는 함수 """
            if product_type == '예금':
                self.retriever = self.retriever_예금
            elif product_type == '적금':
                self.retriever = self.retriever_적금
            else:
                self.retriever = self.retriever_예금_적금  # 예금 & 적금 혹은 기타
###안씀
#10.14 추가
    def extract_valid_banks_and_products(self, context, predefined_valid_banks, predefined_valid_products):
        """
        문서에서 유효한 은행명과 상품명을 추출하는 함수. 
        미리 제공된 은행명과 상품명을 포함하여 처리.
        """
        # 미리 제공된 은행명과 상품명을 set으로 초기화
        valid_banks = set(predefined_valid_banks)
        valid_products = set(predefined_valid_products)

        # 문서에서 은행명과 상품명을 추출
        for line in context.splitlines():
            if "은행명" in line:
                split_line = line.split(":")
                if len(split_line) > 1:  # split 결과가 기대한 대로 적어도 두 요소가 있는지 확인
                    bank_name = split_line[1].strip()
                    print(f"Extracted bank: {bank_name}")
                    valid_banks.add(bank_name)  # 추출된 은행명 추가
                    if bank_name not in valid_banks:
                        print(f"Invalid bank found: {bank_name}")
                        return False
                else:
                    print(f"Invalid format for bank line: {line}")

            if "상품명" in line:
                split_line = line.split(":")
                if len(split_line) > 1:  # split 결과가 기대한 대로 적어도 두 요소가 있는지 확인
                    product_name = split_line[1].strip()
                    print(f"Extracted product: {product_name}")
                    if product_name not in valid_products:
                        print(f"Invalid product found: {product_name}")
                        return False
                    valid_products.add(product_name)  # 추출된 상품명 추가
                else:
                    print(f"Invalid format for product line: {line}")

        print(f"Valid banks extracted: {valid_banks}")
        print(f"Valid products extracted: {valid_products}")
        return valid_banks, valid_products
