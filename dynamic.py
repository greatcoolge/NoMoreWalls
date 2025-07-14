#!/usr/bin/env python3
import re
import datetime
import requests
import threading
from typing import Set
from fetch import raw2fastly, session, LOCAL
from bs4 import BeautifulSoup
import datetime as dt
from typing import Optional

# def kkzui():
#     if LOCAL: return
#     res = session.get("https://kkzui.com/jd?orderby=modified")
#     article_url = re.search(r'<a href="(https://kkzui.com/(.*?)\.html)" title="20(.*?)节点(.*?)</a>',res.text).groups()[0]
#     res = session.get(article_url)
#     passwd = re.search(r'<strong>本期密码：(.*?)</strong>',res.text).groups()[0]
#     res = session.post(article_url, data={'secret-key': passwd})
#     sub = res.text.split('<pre')[1].split('</pre>')[0]
#     if '</' in sub:
#         sub = sub.split('</')[-2]
#     if '>' in sub:
#         sub = sub.split('>')[-1]
#     return sub


session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
})

# ---------------- 辅助函数：从标题提取日期 ---------------- #
def extract_date_from_title(title: str) -> Optional[dt.datetime]:
    patterns = [
        r'(\d{4})年(\d{1,2})月(\d{1,2})日',    # 2025年07月14日
        r'(\d{4})(\d{2})(\d{2})',            # 20250714
        r'(\d{1,2})月(\d{1,2})日',            # 7月14日  → 默认当年
    ]
    for pat in patterns:
        m = re.search(pat, title)
        if m:
            try:
                if len(m.groups()) == 3:
                    g = list(map(int, m.groups()))
                    # 若只有“月日”，补当前年份
                    if g[0] <= 31:                         # 命中 ③ 格式
                        y = dt.datetime.now().year
                        mth, d = g[0], g[1]
                    else:                                  # 命中 ①② 格式
                        y, mth, d = g
                    return dt.datetime(y, mth, d)
            except Exception:
                pass
    return None

# ---------------- 主函数：返回最新“节点”文章链接 ---------------- #
def fetch_latest_cfmem_article() -> str:
    base_url = "https://www.cfmem.com/"
    res = session.get(base_url)
    soup = BeautifulSoup(res.text, 'html.parser')

    link_pattern  = re.compile(r"https://www\.cfmem\.com/\d{4}/\d{2}/[a-z0-9\-]+\.html")
    url_date_pat  = re.compile(r"(\d{8})")  # 直接从 slug 抓 8 位日期

    candidates = []   # [(date_obj, href)]

    for a in soup.find_all("a", href=True):
        href  = a["href"]
        title = a.get_text(strip=True)

        if not (link_pattern.match(href) and "节点" in title):
            continue

        # ① 先尝试从 URL 获取日期
        m = url_date_pat.search(href)
        date_obj = None
def fetch_cfmem():
    base_url = "https://www.cfmem.com/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    }

    # 访问首页
    res = session.get(base_url, headers=headers)
    soup = BeautifulSoup(res.text, 'html.parser')

    # 查找包含“节点”的文章链接（支持 2025/07/xxx.html 格式）
    article_url = None
    for a in soup.find_all("a", href=True):
        href = a["href"]
        title = a.get_text(strip=True)
        if (
            re.match(r"https://www\.cfmem\.com/\d{4}/\d{2}/[a-z0-9\-]+\.html", href)
            and "节点" in title
        ):
            article_url = href
            break


def sharkdoor():
    res_json = session.get(datetime.datetime.now().strftime(
        'https://api.github.com/repos/sharkDoor/vpn-free-nodes/contents/node-list/%Y-%m?ref=master')).json()
    res = session.get(raw2fastly(res_json[-1]['download_url']))
    nodes: Set[str] = set()
    for line in res.text.split('\n'):
        if '://' in line:
            nodes.add(line.split('|')[-2])
    return nodes

def changfengoss():
    # Unused
    res = session.get(datetime.datetime.now().strftime(
        "https://api.github.com/repos/changfengoss/pub/contents/data/%Y_%m_%d?ref=main")).json()
    return [_['download_url'] for _ in res]

def vpn_fail():
    # The site has been closed
    # if LOCAL: return
    response = session.get("https://vpn.fail/free-proxy/type/v2ray").text
    lines = re.findall(r'<article(.*?)</article', response, re.DOTALL)
    links = set()
    ips = set()
    for line in lines:
        result = re.search(r'<span>(\d+)%</span>', line)
        if result and result.group(1) == '100':
            ips.add(re.search(r'<a href="https://vpn\.fail/free-proxy/ip/(.*?)" style=', line).group(1))

    def get_link(ip: str) -> None:
        try:
            response = session.get(f"https://vpn.fail/free-proxy/ip/{ip}").text
            link = response.split('class="form-control text-center" id="pp2" value="')[1].split('"')[0]
            links.add(link)
        except requests.exceptions.RequestException:
            pass

    threads = [threading.Thread(target=get_link, args=(ip,)) for ip in ips]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    return links
      
def w1770946466():
    if LOCAL: return
    res = session.get(raw2fastly("https://raw.githubusercontent.com/w1770946466/Auto_proxy/main/README.md")).text
    subs: Set[str] = set()
    for line in res.strip().split('\n'):
        if line.startswith("`http"):
            sub = line.strip().strip('`')
            if not sub.startswith("https://raw.githubusercontent.com"):
                subs.add(sub)
    return subs

def peasoft():
    return session.get("https://gist.githubusercontent.com/peasoft/8a0613b7a2be881d1b793a6bb7536281/raw/417c1d6a75a53d6c197448762e7c97852d34787f/-").text

AUTOURLS = []
AUTOFETCH = [vpn_fail, sharkdoor, fetch_latest_cfmem_article]

if __name__ == '__main__':
    print("URL 抓取："+', '.join([_.__name__ for _ in AUTOURLS]))
    print("内容抓取："+', '.join([_.__name__ for _ in AUTOFETCH]))
    import code
    code.interact(banner='', exitmsg='', local=globals())
