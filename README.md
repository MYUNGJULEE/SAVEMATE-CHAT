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


Launch the chat service locally :
```bash
streamlit run /Users/imyungju/desktop/code_sh/CHATBOT_BASIC/src/SaveMate-chat.py #로컬 주소로 바꾼 후 실행
```
#### That's it! The service is now up and running locally. 🤗

## Contributing 🙌
If you want to contribute to this project, please open an issue, submit a pull request or contact me at barbot.yvann@gmail.com #수정 (:


