# Day 3

# 모듈 준비 #######################################################

# OLED display 관련
import Adafruit_GPIO.SPI as SPI
import Adafruit_SSD1306
from PIL import Image
from PIL import ImageFont
from PIL import ImageDraw
DisplayWidth, DisplayHeight = 64, 128 # OLED display 해상도
RST, DC, SPI_PORT, SPI_DEVICE = 24, 25, 0, 0 # OLED pin 설정

# datetime 관련
from datetime import datetime, timedelta, timezone
TimeZone = timezone(timedelta(hours = +9)) # 서울표준시

#  GPIO
import RPi.GPIO as GPIO
(OKbtn, UPbtn, DOWNbtn) = (12, 5, 6)  #  GPIO 핀 할당

# google cloud platform 관련
import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
# 구글 클라우드 플랫폼 프로젝트 클라이언트 인증정보파일
GOOGLE_CLIENT_SECRET_JSON_FILE_NAME = 'my_credentials.json'
# 구글 authorization 요청 범위
SCOPES = ['https://www.googleapis.com/auth/gmail.modify', 'https://www.googleapis.com/auth/calendar.readonly']

# 쓰레드: 글자 애니메이션
import threading
from time import sleep

# Noti image는 전체 화면보다 조금 작게 만들어 시계가 항상 노출 되도록 하자
NotiWidth, NotiHeight, NotiHeightMAX = 60, 100, 450 # 시계보이도록 조금 작게. gmail 메시지가 중간에 짤린다면 max를 키워준다.

# classes ########################################################
# Noti 추상 클래스
class Noti:
    def __init__(self):
        self.image = None   #모든 Noti 는 화면에 보여질 image를 갖도록하자.
        self.id = None
        self.pagemark = 1

    # 버튼 눌렸을 때 각 노티의 작용
    def whenOKpressed(self):
        pass
    def whenUPpressed(self):
        pass
    def whenDOWNpressed(self):
        pass

    # 텍스트가 화면을 좌에서 우로 흘러가며 디스플레이되도록
    # threading.Thread()를 사용해 별도 쓰레드로 작동시키자. 이 떼 Daemon=True로해야 종료후 없어짐.
    def textAniThread(self, image, text, textXposition, textYposition): # 텍스트를 표시할 이미지 (PIL image object), 표시할 텍스트, x좌표, y좌표.

        draw = ImageDraw.Draw(image)
        font_body = ImageFont.truetype("malgun.ttf", 10)

        while True:
            # 검정박스로 텍스트 지우기 (텍스트 높이는 13으로 가정...)
            draw.rectangle((0, textYposition, NotiWidth, textYposition+13), fill=0)
            # 텍스트 쓰기
            draw.text((textXposition,textYposition),text, font= font_body, fill = 1)
            sleep(0.5) # 이 시간이 길면 깜빡거림이 줄어듬.

            # 다음 턴엔 3px 씩 좌로 이동 (만일 문자열 우측 끝이 화면을 벗어났다면 최초위치로 )
            if textXposition <= -(draw.textsize(text, font= font_body)[0]):
                textXposition = NotiWidth
            else:
                textXposition -= 3

# 새로운 메일이 있을 때 뜨는 noti메시지
class GmailNoti(Noti):
    def __init__(self, message): # gmail message를 받는다. message  내용 구성은 'http://googleapis.github.io/google-api-python-client/docs/dyn/gmail_v1.users.messages.html#get'  참고

        # 멤버변수 초기화
        self.id = message['id'] # 메일 고유 id
        for header in message['payload']['headers']:
            if ('name','From') in header.items():
                self.fromWho = header['value']   # 발신인(from은 파이썬 키워드이기 때문에 fromWho 로 표기)
            elif ('name','Subject') in header.items():
                self.subject = header['value'] # 제목
        self.body = message['snippet'] #본문요약

        # gmailNoti는 2페이지로 구성되며, 처음엔 1페이지가 표시된다.
        # self.page1 = self.createPage1Image()
        self.createPage1Image()
        self.image = self.page1
        self.pagemark = 1 # noti가 표시하고있는 현재 페이지
        # 페이지 스크롤효과를 위한 offset값 초기화
        self.pageOffsetY = 0
        self.createPage2Image() # 디스플레이 속도 문제로 page2도 먼저 만들어놓는다.

    # GmailNoti page1-image  생성
    def createPage1Image(self):

        self.pageOffsetY = 0 # 페이지 스크롤 초기화

        im = Image.open('gotamail.png').convert(mode='1') # 도트 편집기로 만든 이미지 64x108px, mode='1'로 변환
        self.page1 = im

        #화면이 작으므로 텍스트가 흘러가도록 하자(매 프레임마다 좌로 5px씩...)
        t = threading.Thread(target = self.textAniThread, args = (im, self.fromWho, 10,80), daemon = True)
        t.start()

    def createPage2Image(self):

         self.pageOffsetY = 0   # 페이지 스크롤 초기화

         im = Image.new('1', (NotiWidth, NotiHeightMAX),0)
         draw = ImageDraw.Draw(im)
         #draw.rectangle((0,0,NotiWidth,NotiHeight),fill=0)
         font_label = ImageFont.truetype("Arial.ttf",8)
         font_body = ImageFont.truetype("malgun.ttf", 10)
         text_line_gap = 2 # 줄간격(px)

         # subject 레이블
         draw.text((0,5), 'Subject:', font=font_label, fill=1)
         # subject
         draw.text((0,14), self.subject, font=font_body, fill=1)
         # from 레이블
         draw.text((0,34), 'From:', font=font_label, fill=1)
         # from
         draw.text((0,43), self.fromWho, font=font_body, fill=1)
         # 내용
         # 내용이 디스플레이 폭에 맞추어 줄바꿈 되도록, self.body의 내용을 한자씩 새로운 문자열에 추가하면서 가로폭을 재보고, NotiWidth  보다 커지면 '\n'넣어줌.
         contents =''
         for ch in self.body:
             contents += ch
             if draw.textsize(contents, font=font_body)[0] >= NotiWidth:
                contents = contents[:-1]+'\n'+contents[-1]  # 마지막 글자 바로앞에서 줄바꿈
            # 메시지 끝알림
         contents += '\n  <end>'
         draw.text((0,63), contents, font=font_body, spacing = 0, fill=1)

         self.page2 = im

    # 버튼 눌렸을 때의 동작
    def whenDOWNpressed(self):
        if self.pagemark == 1:
            pass
        elif self.pagemark == 2:
            #다운버튼 눌리면 image crop하는 범위를 더 아래로 내림
            self.pageOffsetY += 5
            self.image = self.page2.crop((0, self.pageOffsetY ,NotiWidth ,NotiHeight+self.pageOffsetY))

    def whenUPpressed(self):
        if self.pagemark == 1:
            pass
        elif self.pagemark == 2:
            #다운버튼 눌리면 image crop하는 범위를 더 아래로 내림
            self.pageOffsetY -= 5
            self.image = self.page2.crop((0, self.pageOffsetY ,NotiWidth ,NotiHeight+self.pageOffsetY))

    def whenOKpressed(self):

        # 메시지를 읽음으로 표시하고 메인 루프에  noti를 삭제하라고 알려줌.
        #차후  page1,2를 구분해 page1이 디스플레이중일때에는 page2로 넘어가고 page2일때는 메시지 읽음표시하도록 수정.
        if self.pagemark == 1:  # 현재 1페이지일때
            self.image = self.page2.crop((0,0,NotiWidth,NotiHeight)) #page2 image 는 메일내용을 담고있어 길다.
            self.pagemark = 2 # noti가 표시하고있는 현재 페이지 = 2
        elif self.pagemark == 2: #현재 2페이지일때

            #메시지 읽음표시
            self.markEmailRead()

            return 'CLOSE'  # 메인루프에서 마지막 NotiList 아이템을 삭제토록함
        else:
            print('we should not reach here')

    # gmail message 읽음으로 표시
    def markEmailRead(self):
        gmailChecker.markEmailRead(self.id)

# 일정이 다가왔을 때 알려주는  노티 메시지
class CalendarNoti(Noti):
    def __init__(self, event): # calendar list로부터 event dict.를 받는다. http://googleapis.github.io/google-api-python-client/docs/dyn/calendar_v3.events.html#list 참고

        # 멤버변수 초기화
        self.id = event['id'] # 이벤트 고유 id
        self.title = event['summary']   # 이벤트 제목
        self.startTime = datetime.fromisoformat(event['start']['dateTime']) # datetime object
        self.image = None
        self.createCalendarNotiImage()

    def createCalendarNotiImage(self):
    # 달력 그림을 배경으로 이벤트 타이틀과 남은 시간을 표시.
        im = Image.open('eventcoming.png').convert(mode='1')
        self.image = im

        #이벤트 타이틀 애니메이션 표시
        t = threading.Thread(target = self.textAniThread, args = (im, 'EVENT : '+self.title, 10,10), daemon = True)
        t.start()

        # 몇분안에 시작되는지 표시
        seoulnow = datetime.now(timezone(timedelta(hours=9)))
        timeLeft = str(self.startTime - seoulnow) # timedelta.str(timedate): 시간을 문자열로 표현.

        # 시작시간이 지나갔으면 timeLeft는 -로 시작함.
        if timeLeft[0] is '-':
            text = '일정이\n이미 시작됨'
        else:
            text = ' 일정 시작 \n' + timeLeft.split(':')[1] + ' 분 전' # 남은 시간이 실시간으로 카운트다운된다면 좋겠다?

        draw = ImageDraw.Draw(im)
        font = ImageFont.truetype("malgun.ttf", 11)
        draw.text((0,70),text,font = font, spacing = 0, fill=1, align = 'center')

    def whenOKpressed(self):
        return 'CLOSE'

# Checker 추상 클래스- 주기적으로 메일, 시간 등을 확인하는 오브젝트들
class Checker:
    # checker()를 반드시 구현토록 하자.
    def check(self):
        pass

# 시간확인하는 콤포넌트
class TimeChecker(Checker):
    # 모드 초기화
    def __init__(self):
        self.dateMode = False   # dateMode=True : 날짜표시, Flase : 시각표시

    # 현재시간 얻기
    def getCurrentTime(self):
        return datetime.now(TimeZone)

    # 특정한 형식으로 시간 표현 ..."pm 3:00" 과 같은 형식으로
    def getTimeString(self, time):
        return time.strftime('%p %I:%M:%S')

    # 특정한 형식으로 날짜 표현 ..."8월 15일 화요일 " 과 같은 형식으로
    def getDateString(self, date):
        wol = date.month
        il = date.day
        yoil = '월화수목금토일'[date.weekday()]
        return '%s월,%s일,%s요일' %(wol, il, yoil)

    # 현재 시간을 체크해서 적당한 양식으로 바꾼후 BgImage에 그려둔다...루프 내무에 들어간다.
    def check(self):

        draw = ImageDraw.Draw(BgImage)
        draw.rectangle((0,0,DisplayWidth,12),fill=0) # 글상자 지움 높이는 12?
        font= ImageFont.truetype("malgun.ttf",10)

        # Timechecker.dateMode 에 따라 시간이나 날짜를 표시함.
        if self.dateMode is False: # 시간모드(디폴트)
            timeString = self.getTimeString(self.getCurrentTime())
            draw.text((10,0),timeString[:8], font = font, fill = 1)

        else: # 날짜모드
            dateStringList = self.getDateString(datetime.today())
            # 예를들어, '8월,15일,월요일'
            draw.text((13,0), dateStringList[:-4], font = font, fill = 1) # 월일까지만...

# 새 메일 있는지 확인하는 콤포넌트
class GmailChecker(Checker):
    def __init__(self,service):
        self.gmailService = service

    def check(self):
        # inbox 보관함의 목록 가져오기 (q= 아규먼트  사용해 읽지않은 메시지만 가져오기)

        mailList = self.gmailService.users().messages().list(userId='me', labelIds=['INBOX'], q='is:unread', maxResults='3' ).execute() # 리퀘스트 보냄.

        messages = mailList.get('messages', []) # messages 라는 어트리뷰트가 없는 경우  디폴트로 [](빈 리스트)를 가짐.

        # 새로운 메시지 각각에 대해, 현재 만들어져있는  notilist중 GmailNoti 와  id 비교한 후, 새로운 id로 확인되면 GmailNoti object 만들어 NotiList[]에 집어넣기.
        for message in messages: #각각의 메일에 대해
            messageId = message['id']
            sameFlag = False    # id가 동일한 메시지가 이미 있다면 flag를 True로 바꾸기로하자.
            for noti in NotiList:   # 현재 디스플레이되고있는 noti들과 비교
                if not isinstance(noti, GmailNoti):
                    continue
                elif noti.id ==messageId:
                    sameFlag = True
                    break
            if sameFlag == False:

                messageContents = self.gmailService.users().messages().get(userId='me', id=messageId).execute() #특정한 메시지를 리퀘스트
                NotiList.insert(0,GmailNoti(messageContents)) # 새로운 GmailNoti object  생성. 새로운 메시지는 리스트의 앞쪽에 끼워넣기-메일 읽는중에 업데이트되거나 하면 불편하므로...

    # 특정 이메일을 읽은것으로 표시
    def markEmailRead(self,messageId):
            resp = self.gmailService.users().messages().modify(userId='me',id=messageId,body={"removeLabelIds": [ "UNREAD"]} ).execute() #'UNREAD' 라벨을 삭제하면 읽은것으로 표시됨.
            return resp

# 다가오는 일정이 있는지 확인하는 콤포넌트
class CalendarChecker(Checker):
    def __init__(self,service):
        self.calendarService = service
        self.checkedEventId = []

    def check(self):
        # 지금 부터 10분 후까지의 이벤트 가져오기.
        # 이미 확인한 이벤트 목록과 id 비교.
        # 현재 표시되고있는  (NotiList안에 있는 ) CalendarNoti와 비교
        # 처음 등장한 이벤트라면 새로운 CalendarNoti 만들어  NotiList[]  맨 앞쪽에 끼워넣기
        now = datetime.utcnow() # 현재  GMT 표준시
        tenMinuteAfterNow = now + timedelta(minutes=10) # timedelta class  사용해  10분 더함.
        list = self.calendarService.events().list(calendarId='primary', timeMin=now.isoformat()+'Z', timeMax =tenMinuteAfterNow.isoformat()+'Z', maxResults = 3).execute()

        events = list.get('items',[]) # 응답에 'items'항목이 없다면 디폴트는 빈 리스트 []

        for event in events: # 각각의 이벤트에 대해
            eventId = event['id']
            if eventId not in self.checkedEventId:  # 이미 확인한 이벤트가 아니라면,
                NotiList.insert(0,CalendarNoti(event)) #노티 리스트 맨 앞에 추가. 별도로 get().execute()로 이벤트를 가져오지 않는데, 리스트에 포함된 내용으로 충분하기 때문.
                self.checkedEventId.append(eventId) # 확인한 이벤트 목록에 현재 이벤트 추가
                if len(self.checkedEventId) >=5:    # 리스트가 계속 길어지는건 좋지않으므로 5개까지로 제한.
                    del self.checkedEventId[0]

# 메인 스레드 #####################################################

# 디스플레이 콤포넌트는 전역에서 접근가능한
BgImage = None #백그라운드 이미지 PIL.Image 객체
Display = None # oled 디스플레이
NotiList = [] # 알림메시지들,뒤로갈수록 위쪽 레이어
(gmailChecker,calendarChecker) = (None, None)   # gmail, calendar 체커

# 백그라운드 이미지 초기화
def bgImageInitiator():
    return Image.new('1', (DisplayWidth, DisplayHeight),0) # mode = '1' 단색 비트맵이미지

# 디스플레이 초기화
def displayInitiator():
    disp = Adafruit_SSD1306.SSD1306_128_64(rst=RST, dc=DC, spi=SPI.SpiDev(SPI_PORT,SPI_DEVICE,max_speed_hz=8000000))
    disp.begin()
    disp.clear()
    disp.display()
    return disp

# 매 루프마다 updateDisplay()를 실행해 표시해야할 모든 이미지 레이어를 하나로 합쳐 디스플레이한다.
def updateDisplay():

    # bgImage를 tempImage에 머지
    tempImage = Image.new('1', (DisplayWidth, DisplayHeight), 0)
    tempImage.paste(BgImage,(0,0))

    # 매 루프마다 NotiList[]에 있는(=현재 디스플레이에 올라가있는)  Noti들을 차례대로  tempImage에 머지시킴
    for noti in NotiList:
        hGap = int((DisplayWidth - NotiWidth )/2)
        vGap = int((DisplayHeight - NotiHeight)/2)
        messagebox = (0+hGap,0+vGap,DisplayWidth-hGap,DisplayHeight-vGap)  # 전체 디스플레이의 중심에 메시지 디스플레이
        notiImage = noti.image
        tempImage.paste(notiImage,messagebox)

    # 준비된 tempImage가 최종적으로 반영되어 oled에 표시됨
    # 화면을 기기에 맞추어 세로로 회전, 거울상만들기.
    flippedImage = tempImage.transpose(Image.FLIP_LEFT_RIGHT)
    rotatedImage = flippedImage.transpose(Image.ROTATE_90)
    Display.image(rotatedImage)
    # 최종적으로 oled에 표현
    Display.display()

#  버튼 인터럽트 초기화
def initButtons():
    GPIO.setmode(GPIO.BCM)
    buttons = [OKbtn, UPbtn, DOWNbtn]
    GPIO.setup(buttons, GPIO.IN, pull_up_down=GPIO.PUD_UP) # 3개버튼. 버튼을 input으로. 내장 풀업 활성화

    # 인터럽트 스레드 시작. debounce 적용 4개 버튼에 대해
    for bt in buttons:
        GPIO.add_event_detect(bt, GPIO.FALLING, callback=buttonPressed, bouncetime=200)

# 버튼 인터럽트 콜백함수
def buttonPressed(channel):
    #test
    print('button %s pressed!' %channel)

    # 키가 눌렸으면 Notilist의 마지막 아이템(디스플레이 가장 표면레이어)로
    # 어떤 키가 눌려졌는지를 보냄.
    # Noti object로부터 str으로된 응답을 리턴받아 처리할 일이 있다면 적절히 처리함.
    # 예를들어 응답이 'CLOSE'라면 noti를 NotiList[]에서 삭제.

    if len(NotiList) is 0:   #  Noti가 디스플레이되고있지 않다면
        #bgImage에서 필요한 사항 처리: 시간-날짜 모드 변경
        timeChecker.dateMode = not timeChecker.dateMode

    else:       #  Noti 가 하나라도 디스플레이되고있다면
        target = NotiList[len(NotiList)-1]
        response = None # Noti Object로부터의 리턴을 받게될 변수

        if channel == OKbtn:
            response = target.whenOKpressed()

        elif channel == UPbtn:
            response = target.whenUPpressed()

        elif channel == DOWNbtn:
            response = target.whenDOWNpressed()

        if response == 'CLOSE': # 제어권을 넘겨준 class로부터 'CLOSE'응답이 왔다면,
            del NotiList[-1]

# 구글 서비스 초기화
def googleInitiator():

    creds = None
    # token.pickle에 저장된 인증정보가 있다면 로드해 사용.
    if os.path.exists('token.pickle'):
        with open('token.pickle','rb') as token:
            creds = pickle.load(token)
    # 만일 저장된 인증정보가 없거나 유효하지 않다면
    if not creds or not creds.valid:
        # 인증정보가 만료된거라면 refresh()
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        # 저장된정보가 없는것이라면 InstalledAppFlow()를 사용해 인증획득
        else:
            flow = InstalledAppFlow.from_client_secrets_file(GOOGLE_CLIENT_SECRET_JSON_FILE_NAME, SCOPES)
            creds = flow.run_console()
        # 인증 획득했다면 다음에 사용하기 위해 저장
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds,token)


    gmailService = build('gmail','v1', credentials=creds)
    calendarService = build('calendar', 'v3', credentials=creds)
    # GmailChecker와 CalendarChecker 리턴
    return (GmailChecker(gmailService), CalendarChecker(calendarService))

# 메인 스레드
# 시스템을 구성하는 각 컴포넌트를 로딩한 후
# 사용자에 의해 멈추어질때까지 루프를 무한반복하며
# 현재시간을 체크하고 디스플레이를 업데이트 한다.
if __name__ == '__main__':
    # 각 콤포넌트 로딩
    timeChecker = TimeChecker()
    BgImage = bgImageInitiator() #백그라운드 이미지 PIL.Image 객체
    Display = displayInitiator() # oled 디스플레이
    (gmailChecker,calendarChecker) = googleInitiator() # 구글 서비스 초기화
    # 버튼 초기화
    initButtons()

    # 무한반복
    try:
        loopCounter = 0 # 각 checker의 확인 주기를 가각 컨트롤 하기위해 루프 횟수 카운트

        # 시작할 때 모두 한 번씩 체크
        timeChecker.check()
        gmailChecker.check()
        calendarChecker.check()

        while True:
            # 10루프마다 시간 체크
            if loopCounter % 10 is 0:
                timeChecker.check()

            # 500 루프마다 이메일 체크
            if loopCounter % 500 is 0:
                gmailChecker.check()

            # 700 루프마다 캘린더  체크
            if loopCounter % 700 is 0:
                calendarChecker.check()
                # 루프 카운터 리셋
                loopCounter = 0

            loopCounter += 1
            updateDisplay() # 디스플레이 업데이트

    # Ctrl+C 누르면 프로그램 종료
    except KeyboardInterrupt:
        print("System terminated by the User...")
    # 종료시 gpio 인터럽트 정리
    finally:
        GPIO.cleanup()
