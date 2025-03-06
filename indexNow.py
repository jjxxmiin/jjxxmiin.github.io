import requests
import xml.etree.ElementTree as ET
from io import StringIO
import json

# sitemap URL
sitemap_url = "https://blog.opsoai.com/sitemap.xml"

# IndexNow API 엔드포인트 (Bing)
indexnow_url = "https://www.bing.com/IndexNow"

# API 키와 keyLocation 설정 (실제 값으로 교체 필요)
api_key = "9022693e922e49838303f1c6229126bc"  # 예시 키, 실제 키로 변경하세요
key_location = "https://blog.opsoai.com/9022693e922e49838303f1c6229126bc.txt"  # 실제 keyLocation으로 변경하세요

try:
    # 1. Sitemap XML 가져오기
    response = requests.get(sitemap_url)
    response.raise_for_status()  # 요청 실패 시 예외 발생

    # 2. XML 파싱
    xml_content = response.text
    root = ET.parse(StringIO(xml_content)).getroot()

    # 네임스페이스 처리
    namespace = {'sitemap': 'http://www.sitemaps.org/schemas/sitemap/0.9'}

    # 3. 모든 <loc> 태그에서 URL 추출
    url_tags = root.findall('.//sitemap:url/sitemap:loc', namespace)
    url_list = []
    
    for url in url_tags:
        if url.text:
            if url.text[-1] == '/':
                url_list.append(url.text)

    # url_list = [url.text for url in url_tags if url.text]

    if not url_list:
        print("No URLs found in the sitemap.")
        exit()

    print(f"Found {len(url_list)} URLs to submit:")
    for url in url_list:
        print(f" - {url}")

    # 4. IndexNow 요청 데이터 구성
    payload = {
        "host": "blog.opsoai.com",
        "key": api_key,
        "keyLocation": key_location,
        "urlList": url_list
    }

    # 헤더 설정
    headers = {
        "Content-Type": "application/json; charset=utf-8"
    }

    # 5. POST 요청 보내기
    indexnow_response = requests.post(indexnow_url,
                                    data=json.dumps(payload),
                                    headers=headers)

    # 6. 응답 처리
    print(f"Response Body: {indexnow_response}")

except requests.exceptions.RequestException as e:
    print(f"Failed to fetch sitemap or submit to IndexNow: {e}")
except ET.ParseError as e:
    print(f"Failed to parse XML: {e}")