import requests
from bs4 import BeautifulSoup
import math
import time
import csv
import re
import os
import urllib3

# 關閉 SSL 警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 設定
BASE_URL = "https://bsb.kh.edu.tw/"
SHOWPAGE_URL = "https://bsb.kh.edu.tw/showpage.jsp"
DETAIL_URL = "https://bsb.kh.edu.tw/detail.jsp"

# 輸出檔案
FILE_SCHOOLS = "schools.csv"
FILE_SUBJECTS = "subjects.csv"
FILE_VEHICLES = "vehicles.csv"

# 參考 backup/get.py 的完整 Headers
HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'Accept-Language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7,zh-CN;q=0.6',
    'Cache-Control': 'no-cache',
    'Connection': 'keep-alive',
    'Pragma': 'no-cache',
    'Referer': 'https://bsb.kh.edu.tw/afterschool/index-r.jsp',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'same-origin',
    'Sec-Fetch-User': '?1',
    'Upgrade-Insecure-Requests': '1',
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
    'sec-ch-ua': '"Not/A)Brand";v="8", "Chromium";v="126", "Google Chrome";v="126"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"macOS"',
}

def get_session():
    """建立並初始化 Session"""
    session = requests.Session()
    try:
        session.get(BASE_URL, headers=HEADERS, verify=False)
    except Exception as e:
        print(f"Error initializing session: {e}")
    return session

def get_page_content(session, page_num):
    """抓取指定頁面的內容"""
    params = {
        'pageno': page_num,
        'l': 0, 'p_name': '', 'p_area': '', 'p_road': '',
        'start_date': '', 'end_date': '', 'p_type': '', 'c_type': '',
        'p_city': 'all', 'm': 1
    }
    
    try:
        response = session.get(SHOWPAGE_URL, params=params, headers=HEADERS, verify=False)
        response.raise_for_status()
        return response.text
    except Exception as e:
        print(f"Error fetching page {page_num}: {e}")
        return None

def get_text_by_headers(soup, headers_id):
    """輔助函式：根據 headers 屬性獲取文字"""
    element = soup.find('td', headers=headers_id)
    if not element:
        element = soup.find('th', headers=headers_id)
    if element:
        return element.get_text(strip=True)
    return ""

def parse_detail_table(soup, school_id, caption_text, headers_map):
    """
    通用解析函式：解析科目或交通車表格
    headers_map: dict, key為HTML中的headers id, value為輸出欄位名
    """
    results = []
    # 尋找對應 caption 的 table
    # 先找所有 table，再檢查 caption
    tables = soup.find_all('table')
    target_table = None
    for t in tables:
        cap = t.find('caption')
        if cap and caption_text in cap.get_text():
            target_table = t
            break
            
    if not target_table:
        return results
        
    tbody = target_table.find('tbody')
    if not tbody:
        return results
        
    rows = tbody.find_all('tr')
    for row in rows:
        # 檢查是否為「無資料」
        if "無資料" in row.get_text():
            continue
            
        item = {'補習班代碼': school_id}
        has_data = False
        
        for header_id, field_name in headers_map.items():
            val = get_text_by_headers(row, header_id) # 這裡傳入 row 作為 scope
            # 注意：get_text_by_headers 原本是設計給 soup 查找 id，
            #但在科目列表中，td 的 headers 屬性是用來對應 th 的。
            # bs4 的 find 在 row 裡面找 headers=... 是可行的。
            item[field_name] = val
            if val:
                has_data = True
                
        if has_data:
            results.append(item)
            
    return results

def get_school_details(session, school_id):
    """抓取並解析詳細資料頁面，回傳 (info, subjects, vehicles)"""
    params = {'u': school_id}
    info = {}
    subjects = []
    vehicles = []
    
    try:
        response = session.get(DETAIL_URL, params=params, headers=HEADERS, verify=False)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        # 1. 基本資料 (schools.csv)
        info['主管機關文件單位代碼'] = get_text_by_headers(soup, 'th-sqnum')
        info['補習班類別/科目'] = get_text_by_headers(soup, 'th-cataname')
        info['立案情形'] = get_text_by_headers(soup, 'th-legaltype')
        info['傳真號碼'] = get_text_by_headers(soup, 'th-fax')
        info['電子郵件'] = get_text_by_headers(soup, 'th-email')
        info['教室數'] = get_text_by_headers(soup, 'th-roomcount')
        info['飲用水設備維護管理'] = get_text_by_headers(soup, 'th-water')
        info['教室面積'] = get_text_by_headers(soup, 'th-roomarea')
        info['班舍總面積'] = get_text_by_headers(soup, 'th-schoolarea')
        info['停辦文號'] = get_text_by_headers(soup, 'th-shutnumber')
        info['停辦生效日'] = get_text_by_headers(soup, 'th-shutexpire')
        info['停辦截止日'] = get_text_by_headers(soup, 'th-shutclosure')
        info['負責人姓名'] = get_text_by_headers(soup, 'th-incharge')
        info['設立人姓名'] = get_text_by_headers(soup, 'th-establish')
        info['班主任'] = get_text_by_headers(soup, 'th-director')

        # 2. 核准科目資料 (subjects.csv)
        subj_map = {
            'th-course-name': '核准科目名稱',
            'th-allow-class': '核准班級數',
            'th-allow-person': '每班核准人數',
            'th-lesson-total': '每週總節(時)數',
            'th-study-period': '修業期限',
            'th-allow-recruiter': '招生對象'
        }
        subjects = parse_detail_table(soup, school_id, "核准科目資料", subj_map)

        # 3. 交通車資料 (vehicles.csv)
        veh_map = {
            'th-permit-id': '牌照號碼',
            'th-approve-doc': '備查文號',
            'th-approve-date': '備查日期'
        }
        vehicles = parse_detail_table(soup, school_id, "交通車資料", veh_map)

        return info, subjects, vehicles

    except Exception as e:
        print(f"Error fetching details for {school_id}: {e}")
        return {}, [], []

def parse_total_count(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    caption = soup.find('caption', id='result-list')
    if caption:
        text = caption.get_text(strip=True)
        match = re.search(r'共\s*(\d+)\s*筆', text)
        if match:
            return int(match.group(1))
    return 0

def parse_list_page(html_content):
    """解析列表頁的基本資料，回傳 list of items"""
    data = []
    soup = BeautifulSoup(html_content, 'html.parser')
    table = soup.find('table', {'class': 'table m-2'})
    
    if not table or not table.find('tbody'):
        return data

    rows = table.find('tbody').find_all('tr')
    for row in rows:
        cols = row.find_all(['td', 'th'])
        if len(cols) >= 7:
            item = {
                '縣市': cols[1].get_text(strip=True),
                '補習班名稱': cols[2].get_text(strip=True),
                '班址': cols[3].get_text(strip=True),
                '電話': cols[4].get_text(strip=True),
                '立案文號': cols[5].get_text(strip=True),
                '立案日期': cols[6].get_text(strip=True),
                '補習班代碼': ''
            }
            # 提取 ID
            action_col = cols[7]
            button = action_col.find('button')
            if button and button.get('onclick'):
                match = re.search(r'detail\.jsp\?u=(\d+)', button.get('onclick'))
                if match:
                    item['補習班代碼'] = match.group(1)
            
            data.append(item)
    return data

def main():
    print("開始抓取全台補習班資料 (含詳細資訊)...")
    session = get_session()
    
    # 1. 取得第一頁
    first_page_html = get_page_content(session, 1)
    if not first_page_html:
        print("無法取得第一頁，終止。")
        return

    total_count = parse_total_count(first_page_html)
    if total_count == 0:
        print("警告: 無法解析總筆數。")
        return

    items_per_page = 15
    total_pages = math.ceil(total_count / items_per_page)
    print(f"總筆數: {total_count}, 總頁數: {total_pages}")
    
    # 定義 CSV Headers
    header_schools = [
        '縣市', '補習班名稱', '補習班代碼', '主管機關文件單位代碼', '補習班類別/科目', 
        '班址', '電話', '傳真號碼', '電子郵件', '立案情形', '立案文號', '立案日期',
        '教室數', '飲用水設備維護管理', '教室面積', '班舍總面積',
        '停辦文號', '停辦生效日', '停辦截止日',
        '負責人姓名', '設立人姓名', '班主任'
    ]
    header_subjects = ['補習班代碼', '核准科目名稱', '核准班級數', '每班核准人數', '每週總節(時)數', '修業期限', '招生對象']
    header_vehicles = ['補習班代碼', '牌照號碼', '備查文號', '備查日期']
    
    # 開啟檔案 (Append mode if resuming, but here we overwrite)
    # 使用 ExitStack 來管理多個檔案較好，但這裡簡單用巢狀或分開開
    f_schools = open(FILE_SCHOOLS, 'w', newline='', encoding='utf-8-sig')
    f_subjects = open(FILE_SUBJECTS, 'w', newline='', encoding='utf-8-sig')
    f_vehicles = open(FILE_VEHICLES, 'w', newline='', encoding='utf-8-sig')
    
    w_schools = csv.DictWriter(f_schools, fieldnames=header_schools)
    w_subjects = csv.DictWriter(f_subjects, fieldnames=header_subjects)
    w_vehicles = csv.DictWriter(f_vehicles, fieldnames=header_vehicles)
    
    w_schools.writeheader()
    w_subjects.writeheader()
    w_vehicles.writeheader()
    
    try:
        # 2. 遍歷頁面
        for page in range(1, total_pages + 1):
            print(f"正在抓取第 {page}/{total_pages} 頁...", end='\r')
            
            html = first_page_html if page == 1 else get_page_content(session, page)
            
            if html:
                # 1. 解析列表
                list_items = parse_list_page(html)
                
                # 2. 逐筆抓取詳細資料
                for item in list_items:
                    school_id = item.get('補習班代碼')
                    if school_id:
                        det_info, det_subjs, det_vehs = get_school_details(session, school_id)
                        
                        # 合併基本資料
                        item.update(det_info)
                        w_schools.writerow(item)
                        
                        # 寫入科目
                        if det_subjs:
                            w_subjects.writerows(det_subjs)
                            
                        # 寫入交通車
                        if det_vehs:
                            w_vehicles.writerows(det_vehs)
                    else:
                        # 若無 ID，僅寫入列表有的資料
                        w_schools.writerow(item)
            
            time.sleep(1)

    finally:
        f_schools.close()
        f_subjects.close()
        f_vehicles.close()
        print(f"\n抓取完成！資料已儲存至 {FILE_SCHOOLS}, {FILE_SUBJECTS}, {FILE_VEHICLES}")

if __name__ == "__main__":
    main()
