import requests
from bs4 import BeautifulSoup
import datetime
import os
import time

# ------------------------------------------------------
# 설정값 (깃허브 Secrets에서 가져옴)
# ------------------------------------------------------
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('CHAT_ID')

# ------------------------------------------------------
# 텔레그램 메시지 전송 함수
# ------------------------------------------------------
def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {'chat_id': CHAT_ID, 'text': message}
    try:
        requests.post(url, data=data)
        print("메시지 전송 완료")
    except Exception as e:
        print(f"메시지 전송 실패: {e}")

# ------------------------------------------------------
# 메인 로직
# ------------------------------------------------------
def main():
    # 1. 한국 시간(KST) 구하기
    # 깃허브 서버(UTC) + 9시간 = 한국 시간
    now_kst = datetime.datetime.utcnow() + datetime.timedelta(hours=9)
    today_str = now_kst.strftime("%Y.%m.%d")
    
    print(f"현재 시간(KST): {now_kst.strftime('%Y-%m-%d %H:%M:%S')}")

    # 2. 네이버 IPO 페이지 접속
    target_url = "https://finance.naver.com/sise/ipo.nhn"
    headers = {'User-Agent': 'Mozilla/5.0'} 
    
    try:
        response = requests.get(target_url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
    except Exception as e:
        send_telegram_message(f"오류 발생: 네이버 접속 실패\n{e}")
        return

    table_rows = soup.select("div.type_list > table.type_5 tr")
    messages = []

    # 3. 데이터 분석
    for row in table_rows:
        cols = row.find_all("td")
        if len(cols) < 4: 
            continue

        try:
            name = cols[0].get_text(strip=True) # 종목명
            sub_schedule = cols[1].get_text(strip=True) # 공모 일정
            listing_date = cols[2].get_text(strip=True) # 상장일

            # 3-1) 청약 일정 확인 (1일차, 2일차)
            if "~" in sub_schedule:
                dates = sub_schedule.split("~")
                start_date_str = dates[0].strip()
                end_date_part = dates[1].strip()

                start_date = start_date_str
                start_year = start_date_str.split(".")[0]
                
                if len(end_date_part.split(".")) == 2:
                    end_date = f"{start_year}.{end_date_part}"
                else:
                    end_date = end_date_part

                if today_str == start_date:
                    messages.append(f"🔔 [청약 1일차] {name}\n일정: {sub_schedule}")
                elif today_str == end_date:
                    messages.append(f"🚨 [청약 마감] {name}\n일정: {sub_schedule}")

            # 3-2) 상장일 확인
            if listing_date and listing_date != "미정":
                if today_str == listing_date:
                    messages.append(f"🎉 [오늘 상장] {name}")

        except Exception as e:
            continue

    # 4. 결과 전송 (7시 대기 로직)
    if messages:
        final_msg = f"📅 {today_str} 공모주 알림\n\n" + "\n\n".join(messages)
        
        # 목표 시간: 오늘 아침 7시 0분 0초
        target_time = now_kst.replace(hour=7, minute=0, second=0, microsecond=0)
        
        # 현재 시간이 7시보다 전이라면 기다림
        if now_kst < target_time:
            wait_seconds = (target_time - now_kst).total_seconds()
            print(f"현재 {now_kst.strftime('%H:%M:%S')}, 7시 발송을 위해 {wait_seconds:.0f}초 대기합니다...")
            time.sleep(wait_seconds)
        else:
            print("이미 7시가 지났거나 깃허브 실행이 늦었습니다. 즉시 발송합니다.")
        
        # 발송
        send_telegram_message(final_msg)
    else:
        print("오늘은 알림 보낼 일정이 없습니다.")

if __name__ == "__main__":
    main()
