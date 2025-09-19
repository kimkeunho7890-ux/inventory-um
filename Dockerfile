# 1. 안정적인 파이썬 3.11 버전의 공식 이미지를 기반으로 시작합니다.
FROM python:3.11-slim

# 2. 앱 파일을 저장할 작업 폴더를 만듭니다.
WORKDIR /app

# 3. 먼저 필요한 라이브러리 목록을 복사합니다.
COPY requirements.txt .

# 4. 라이브러리를 설치합니다.
RUN pip install --no-cache-dir -r requirements.txt

# 5. 나머지 모든 프로젝트 파일들을 복사합니다.
COPY . .

# 6. 앱을 실행하는 기본 명령어를 설정합니다.
CMD ["streamlit", "run", "app.py", "--server.port", "10000", "--server.enableCORS", "false"]