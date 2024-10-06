# SaveMate-chatbot 🤖

[![Twitter Follow](https://img.shields.io/twitter/follow/yvann_hub?style=social)](https://twitter.com/yvann_hub)


### An AI chatbot featuring conversational memory, designed to enable users to discuss their CSV, PDF, TXT data and YTB videos in a more intuitive manner. 🚀
![Robby](golden_retriever.jpg)
Robby the Robot from [Forbidden Planet](https://youtu.be/bflfQN_YsTM)

#### For better understanding, see my medium article 🖖 : [Build a chat-bot over your CSV data](https://medium.com/@yvann-hub/build-a-chatbot-on-your-csv-data-with-langchain-and-openai-ed121f85f0cd)

## Quick Start 🚀 (Website in maintenance)

[![Robby-Chatbot](https://img.shields.io/static/v1?label=Robby-Chatbot&message=Visit%20Website&color=ffffff&labelColor=ADD8E6&style=for-the-badge)](https://robby-chatbot.streamlit.app/)

##Quick Start (streamlit.app 배포)
https://savemate-chat1.streamlit.app/


## Running Locally 💻
Follow these steps to set up and run the service locally :

### Prerequisites
- Python 3.8 or higher
- Git

### Installation
Clone the repository :

`git clone https://github.com/MYUNGJULEE/SAVEMATE-CHAT`


Navigate to the project directory :

`cd CHATBOT_BASIC`


Create a virtual environment for Windows:
```bash
python -m venv .venv
.\.venv\Scripts\activate
```

Create a virtual environment for Mac/Linux:
```bash
python -m venv .venv
source .venv/bin/activate
```

Install the required dependencies in the virtual environment :
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

.env 파일 생성후 환경변수 설정 후 확인 (자신의 upstage api key로 변경)
```bash
export UPSTAGE_API_KEY="up_1RO1Iau1STYJ6PyihOQmRUJyHtacD"
echo UPSTAGE_API_KEY= up_1RO1Iau1STYJ6PyihOQmRUJyHtacD > .env
cat .env
```


Launch the chat service locally (로컬 주소로 바꾼 후 실행) :
```bash
streamlit run /Users/imyungju/desktop/code_sh/CHATBOT_BASIC/src/SaveMate-chat.py 
```


## 사용방법

1. 사이드바에서 유저아이디를 입력해주세요. 입력하지 않으면 게스트모드로 실행됩니다.
2. 사이드바에서 금융상품종류를 입력해주세요. 입력하지 않으면 일반채팅모드(금융상품정보 적용안함)로 실행이 됩니다.
3. 채팅창에 '기능별 가이드라인'과 '내가 원하는 조건 찾아내기 가이드라인' 을 참고하여 자유롭게 입력하세요.

        기능별 가이드라인
        [마이데이터 기반 예금/적금상품 추천 기능]
        1. 유저아이디를 사이드바에서 입력하세요. 
        2. 원하시는 금융상품을 사이드바에서 선택하세요.
        3. 채팅창에 내 계좌정보 알려줘를 입력해주세요.
        4. 이후, 원하시는 조건 + 상품 추천해줘를 입력해주세요.
        5. 원하시는 조건의 예시로는 군인, 20대, 50대가 있습니다.
        6. 마이데이터에서 계좌잔액, 주거래은행 등의 정보를 반영해서 예금자보호법에 따라 상품을 추천합니다.
        7. 보다 자세한 조건 구성방법은 아래 '내가 원하는 조건 찾아내기 가이드라인'을 참고하세요.

        [상품정보 검색 기능]
        1. 채팅창에 원하시는 상품명 + 궁금한 내용을 입력하세요.
        2. 현재 10여개 은행의 50여개의 상품정보가 준비되어 있습니다.
        3. 상품명 예시: 우리 SUPER주거래 정기적금, 급여하나 월복리 적금, 행복knowhow 연금예금, NH장병내일준비적금

        [금융정보 기능]
        1. 궁금하신 금융정보를 채팅창에 자유롭게 물어보세요.
        2. 금융정보 예시: 복리, 예금자보호법, 인플레이션

        '내가 원하는 조건 찾아보기' 가이드라인
        1. 어떤 금융 목표를 달성하고 싶으신가요? (예: 목돈 모으기, 주택 구매, 여행 자금 등) 
        2. 예금 또는 적금에 얼마나 많은 금액을 투자하고 싶으신가요? 
        3. 예금 또는 적금의 기간은 어느 정도로 생각하고 계신가요? (예: 단기, 중기, 장기) 
        4. 우대금리를 받기 위해 어떤 조건을 충족하실 수 있으신가요? (예: 급여 이체, 카드 이용, 마케팅 동의 등)
        5. 채팅창에 위에서 찾아낸 원하는 조건 + 상품 추천해줘를 입력하세요.
        6. 채팅문구 예시: 목돈 모으기, 1000만원 투자, 단기, 급여 이체 우대 조건 고려해서 상품 추천해줘
