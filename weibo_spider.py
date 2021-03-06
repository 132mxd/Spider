import time
from functools import partial
import pandas as pd
import csv
import os
import re
import requests
from lxml import etree
import random
from datetime import datetime
from datetime import timedelta
from multiprocessing import Process, Lock, Queue,Pool

# 收集到的常用Header
my_headers = [
    "Mozilla/5.0 (Windows NT 6.3; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.153 Safari/537.36",
    "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:30.0) Gecko/20100101 Firefox/30.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_2) AppleWebKit/537.75.14 (KHTML, like Gecko) Version/7.0.3 Safari/537.75.14",
    "Mozilla/5.0 (compatible; MSIE 10.0; Windows NT 6.2; Win64; x64; Trident/6.0)",
    'Mozilla/5.0 (Windows; U; Windows NT 5.1; it; rv:1.8.1.11) Gecko/20071127 Firefox/2.0.0.11',
    'Opera/9.25 (Windows NT 5.1; U; en)',
    'Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1; .NET CLR 1.1.4322; .NET CLR 2.0.50727)',
    'Mozilla/5.0 (compatible; Konqueror/3.5; Linux) KHTML/3.5.5 (like Gecko) (Kubuntu)',
    'Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.8.0.12) Gecko/20070731 Ubuntu/dapper-security Firefox/1.5.0.12',
    'Lynx/2.8.5rel.1 libwww-FM/2.14 SSL-MM/1.4.1 GNUTLS/1.2.9',
    "Mozilla/5.0 (X11; Linux i686) AppleWebKit/535.7 (KHTML, like Gecko) Ubuntu/11.04 Chromium/16.0.912.77 Chrome/16.0.912.77 Safari/535.7",
    "Mozilla/5.0 (X11; Ubuntu; Linux i686; rv:10.0) Gecko/20100101 Firefox/10.0 "
]
startTime = time.time()  # 记录起始时间
cookie = {"Cookie": " _T_WM=49784700768; SCF=Ag67Gx778iNJeLhI0fQcXEUY320VEF9Jx_nrW8NXvSDrea8TsfJKQ7194b3M1wgTwh0gH0TAltMXLM5adHcr1hs.; "
                    "ALF=1598946172; "
                    "SUB=_2A25yIsZ1DeRhGeNJ7FAX9SvIyDSIHXVR7Oo9rDV6PUJbkdAKLUfbkW1NS77s2W2EdPEnjwukTCZAtEJ7bH_rVEo-; "
                    "SUHB=0TPVvR5U0j28MS; "
                    "SSOLoginState=1596372517; "
                    "M_WEIBOCN_PARAMS=oid%3D4533141312897599"}

def RandomUserAgent():
    header = {'User-Agent': random.choice(my_headers)}
    return header

def get_contents(url):
    #只爬取原创微博
    # 禁用安全请求警告
    requests.packages.urllib3.disable_warnings()
    headers = random.choice(my_headers)
    html = requests.get(url, cookies=cookie, verify=False, headers=RandomUserAgent()).content
    html_selector = etree.HTML(html)
    try:
        pageNum = (int)(html_selector.xpath('//input[@name="mp"]')[0].attrib['value'])
        print(pageNum)
    except IndexError as e:
        print ("微博只有一页")
        pageNum=1
    # 微博爬取数量
    crawl_num = 1
    info_list=[]

    for page in range(1,pageNum+1):
        # 获取lxml页面
        url_new=url+"&page="+(str)(page)
        print(f'第{page}页的url:{url_new}')
        lxml = requests.get(url_new, cookies=cookie, verify=False, headers=RandomUserAgent()).content
        selector = etree.HTML(lxml)

        weibos=selector.xpath('//div[@class="c" and @id]')
        for weibo in weibos:
            print(f'第{crawl_num}条微博正爬取中。。。')
            weibo_idinfo=str(weibo.xpath('@id')[0])
            weibo_id=weibo_idinfo.split('_')[-1]

            content_info=weibo.xpath('.//span[@class="ctt"]/..')
            content=content_info[0].xpath('string(.)')
            content=''.join(content.split())

            create_timeinfo=weibo.xpath('.//span[@class="ct"]/text()')[-1]
            create_time=create_timeinfo.split('来自')[0].strip()
            create_time=time_fix(create_time)

            likeinfo=weibo.xpath('.//a[contains(text(),"赞[")]/text()')[-1]
            like_num=int(re.search('\d+',likeinfo).group())

            commentinfo = weibo.xpath('.//a[@class="cc"]/text()')[-1]
            comment_num=int(re.search('\d+',commentinfo).group())
            crawl_num=crawl_num+1
            info_list.append([weibo_id,content,create_time,like_num,comment_num])
    print("所有微博正文信息爬取完毕Done!")
    return info_list

# path=os.getcwd() + "/weiboContents.csv"
def save(path,list):
    with open(path, 'a', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerows(list)
    print('Save Done!')

# 爬取每条微博后，爬取该微博的评论https://weibo.cn/comment/hot/JbtrV9xmX?rl=2&oid=4533141312897599
def get_comments(weibo_id,c_url):
    # 禁用安全请求警告
    requests.packages.urllib3.disable_warnings()
    html = requests.get(c_url, cookies=cookie, verify=False, headers=RandomUserAgent()).content
    html_selector = etree.HTML(html)
    try:
        c_pageNum = (int)(html_selector.xpath('//input[@name="mp"]')[0].attrib['value'])
        print(f'该条微博有{c_pageNum}页评论')
    except IndexError as e:
        print ("评论只有一页")
        c_pageNum=1

    crawl_num = 1
    c_info_list=[]
    for page in range(1,c_pageNum+1):
        if page>51:
            break
        # 获取lxml页面
        url_new=c_url+"&page="+(str)(page)
        print(f'{weibo_id}第{page}页评论的url:{url_new}')
        lxml = requests.get(url_new, cookies=cookie, verify=False, headers=RandomUserAgent()).content
        selector = etree.HTML(lxml)

        comments=selector.xpath('//div[@class="c" and @id]')
        if comments:
            # 存在即为真
            for comment in comments:
                print(f'{weibo_id}第{crawl_num}条评论正爬取中...')

                c_content=comment.xpath('.//span[@class="ctt"]/text()')
                if len(c_content) == 0:
                    break
                else:
                    c_content=c_content[0]

                    uid = comment.xpath('.//a[contains(text(),"举报")]/@href')[0]
                    uid = re.findall("\d+", uid)[1]

                    c_create_timeinfo=comment.xpath('.//span[@class="ct"]/text()')[-1]
                    c_create_time=c_create_timeinfo.split('来自')[0].strip()
                    c_create_time = time_fix(c_create_time)

                    c_likeinfo = comment.xpath('.//a[contains(text(),"赞[")]/text()')[-1]
                    c_like_num=int(re.search('\d+',c_likeinfo).group())

                    crawl_num=crawl_num+1
                    c_info_list.append([weibo_id,uid,c_content,c_create_time,c_like_num])
        else:
            # list为空
            print(f'{id}无评论')
    print("该条微博评论爬取已完成！")
    return c_info_list

# 通过用户ID获取用户信息
def get_user_info(id):
    # 通过用户ID获取用户信息
    def get_user_info(id):
        # 禁用安全请求警告
        path = os.getcwd() + "/weiboUserInfo.csv"
        requests.packages.urllib3.disable_warnings()
        userinfo = []
        u_url = f'https://weibo.cn/{id}/info'
        lxml = requests.get(u_url, cookies=cookie, verify=False, headers=RandomUserAgent()).content
        selector = etree.HTML(lxml)
        allinfo = selector.xpath('//div[@class="c"]//text()')  # 获取标签里的所有text()
        # print(allinfo)
        info_text = ";".join(allinfo)
        gender = re.findall('性别;?[：:]?(.*?);', info_text)
        birthday = re.findall('生日;?[：:]?(.*?);', info_text)
        place = re.findall('地区;?[：:]?(.*?);', info_text)
        authenticated = re.findall('认证;?:?(.*?);', info_text)
        userinfo.append([id, gender, birthday, place, authenticated])
        lock.acquire()  # 添加锁
        with open(path, 'a', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerows(userinfo)
        print('Save Done!')
        lock.release()  # 释放锁
        time.sleep(1)

# 删除完全重复的行
def drop_dup(path):
    frame = pd.read_csv(path, engine='python', encoding='utf-8-sig', index_col=0)
    frame.drop_duplicates(keep='first', inplace=True)
    frame.to_csv(path, encoding='utf-8-sig')
# 发布时间处理为标准格式
def time_fix(publish_time):
    if "刚刚" in publish_time:
        publish_time=datetime.now().strftime('%Y-%m-%d %H:%M')
    elif "分钟" in publish_time:
        minute = publish_time[:publish_time.find("分钟")]
        minute = timedelta(minutes=int(minute))
        publish_time = (
                datetime.now() - minute).strftime(
            "%Y-%m-%d %H:%M")
    elif "今天" in publish_time:
        today = datetime.now().strftime("%Y-%m-%d")
        time = publish_time.replace('今天', '')
        publish_time = today + " " + time
    elif "月" in publish_time:
        year = datetime.now().strftime("%Y")
        publish_time = str(publish_time)
        publish_time = year + "-" + publish_time.replace('月', '-').replace('日', '')
    else:
        publish_time = publish_time[:16]
    return publish_time
def init(l):
    global lock #定义lock为全局变量，供所有进程用
    lock = l
if __name__ == '__main__':
    # 人民日报2803301701人民网2286908003
    # 天山网2803301701
    # 头条新闻1618051664
    # 新浪新闻2028810631
    # 中国新闻网1784473157
    home_url='https://weibo.cn/1784473157/profile?keyword=新疆疫情&hasori=0&haspic=0&starttime=20200713&endtime=20200808&advancedfilter=1&oid=4533141312897599'
    # https://weibo.cn/2803301701/search?f=u&rl=1&hasori=0&haspic=0&starttime=20200713&endtime=20200808&keyword=%E6%96%B0%E7%96%86%E7%96%AB%E6%83%85&oid=4533141312897599
    contentlist=get_contents(home_url)

    content_path=os.getcwd() + "/weiboContents.csv"
    comment_path=os.getcwd() + "/weiboComments.csv"
    user_path = os.getcwd() + "/weiboUserInfo.csv"
    with open(content_path, 'a', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        # csv头部
        writer.writerow(('微博ID', '微博内容', '发布时间','微博点赞数','评论数'))
    save(content_path,contentlist)

    with open(comment_path, 'a', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        # csv头部
        writer.writerow(('微博ID', '用户ID','评论内容', '发布时间', '评论点赞数'))
    with open(user_path, 'a', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        # csv头部
        writer.writerow(('用户ID', '性别', '出生日期', '地址', '认证用户'))

    weibo_ids=[i[0] for i in contentlist]
    count=1
    comments_list=[]
    for id in weibo_ids:
        comment_url = f'https://weibo.cn/comment/hot/{id}?rl=2&oid=4533141312897599'
        comments_list = get_comments(id,comment_url)
        save(comment_path, comments_list)
        print(f'第{count}条微博的评论爬取完毕，还有{len(weibo_ids)-count}条微博的评论需要爬取...')
        count=count+1
    # drop_dup(comment_path)
    # 爬取用户信息
    print("----------------------------------------------------------")
    # with open(comment_path, 'r', encoding='utf-8-sig') as csvfile:
    #     reader = csv.reader(csvfile)
    #     column = [row[1] for row in reader]
    # ids_list = list(set(column[1:]))
    # print('开始获取每条评论用户信息...' + f'共有{len(ids_list)}个用户')
    # count = 1
    # for id in ids_list:
    #     # print(get_user_info(id))
    #     save(user_path, (get_user_info(id)))
    #     print(f'第{count}个用户信息爬取完毕，还有{len(ids_list) - count}个用户信息需要爬取...')
    #     count = count + 1
    # print(f'已获取{len(ids_list)}个用户信息')
    with open(user_path, 'a', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        # csv头部
        writer.writerow(('用户ID', '性别', '出生日期', '地址', '认证用户'))
    lock=Lock()
    pool = Pool(processes=5, initializer=init, initargs=(lock,))  # 设定进程数为20
    with open(comment_path, 'r', encoding='utf-8-sig') as csvfile:
        reader = csv.reader(csvfile)
        column = [row[1] for row in reader]
    ids_list = list(set(column[1:]))
    print('开始获取每条评论用户信息...' + f'共有{len(ids_list)}个用户')
    count = 1
    pool.map(partial(get_user_info),ids_list)
    pool.close()        # 关闭进程池，不再接受新的进程
    pool.join()         # 主进程阻塞等待子进程的退出
    print(f'已获取{len(ids_list)}个用户信息')

    # 计算使用时间
    endTime = time.time()
    useTime = (endTime - startTime) / 60
    print("该次所获的信息一共使用%s分钟" % useTime)
