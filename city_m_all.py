import requests
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime

# 定義全域變數來控制篩選日期
START_DATE = '2023-12'

def fetch_data(session, url, headers):
    response = session.get(url, headers=headers)
    response.encoding = 'utf-8'
    soup = BeautifulSoup(response.text, 'html.parser')
    table = soup.find('table', {'border': '1'})
    if table is None:
        print(f"未能找到表格: {url}")
        return None, None
    rows = table.find_all('tr')
    data = []
    headers = [th.text.strip() for th in rows[0].find_all('th')]
    for row in rows[1:]:
        cols = row.find_all('td')
        cols = [col.text.strip() for col in cols]
        data.append(cols)
    return headers, data

def fetch_additional_data(session, url, headers):
    response = session.get(url, headers=headers)
    response.encoding = 'utf-8'
    additional_data = response.json()
    return additional_data

def filter_recent_data(headers, data, date_column, start_date):
    filtered_data = []
    start_date = datetime.strptime(start_date, '%Y-%m')
    for row in data:
        date_str = row[headers.index(date_column)]
        try:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            if date_obj >= start_date:
                filtered_data.append(row)
        except ValueError:
            continue
    return filtered_data

base_url = "https://bsb.kh.edu.tw/"
city_url = "https://bsb.kh.edu.tw/afterschool/?usercity={}"
data_url_template = "https://bsb.kh.edu.tw/afterschool/register/print_showpage.jsp?pageno=1&p_road=&p_name=&e_name=&p_area=&p_type=&di=&estab=&start_year=&start_month=&start_day=&end_year=&end_month=&end_day=&p_range=on&citylink={}&pnt=2"
additional_data_url_template = "https://bsb.kh.edu.tw/afterschool/opendata/afterschool_json.jsp?city={}"

county_list = {
    "台北市": 20, "新北市": 21, "桃園市": 33, "台中市": 42, "台南市": 62, "高雄市": 70,
    "基隆市": 24, "新竹市": 35, "新竹縣": 36, "苗栗縣": 37, "彰化縣": 47, "南投縣": 49,
    "雲林縣": 55, "嘉義市": 52, "嘉義縣": 53, "屏東縣": 87, "宜蘭縣": 39, "花蓮縣": 38,
    "臺東縣": 89, "澎湖縣": 69, "金門縣": 82, "連江縣": 83
}

headers = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'Accept-Language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7,zh-CN;q=0.6',
    'Cache-Control': 'no-cache',
    'Connection': 'keep-alive',
    'Pragma': 'no-cache',
    'Referer': 'https://bsb.kh.edu.tw/afterschool/index-r.jsp',
    'Sec-Fetch-Dest': 'frame',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'same-origin',
    'Sec-Fetch-User': '?1',
    'Upgrade-Insecure-Requests': '1',
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
    'sec-ch-ua': '"Not/A)Brand";v="8", "Chromium";v="126", "Google Chrome";v="126"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"macOS"',
}

session = requests.Session()
session.get(base_url, headers=headers)

all_data = []

for county, code in county_list.items():
    session.get(city_url.format(code), headers=headers)
    url = data_url_template.format(code)
    page_headers, data = fetch_data(session, url, headers)
    additional_url = additional_data_url_template.format(code)
    additional_data = fetch_additional_data(session, additional_url, headers)
    
    if data:
        filtered_data = filter_recent_data(page_headers, data, '立案日期', START_DATE)
        df = pd.DataFrame(filtered_data, columns=page_headers)
        additional_df = pd.DataFrame(additional_data)
        
        df = df.merge(additional_df[['短期補習班名稱', '電子郵件', '短期補習班類別', '地區縣市']],
                      left_on='補習班名稱', right_on='短期補習班名稱', how='left').drop(columns=['短期補習班名稱'])
        
        all_data.append(df)
    else:
        print(f"未能抓取到資料: {county}")

if all_data:
    combined_df = pd.concat(all_data, ignore_index=True)
    combined_df.to_csv('combined_data.csv', index=False, encoding='utf-8-sig', quotechar='"', sep=';')
    print("所有資料已成功抓取並合併為 combined_data.csv")
else:
    print("未能抓取到任何資料")

