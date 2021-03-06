import datetime as dt
import time
import threading

import requests
import yaml
from bs4 import BeautifulSoup

NEED_BEFORE = True  # 如需补报则置为True，否则False
MONTHS = [10, 11]  # 补报的月份，默认10月、11月


# 获取东八区时间
def get_time():
    # 获取0时区时间，变换为东八区时间
    # 原因：运行程序的服务器所处时区不确定
    t = dt.datetime.utcnow()
    t = t + dt.timedelta(hours=8)

    # 或者：
    # t = dt.datetime.utcnow()
    # tz_utc_8 = dt.timezone(dt.timedelta(hours=8))
    # t = t.astimezone(tz_utc_8)

    # 如果服务器位于东八区，也可用：
    # t = dt.datetime.now()

    return t


def login(username, password):
    sess = requests.Session()
    while True:
        try:
            r = sess.get('https://selfreport.shu.edu.cn/Default.aspx')
            sess.post(r.url, data={
                'username': username,
                'password': password
            })
            sess.get('https://newsso.shu.edu.cn/oauth/authorize?response_type=code&client_id=WUHWfrntnWYHZfzQ5QvXUCVy&redirect_uri=https%3a%2f%2fselfreport.shu.edu.cn%2fLoginSSO.aspx%3fReturnUrl%3d%252fDefault.aspx&scope=1')
        except Exception as e:
            print(e)
            continue
        break

    url = f'https://selfreport.shu.edu.cn/XueSFX/HalfdayReport.aspx?day=2020-11-21&t=1'
    while True:
        try:
            r = sess.get(url)
        except Exception as e:
            print(e)
            continue
        break

    soup = BeautifulSoup(r.text, 'html.parser')
    view_state = soup.find('input', attrs={'name': '__VIEWSTATE'})

    if view_state is None:
        print(f'{username} 登录失败')
        print(r.text)
        return

    print(f'{username} 登录成功')

    return sess


def report(sess, t, temperature=37):
    ii = '1' if t.hour < 20 else '2'
    url = f'https://selfreport.shu.edu.cn/XueSFX/HalfdayReport.aspx?day={t.year}-{t.month}-{t.day}&t={ii}'
    while True:
        try:
            r = sess.get(url)
        except Exception as e:
            print(e)
            continue
        break

    soup = BeautifulSoup(r.text, 'html.parser')
    view_state = soup.find('input', attrs={'name': '__VIEWSTATE'})

    if view_state is None:
        print(r.text)
        return False

    r = sess.post(url, data={
        '__EVENTTARGET': 'p1$ctl00$btnSubmit',
        '__VIEWSTATE': view_state['value'],
        '__VIEWSTATEGENERATOR': 'DC4D08A3',
        'p1$ChengNuo': 'p1_ChengNuo',
        'p1$BaoSRQ': t.strftime('%Y-%m-%d'),
        'p1$DangQSTZK': '良好',
        'p1$TiWen': str(temperature),
        'p1$SuiSM': '绿色',
        'p1$ShiFJC': ['早餐', '午餐', '晚餐'],
        'F_TARGET': 'p1_ctl00_btnSubmit',
        'p1_Collapsed': 'false',
    }, headers={
        'X-Requested-With': 'XMLHttpRequest',
        'X-FineUI-Ajax': 'true'
    }, allow_redirects=False)

    if '提交成功' or '历史信息不能修改' in r.text:
        print(f'{t} 提交成功')
        return True
    else:
        print(r.text)
        return False


with open('config.yaml', encoding='utf8') as f:
    config = yaml.load(f, Loader=yaml.FullLoader)
last_login_time = 0
user_login_status = {user: {'sess': None, 'has_before': False} for user in config}

while True:
    for user in config:
        print(f'======{user}======')
        if user_login_status[user]['sess'] is None:
            if time.time() - last_login_time > 60:
                user_login_status[user]['sess'] = login(user, config[user]['pwd'])
                last_login_time = time.time()
            else:
                print('等待登录')

        sess = user_login_status[user]['sess']
        if sess:
            if NEED_BEFORE and not user_login_status[user]['has_before']:
                for month in MONTHS:
                    for day in range(1, 32):
                        for hour in [9, 21]:
                            try:
                                t = dt.datetime(2020, month, day, hour)
                            except ValueError:
                                continue

                            if not report(sess, t):
                                user_login_status[user]['sess'] = None
                                user_login_status[user]['has_before'] = False
                                break
                            else:
                                user_login_status[user]['has_before'] = True

            t = get_time()
            if not report(sess, t):
                user_login_status[user]['sess'] = None

    time.sleep(60)
