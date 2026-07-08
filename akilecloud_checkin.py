# !/usr/bin/env python
# -*-coding:utf-8 -*-
# -------------------------------
# @Author : github@yuanter https://github.com/yuanter  by院长
# @Time : 2025/06/08 12:25
# const $ = new Env('AkileCloud签到');
# -------------------------------

"""
1. AkileCloud签到 支持多账号执行 脚本仅供学习交流使用, 请在下载后24h内删除
2. 网址：https://akile.io/register?aff_code=7e9eb403-53c2-414a-8963-c5492fa259d0  本脚本需要使用账号密码，请记得设置密码（注意：本脚本使用了&、#和@3个符号，更改密码无需使用这3个符号）
3. 环境变量说明:
    变量名(必须)： AkCloudCK  格式： 账号&密码
    单个CK塞多个账号时，以#或者换行分隔开：CK1#CK2
4、请注意，本脚本使用了青龙auth.json文件内部的token，该token具有时效性，3天有效期。需要3天内保持一次登录青龙，保证token有效期，不然脚本会出错
   可配合自动登录青龙脚本(https://raw.githubusercontent.com/yuanter/misaka/refs/heads/master/login_qinglong.py)，实行自动更新token。安全问题，自行斟酌
wxpusher推送(非必填)
青龙变量：AkCloudCK_WXPUSHER_TOKEN   wxpusher推送的token
青龙变量：AkCloudCK_WXPUSHER_TOPIC_ID   wxpusher推送的topicId
"""
import requests,re
import json, os
import time
from sys import stdout
import random
from datetime import datetime
import logging
import sys
try:
    import cloudscraper
except Exception:
    print(f"❌未安装 cloudscraper 依赖!!!")
    exit(0)
try:
    import sqlite3
except Exception:
    print(f"❌未安装 sqlite3 依赖!!!")
    exit(0)



# 加载通知
def load_send() -> None:
    logging.info("加载推送功能中...")
    global send
    send = None
    cur_path = os.path.abspath(os.path.dirname(__file__))
    sys.path.append(cur_path)
    if os.path.exists(cur_path + "/../notify.py"):
        try:
            from notify import send
        except Exception:
            send = None
            logging.info(f"❌加载通知服务失败!!!\n{traceback.format_exc()}")
    else:
        try:
            from notify import send
        except:
            logging.info(f"❌加载通知服务失败!!!\n")
            print("无法检测到本库中的 notify 依赖，退出程序")
            exit(0)


WXPUSHER_TOKEN = '' # wxpusher推送的token
WXPUSHER_TOPIC_ID = '' # wxpusher推送的topicId
WXPUSHER_CONTENT_TYPE = 2  # wxpusher推送的样式，1表示文字  2表示html(只发送body标签内部的数据即可，不包括body标签)，默认为2
# wxpusher消息推送
def wxpusher(title: str, content: str) -> None:
    """
    使用微信的wxpusher推送
    """
    if not WXPUSHER_TOKEN or not WXPUSHER_TOPIC_ID:
        print("wxpusher 服务的 token 或者 topicId 未设置!!\n取消推送")
        return
    print("wxpusher 服务启动")

    url = f"https://wxpusher.zjiecode.com/api/send/message"
    headers = {"Content-Type": "application/json;charset=utf-8"}
    contentType = 2
    if not WXPUSHER_CONTENT_TYPE:
        contentType = 2
    else:
        contentType = WXPUSHER_CONTENT_TYPE
    if contentType == 2:
        content = content.replace("\n", "<br/>")
    data = {
        "appToken":f"{WXPUSHER_TOKEN}",
        "content":f"{content}",
        "summary":f"{title}",
        "contentType":contentType,
        "topicIds":[
            f'{WXPUSHER_TOPIC_ID}'
        ],
        "verifyPay":False
    }
    response = requests.post(
        url=url, data=json.dumps(data), headers=headers, timeout=15
    ).json()

    if response["code"] == 1000:
        print("wxpusher推送成功！")
    else:
        print("wxpusher推送失败！")
        print(f"wxpusher推送出错响应内容：{response}" )


ql_auth_path = '/ql/data/config/auth.json'
ql_config_path = '/ql/data/config/config.sh'
ql_token_path = '/ql/data/config/token.json'
# 2.20.2之前的版本
ql_url = 'http://localhost:5600'
# 2.20.2之后的版本
# 1. 设置数据库路径 (如果是青龙容器内运行，通常是这个路径)
DB_PATH = '/ql/data/db/keyv.sqlite'

#判断环境变量
flag = 'new'

if not os.path.exists(DB_PATH):
    if not os.path.exists(ql_auth_path):
        ql_config_path = '/ql/config/config.sh'
        ql_auth_path = '/ql/config/auth.json'
        if not os.path.exists(ql_config_path):
            ql_config_path = '/ql/config/config.js'
        flag = 'old'
else:
    ql_url = 'http://localhost:5700'



# 1. 设置数据库路径 (如果是青龙容器内运行，通常是这个路径)
# DB_PATH = '/ql/data/db/keyv.sqlite'

def query_keyv_db():
    if not os.path.exists(DB_PATH):
        print_now(f"❌ 错误: 找不到数据库文件 -> {DB_PATH}")
        print_now("请确认路径是否正确，或者是否已将该文件映射/拷贝到了当前目录。")
        return

    # print_now(f"🔗 正在连接数据库: {DB_PATH}")
    # print_now(f"🔗 正在连接数据库")
    
    try:
        # 2. 连接数据库 (设置 timeout=5，防止青龙后端正在高频读写导致 database is locked)
        with sqlite3.connect(DB_PATH, timeout=5.0) as conn:
            cursor = conn.cursor()

            # 3. 执行 SQL 查询语句
            # keyv 的表名固定为 "keyv"，核心字段为 "key" 和 "value"
            cursor.execute("SELECT key, value FROM keyv")
            rows = cursor.fetchall()

            if not rows:
                print_now("⚠️ 数据库连接成功，但表 'keyv' 中没有任何数据。")
                return

            # print_now(f"✅ 查询成功，共找到 {len(rows)} 条记录:\n")
            # print_now("=" * 60)

            # 4. 遍历并格式化输出数据
            for key, raw_value in rows:
                # print_now(f"🔑 [Key]: {key}")
                if key == "keyv:authInfo":
                    # keyv 库在存入 value 时，通常会将其序列化为 JSON 字符串
                    try:
                        # 尝试解析为字典
                        parsed_value = json.loads(raw_value)
                        value = parsed_value.get("value")
                        token = value.get("token")
                        # # 格式化输出 JSON，使其具备良好的可读性
                        # print_now("📦 [Value] (JSON 格式):")
                        # print_now(json.dumps(parsed_value, indent=4, ensure_ascii=False))
                        
                        # 附加功能：提取出 Token 过期时间或封禁状态
                        if isinstance(parsed_value, dict) and 'expires' in parsed_value:
                            expires_ts = parsed_value.get('expires')
                            if expires_ts:
                                print_now(f"⏱️  [过期时间戳]: {expires_ts}")
                        return token        
                    except json.JSONDecodeError:
                        # 如果解析失败，说明存储的是纯文本或其他格式，直接输出
                        # print_now(f"📄 [Value] (纯文本格式):\n{raw_value}")
                        print_now(f"🔗 数据库解析失败")
                    
                # print_now("-" * 60)


    except sqlite3.OperationalError as e:
        if "no such table" in str(e).lower():
            print_now("❌ 错误: 数据库中不存在 'keyv' 表。这可能不是由 keyv 生成的库。")
        elif "locked" in str(e).lower():
            print_now("❌ 错误: 数据库被锁定 (Database is locked)。青龙后端可能正在进行写入操作，请稍后再试。")
        else:
            print_now(f"❌ SQLite 运行错误: {e}")
    except Exception as e:
        print_now(f"❌ 发生未知异常: {e}")



def __get_token() -> str or None:
    
    if os.path.exists(DB_PATH):
        # 执行查询
        return query_keyv_db()
    else:
        with open(ql_auth_path, 'r', encoding='utf-8') as f:
            j_data = json.load(f)
        return j_data.get('token')


def __get__headers() -> dict:
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json;charset=UTF-8',
        'Authorization': 'Bearer ' + __get_token()
    }
    return headers

# 封装读取环境变量的方法
def get_cookie(key, default="", output=True):
    def no_read():
        if output:
            print_now(f"未填写环境变量 {key} 请添加")
        return default
    return get_cookie_data(key) if get_cookie_data(key) else no_read()

#获取ck
def get_cookie_data(name):
    ck_list = []
    remarks_list = []
    cookie = None
    cookies = get_config_and_envs(name)
    for ck in cookies:
        data_temp = {}
        if ck["name"] != name:
            continue
        if ck.get('status') == 0:
            # ck_list.append(ck.get('value'))
            # 直接添加CK
            ck_list.append(ck)
    if len(ck_list) < 1:
        print('变量{}共配置{}条CK,请添加环境变量,或查看环境变量状态'.format(name,len(ck_list)))
    return ck_list

# 修改print方法 避免某些环境下python执行print 不会去刷新缓存区导致信息第一时间不及时输出
def print_now(content):
    print(content)
    stdout.flush()


# 查询环境变量
def get_envs(name: str = None) -> list:
    params = {
        't': int(time.time() * 1000)
    }
    if name is not None:
        params['searchValue'] = name
    res = requests.get(ql_url + '/api/envs', headers=__get__headers(), params=params)
    j_data = res.json()
    if j_data['code'] == 200:
        return j_data['data']
    return []


# 查询环境变量+config.sh变量
def get_config_and_envs(name: str = None) -> list:
    params = {
        't': int(time.time() * 1000)
    }
    #返回的数据data
    data = []
    if name is not None:
        params['searchValue'] = name
    res = requests.get(ql_url + '/api/envs', headers=__get__headers(), params=params)
    j_data = res.json()
    if j_data['code'] == 200:
        data = j_data['data']
    with open(ql_config_path, 'r', encoding='utf-8') as f:
        while  True:
            # Get next line from file
            line  =  f.readline()
            # If line is empty then end of file reached
            if  not  line  :
                break;
            #print(line.strip())
            exportinfo = line.strip().replace("\"","").replace("\'","")
            #去除注释#行
            rm_str_list = re.findall(r'^#(.+?)', exportinfo,re.DOTALL)
            #print('rm_str_list数据：{}'.format(rm_str_list))
            exportinfolist = []
            if len(rm_str_list) == 1:
                exportinfo = ""
            #list_all = re.findall(r'export[ ](.+?)', exportinfo,re.DOTALL)
            #print('exportinfo数据：{}'.format(exportinfo))
            #以export分隔，字符前面新增标记作为数组0，数组1为后面需要的数据
            list_all = ("标记"+exportinfo.replace(" ","").replace(" ","")).split("export")
            #print('list_all数据：{}'.format(list_all))
            if len(list_all) > 1:
                #以=分割，查找需要的环境名字
                tmp = list_all[1].split("=")
                if len(tmp) > 1:

                    info = tmp[0]
                    if name in info:
                        #print('需要查询的环境数据：{}'.format(tmp))
                        data_tmp = []
                        data_json = {
                            'id': None,
                            'value': tmp[1],
                            'status': 0,
                            'name': name,
                            'remarks': "",
                            'position': None,
                            'timestamp': int(time.time()*1000),
                            'created': int(time.time()*1000)
                        }
                        if flag == 'old':
                            data_json = {
                                '_id': None,
                                'value': tmp[1],
                                'status': 0,
                                'name': name,
                                'remarks': "",
                                'position': None,
                                'timestamp': int(time.time()*1000),
                                'created': int(time.time()*1000)
                            }
                        #print('需要的数据：{}'.format(data_json))
                        data.append(data_json)
        #print('第二次配置数据：{}'.format(data))
    return data


# 新增环境变量
def post_envs(name: str, value: str, remarks: str = None) -> list:
    params = {
        't': int(time.time() * 1000)
    }
    data = [{
        'name': name,
        'value': value
    }]
    if remarks is not None:
        data[0]['remarks'] = remarks
    res = requests.post(ql_url + '/api/envs', headers=__get__headers(), params=params, json=data)
    j_data = res.json()
    if j_data['code'] == 200:
        return j_data['data']
    return []


# 修改环境变量1，青龙2.11.0以下版本（不含2.11.0）
def put_envs_old(_id: str, name: str, value: str, remarks: str = None) -> bool:
    params = {
        't': int(time.time() * 1000)
    }

    data = {
        'name': name,
        'value': value,
        '_id': _id
    }

    if remarks is not None:
        data['remarks'] = remarks
    res = requests.put(ql_url + '/api/envs', headers=__get__headers(), params=params, json=data)
    j_data = res.json()
    if j_data['code'] == 200:
        return True
    return False


# 修改环境变量2，青龙2.11.0以上版本（含2.11.0）
def put_envs_new(_id: int, name: str, value: str, remarks: str = None) -> bool:
    params = {
        't': int(time.time() * 1000)
    }

    data = {
        'name': name,
        'value': value,
        'id': _id
    }

    if remarks is not None:
        data['remarks'] = remarks
    res = requests.put(ql_url + '/api/envs', headers=__get__headers(), params=params, json=data)
    j_data = res.json()
    if j_data['code'] == 200:
        return True
    return False


# 禁用环境变量
def disable_env(_id: str) -> bool:
    params = {
        't': int(time.time() * 1000)
    }
    data = [_id]
    res = requests.put(ql_url + '/api/envs/disable', headers=__get__headers(), params=params, json=data)
    j_data = res.json()
    if j_data['code'] == 200:
        return True
    return False


# 启用环境变量
def enable_env(_id: str) -> bool:
    params = {
        't': int(time.time() * 1000)
    }
    data = [_id]
    res = requests.put(ql_url + '/api/envs/enable', headers=__get__headers(), params=params, json=data)
    j_data = res.json()
    if j_data['code'] == 200:
        return True
    return False

# 删除环境变量
def delete_env(_id: str) -> bool:
    params = {
        't': int(time.time() * 1000)
    }
    data = [_id]
    res = requests.delete(ql_url + '/api/envs', headers=__get__headers(), params=params, json=data)
    j_data = res.json()
    if j_data['code'] == 200:
        return True
    return False


# 获取所有的定时任务详情
def get_crons(name: str = None) -> list:
    params = {
        't': int(time.time() * 1000)
    }
    if name is not None:
        params['searchValue'] = name
    res = requests.get(ql_url + '/api/crons', headers=__get__headers(), params=params)
    j_data = res.json()
    if j_data['code'] == 200:
        if flag == 'old':
            return j_data['data']
        else:
            return j_data['data']['data']
    return []

# 获取指定定时任务详情
def get_crons_by_id(_id: str) -> list:
    # 统一返回队列类型
    result = []
    params = {
        't': int(time.time() * 1000)
    }
    res = requests.get(ql_url + f'/api/crons/{_id}', headers=__get__headers(), params=params)
    j_data = res.json()
    if j_data['code'] == 200:
        return result.append(j_data['data'])
    return []


# 更新任务
def put_crons(_id: str, name: str, labels: str, command: str, schedule: str) -> bool:
    params = {
        't': int(time.time() * 1000)
    }
    data = {
        'labels': labels,
        'command': command,
        'schedule': schedule,
        'name': name,
        'id': _id
    }
    if flag == 'old':
       data = {
        'command': command,
        'schedule': schedule,
        'name': name,
        '_id': _id
        } 
    res = requests.put(ql_url + '/api/crons', headers=__get__headers(), params=params, json=data)
    j_data = res.json()
    if j_data['code'] == 200:
        return True
    return False

# 随机生成比当前时间小的定时任务规则
def generate_past_cron():
    now = datetime.now()
    current_hour = now.hour
    current_minute = now.minute
    
    # 处理无法生成的情况（当前时间为00:00）
    if current_hour == 0 and current_minute == 0:
        return "16 23 * * *"  # 默认返回前一天23:16
    
    # 计算当前时间的总分钟数
    total_minutes = current_hour * 60 + current_minute
    
    # 随机生成过去的时间点（0到总分钟数-1之间）
    random_minutes = random.randint(0, total_minutes - 1)
    random_hour = random_minutes // 60
    random_minute = random_minutes % 60

    current_time = datetime.now().strftime("%H:%M")
    print(f"当前时间: {current_time}")
    print(f"生成新的Cron表达式: {random_minute} {random_hour} * * *")
    print(f"含义: 每天 {random_hour}:{random_minute:02d} 执行")

    # 格式化为cron表达式
    return f"{random_minute} {random_hour} * * *"



# WXPUSHER_TOKEN
WXPUSHER_TOKEN_temp = get_cookie("AkCloudCK_WXPUSHER_TOKEN")
if WXPUSHER_TOKEN_temp != "" and len(WXPUSHER_TOKEN_temp)>0:
    WXPUSHER_TOKEN = WXPUSHER_TOKEN_temp[0]["value"]

# WXPUSHER_TOPIC_ID
WXPUSHER_TOPIC_ID_temp = get_cookie("AkCloudCK_WXPUSHER_TOPIC_ID")
if WXPUSHER_TOPIC_ID_temp != "" and len(WXPUSHER_TOPIC_ID_temp)>0:
    WXPUSHER_TOPIC_ID = WXPUSHER_TOPIC_ID_temp[0]["value"]

msg = ""


headers = headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "TE": "trailers"
}

# 封装过CF页面
def goCF(url,body,headers,method="get"):
    scraper = cloudscraper.create_scraper(
        delay=10,
        interpreter='nodejs',
        browser={
            'browser': 'chrome',
            'platform': 'windows',
            'desktop': True
        }
    )
    if method == "get":
        response = scraper.get(url, headers=headers)
        # print_now(f"获取验证后内容：{response.text}")  # 获取验证后内容
        return response
    else:
        response = scraper.post(url, headers=headers, json=body)
        # print_now(f"获取验证后内容：{response.text}")  # 获取验证后内容
        return response


# 登录
def get_token(ck):
    value = ck["value"]
    remarks = ck["remarks"]
    split = value.split("&")
    
    if not split or len(split)<2:
        print_now(f"提交的账号格式错误: {value} (应为 邮箱&密码)")
        return

    url = 'https://api.akile.io/api/v1/user/login'

    
    # {"email":"xxxxxxx@qq.com","password":"xxxxxxx","token":"","verifyCode":"","remember":true}
    LOGIN_DATA = {
        'email': split[0],
        'password': split[1],
        'token': '',
        'verifyCode': '',
        'remember': True
    }
    
    try:
        response = goCF(url, LOGIN_DATA, headers, method="post")
        response_data = response.json()
        if response_data['status_code'] == 0:
            print_now(f"【{remarks}】{response_data['status_msg']}")
        TOKEN = response_data['data']['token']
        return TOKEN
    except Exception as e:
        print_now(f"【{remarks}】登录出错，Error: {e}\n")
        return None

# 获取用户信息，返回对象
def get_userinfo(token):
    headers['authorization'] = token
    url= 'https://api.akile.io/api/v1/user/info'
    try:
        # response = requests.get(url, headers=headers)
        response = goCF(url, None, headers)
        response_data = response.json()
        # data = response_data["data"]
        # print_now(f'{data["username"]}你好')
        return response_data
    except Exception as e:
        print_now(f"获取个人信息出错，Error: {e}\n")
        return None

# 获取首页，包括ak币值，返回对象
def get_index(token):
    headers['authorization'] = token
    url= 'https://api.akile.io/api/v1/user/index'
    try:
        # response = requests.get(url, headers=headers)
        response = goCF(url, None, headers)
        response_data = response.json()
        # data = response_data["data"]
        return response_data
    except Exception as e:
        print_now(f"获取ak币出错，Error: {e}\n")
        return None

# 签到
def sign_in(token):
    headers['authorization'] = token
    url= 'https://api.akile.io/api/v1/user/Checkin'
    try:
        # response = requests.get(url, headers=headers)
        response = goCF(url, None, headers)
        response_data = response.json()
        # data = response_data["data"]
        return response_data
    except Exception as e:
        print_now(f"签到出错，Error: {e}\n")
        return None


def getup(ck,token):
    global msg
    value = ck["value"]
    remarks = ck["remarks"]
    split = value.split("&")
    if not split or len(split)<2:
        print_now(f"提交的账号:{value}不对")
        return
    headers['authorization'] = token
    # 获取用户名
    user_info = get_userinfo(token)
    if user_info is None:
        print_now(f'【{remarks}】账号登录出错：执行下一个任务')
        return
    if user_info['status_code'] != 0:
        print_now(f"user_info['status_msg']\n执行下一个任务")
        return
    # 获取ak币
    index_info = get_index(token)
    # 签到
    sign_data = sign_in(token)
    if sign_data['status_code'] == 0:
        print_now(f"备注：{remarks}，用户名：{user_info['data']['username']}，签到状态：{sign_data['status_msg']}，账户总AK币：{sign_data['data']}，本次签到获得AK币：{sign_data['data']-index_info['data']['ak_coin']}")
        msg += f"【{time.strftime('%Y-%m-%d %H:%M:%S')}】 ---- 【{remarks}】，用户名：{user_info['data']['username']}，签到前AK币：{index_info['data']['ak_coin']}----------签到后Ak币：{sign_data['data']}，本次签到获得AK币：{sign_data['data']-index_info['data']['ak_coin']}\n\n"
    else:
        print_now(f"【{remarks}】，用户名：{user_info['data']['username']}，总Ak币：{index_info['data']['ak_coin']}----------{sign_data['status_msg']}")
        msg += f"【{time.strftime('%Y-%m-%d %H:%M:%S')}】 ---- 【{remarks}】，用户名：{user_info['data']['username']}，总Ak币：{index_info['data']['ak_coin']}----------{sign_data['status_msg']}\n\n"


# 根据当前文件随机改变定时任务时间
def random_time():
    print_now("执行更改定时任务表达式")
    cron_details = None
    script_path = os.path.abspath(__file__)  # 转为绝对路径
    # print_now(f"脚本绝对路径: {script_path}")    # 示例脚本绝对路径: /ql/data/scripts/yuanter_hw/akilecloud_checkin.py
    # script_name = os.path.basename(script_path)     # 文件名: main.py
    # 获取所有任务的脚本路径
    crons_data = get_crons()
    
    for i in range(len(crons_data)): 
        
        script_path_temp = crons_data[i].get("command").split(" ")[1]
        if script_path_temp in script_path:
            # 获取当前的任务详情
            cron_details = crons_data[i]
            if cron_details is not None:
                _id = None
                if flag == 'new':
                    _id = cron_details["id"]
                else:
                    _id = cron_details["_id"]
                schedule = generate_past_cron()
                # 修改任务
                if put_crons(_id, cron_details.get("name"), cron_details.get("labels"), cron_details.get("command"), schedule):
                    print_now(f"生成新的定时任务成功。旧表达式：{cron_details['schedule']} ，新的表达式：{schedule}")
                else:
                    print_now(f'生成新的定时任务出错了')
            # 结束
            break
    



if __name__ == "__main__":
    # 加载通知
    load_send()

    l = []
    ck_list = []
    cklist = get_cookie("AkCloudCK")
    for i in range(len(cklist)):
        #多账号以#分割开的ck
        split1 = cklist[i]['value'].split("\n")
        #多账号以@分割开的ck
        split2 = cklist[i]['value'].split("#")
        #多账号以换行\n分割开的ck
        split3 = cklist[i]['value'].split("@")
        remarks = cklist[i].get("remarks",None)
        if len(split1)>1:
            for j in range(len(split1)):
                info = {}
                info['value'] = split1[j]
                if remarks is None:
                    info['remarks'] = split1[j]
                else:
                    info['remarks'] = remarks
                ck_list.append(info)
        elif len(split2)>1:
            for j in range(len(split2)):
                info = {}
                info['value'] = split2[j]
                if remarks is None:
                    info['remarks'] = split2[j]
                else:
                    info['remarks'] = remarks
                ck_list.append(info)
        # elif len(split3)>1:
        #     for j in range(len(split3)):
        #         info = {}
        #         info['value'] = split3[j]
        #         if remarks is None:
        #             info['remarks'] = split3[j]
        #         else:
        #             info['remarks'] = remarks
        #         ck_list.append(info)
        else:
            if remarks is None:
                cklist[i]['remarks'] = cklist[i]['value']
            ck_list.append(cklist[i])
    if len(ck_list)<1:
        print_now('未添加CK,退出程序~')
        exit(0)



    for i in range(len(ck_list)):
        ck = ck_list[i]
        print_now(f'开始执行第 {i+1} 个账号')
        if ck is None or ck["value"] is None or len(ck["value"].split("&"))<2:
            print_now("当前账号未填写 跳过\n")
            continue
        token = get_token(ck)
        if token is None:
            continue
        getup(ck,token)
        print_now("\n")
    if WXPUSHER_TOKEN != "" and WXPUSHER_TOPIC_ID != "" and msg != "":
        wxpusher("AkileCloud签到",msg)
    random_time()
    send('AkileCloud签到', msg)

