import requests
from bs4 import BeautifulSoup
import pandas as pd

# 縣市對應的代碼
county_list = {
    "台北市": 20, "新北市": 21, "桃園市": 33, "台中市": 42, "台南市": 62, "高雄市": 70,
    "基隆市": 24, "新竹市": 35, "新竹縣": 36, "苗栗縣": 37, "彰化縣": 47, "南投縣": 49,
    "雲林縣": 55, "嘉義市": 52, "嘉義縣": 53, "屏東縣": 87, "宜蘭縣": 39, "花蓮縣": 38,
    "臺東縣": 89, "澎湖縣": 69, "金門縣": 82, "連江縣": 83
}

# 定義請求頭
headers = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'Accept-Language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7,zh-CN;q=0.6',
    'Cache-Control': 'no-cache',
    'Connection': 'keep-alive',
    'Cookie': 'JSESSIONID=663BB66D15EF3C63195AB0BFF1FB96E7; TS01c4d517=01f7b49a66796787c43c9e59b36e6d36880cb40a7b00e4d784a32ca3abc02d8dc6a3f7caf02b7819873db84d26af18b7ed2f2d70388d005cc23508058db26cb654f83e3163; JSESSIONID=74003F445228CF52FECF8B9EC88AE69B; TS011605d9=01f7b49a664410f93270fd1a60037e5139abf72cdfad21188366b6477bc00b98c68756dfa6a249c8dd73d46d870e04629000698b8d9ad6afabb06e5891a47c3bdeeaf6bec6; TSaac51d7c027=082900c652ab200018df22bf6a79586e308b6c3484dbedadc17c9f76015aefb00f2c089689a90b13085941f875113000fad928eec78cf83aeddcd8bbb94bd0f2adab6c0054c6da72099560a2c02d88b9dedeac0fa38fc0d283c5b717e2bff3b7',
    'Pragma': 'no-cache',
    'Referer': 'https://bsb.kh.edu.tw/afterschool/register/cancel_list_b.jsp',
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

# 遍歷所有縣市
for county, code in county_list.items():
    # 定義每個縣市的URL
    url = f'https://bsb.kh.edu.tw/afterschool/register/print_cancel_list_b.jsp?pageno=1&citylink=&unit=&c_type=&area=&road=&sn_year=&sn_month=&end_year=&end_month=&city={code}&pnt=2&local='
    
    # 發送請求
    response = requests.get(url, headers=headers)
    response.encoding = 'utf-8'
    
    # 解析HTML內容
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # 提取表格數據
    table = soup.find('table')  # 假設數據在表格中
    if not table:
        print(f"{county}的數據未找到")
        continue

    data = []
    table_headers = [header.text for header in table.find_all('th')]

    for row in table.find_all('tr')[1:]:  # 跳過表頭
        columns = row.find_all('td')
        data.append([column.text.strip() for column in columns])

    # 將數據轉換為DataFrame
    df = pd.DataFrame(data, columns=table_headers)
    
    # 保存為CSV文件
    df.to_csv(f'{county}_cancel_list.csv', index=False, encoding='utf-8-sig')
    
    print(f'{county}的資料已保存為{county}_cancel_list.csv')
