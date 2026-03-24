'''
automotive-parts: 883095
automotive-connectors: 883096
automotive-connector-housings: 883097
connectors: 41620
rectangular-connectors: 539819
connector-accessories: 816795


GET
    https://api.te.com/api/v1/search/service/search/products
    ?q=connector
    &ptp=y
    &o=0
    &s=20
    &n=539955
    &storeid=TEUSA
    &c=usa
    &l=en
    &st=web
    &mediaType=jsonns
    &dist_region=North America


GET
    https://api.te.com/api/v1/search/service/search/products?ptp=y&o=0&s=20&storeid=TEUSA&c=usa&l=en&st=web&mediaType=jsonns&dist_region=North America




https://api.te.com/api/v1/search/service/search/products?ptp=y&o={start}&s=(stop}&storeid=TEUSA&c=usa&l=en&st=web&mediaType=jsonns&dist_region=North%20America

'''


import requests
import time


header = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive",
    "Cookie": "AMCV_A638776A5245AFE50A490D44%40AdobeOrg=-432600572%7CMCIDTS%7C20535%7CMCMID%7C37036414041189707455185991421694069091%7CMCAID%7CNONE%7CMCOPTOUT-1774225132s%7CNONE%7CvVersion%7C4.5.2; mbox=PC#beb9df17c300479ca08ccf13ef8a58b2.35_0#1833504047|session#f1a88b24f80e4eac984ed4c8d2b1ab12#1770261107; ak_bmsc=EDE5568E0F944C7D10F5E9D3BB81A486~000000000000000000000000000000~YAAQ0QbSF0nv4hGdAQAAmPWOFx/QxbuHgmvOTSkZeF2WgI5DgMnePuKWJkLWu96ednjORM+KGCQuxWt/VfdAKVyUb7jhrKfk/ysmIoPLS73kSKjt03p6vhxjoIXts/xe4HI9XNeKQYYaxA8Gke3fXpWQktCj3eXk734nt0tY8EPujA+H0PLCtzoJBDfTrUX4HZ9P7G6c5Vgby7TCiYWFmlsJoiiQQblLv0maa+yYdsSbEI8OPY+tXCaMDRjFV4cuziaJ3qANqqw4w5QEODFPbCp4+M9zuG8PhNxa68KjzE9knJOfynWUZRS5Tk1tlbTUML+A1oblhsGxc/PJqUxJBwMe0IPBMf9R2V8laytGwHIx8VyCpvnirDAGRynqGVn0ZdDxiwWNmsc=; bm_sv=39302999CCFF0E2A80E2D5C20F724A28~YAAQkBLfF6XbEPycAQAASeuoFx/0WDxPsXYsTvEb+DseTSMVAjTBISB2WvxdMzdl0oqOd29IAeomR6rxRZWtBL7uUNP6jHaKGlRyGAflfQb7/5jkoBLnjqTtuoSUKzOw7ZiUpb+u6fzpNR9QueNVPGuTaqXU/d0SgJkhNHnG7MYBHLT0YGQfNGNW/9K/FY9eqPL6ZygEcr1YLZbL3hQo/49BNgUyEoQUD8iF5FLN1zKtf/Esi0MFBXLlbtYU~1; AKA_A2=A; PIM-SESSION-ID=NMR1iHrXLmHDeDi4; SSO=guestusr@te.com; SMIDENTITY=InRxrBAYZz8g7rTGTOYCnIoLgg3gV4I0i/kiE813fMLg3oNT4xuFEng+DWhlVp3kfeunacUQWugx9g61BCwuWIenxjPqdwIAyBe4Pn2onUkx9VGkTpnvaHLGLb+FkBWGKgVILK8yaNx2W86nIJ1cdoGjeVjfo+p+2ralcv2kWKM1OYjBLZq5RetbpQ8uebkRCfYGJCqc4M6U71Fm6n4TfynF+KGaaBZBZP4GxoUgPZqqegiYcyHcxnJN2/fB3w+JvmvhFTUOlpbMOVkBG+n29PemJV3zxVuOUvIrfQpGPHbWKWVluvmQM4FE0RTkHpFZTHTya6+AZ976Nfyq2DWNKS2W+zSg9bwyAM85xAGAN5mqoFKmI1adSTxVmZOl9rShPr+XtOACeL9fbBdkCaxRp0uS7oIo4PQUXPhq0CJQssMQ+K8asroHOkwbfPm6++ObanVIpmuIB4gzns6jGUFeDQqLdOnvpyq6KE1ZLtqXRh2PtZBoEGNDcEzLh5Ep+HG2KnnL/4t0IoSSjxNabCla9LFUNjmLhJ3JVahuPmNf8jYX2eUvDmN6C0GFkGCjDRMA; AMCVS_A638776A5245AFE50A490D44%40AdobeOrg=1; dtCookie=v_4_srv_1_sn_57988F6CE361C9761D87B0C01E4EE007_perc_100000_ol_0_mul_1_app-3A619a1bcb124cd83e_1",
    "Host": "api.te.com",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Sec-GPC": "1",
    "Upgrade-Insecure-Requests": "1",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:148.0) Gecko/20100101 Firefox/148.0"
}


URL = 'https://api.te.com/api/v1/search/service/search/products?ptp=y&o={start}&s=100&storeid=TEUSA&c=usa&l=en&st=web&mediaType=jsonns&dist_region=North%20America'
TE_URL = 'https://www.te.com'


COMPAT_URL = 'https://api.te.com/api/v1/search/service/product/related-products?c=usa&l=en&tcpn={part_number}&dist_region=North+America&s=100&r={last}&mediaType=jsonns&has_ida=y&storeid=TEUSA'

'https://api.te.com/api/v1/search/service/search/products?ptp=y&o=0&s=100&storeid=TEUSA&c=usa&l=en&st=web&mediaType=jsonns&dist_region=North%20America'


def handlecookie(response):
    if 'Set-Cookie' in response.headers:
        cur_cookie = header['Cookie']

        cur_cookie = [item.strip() for item in cur_cookie.split(';')]
        cookie = {item.split('=', 1)[0]: item.split('=', 1)[1] for item in cur_cookie}

        new_cookie = [item.strip() for item in response.headers['Set-Cookie'].split(';')]
        new_cookie = {item.split('=', 1)[0]: item.split('=', 1)[1] for item in new_cookie if '=' in item}

        for key, value in new_cookie.items():
            if key in cookie:
                cookie[key] = value

        cookie = [key + '=' + value for key, value in cookie.items()]
        cookie = '; '.join(cookie)
        header['Cookie'] = cookie


class Response:

    headers = {
        'Set-Cookie': 'ak_bmsc=548E2C1A49344FCB167F223FF54F6C18~000000000000000000000000000000~YAAQ0QbSF729DRKdAQAAJ17RFx+zFXkamm704f9ENTY+sRFdxhTjDqzUruDSE0tjfU9KzOT30w4l2WnbPmKOwvAzFqCvsVWxgvXkBVkfcf6qX3SJtBw2XvwLaYUKkrYsE35Xdb1WRCbPB+Y6CcFWaVvQbN4mhBeB6PnhHPEs4RagsT7yjQapwkNICoQFJGrkDRlAESAZgj89t64TXVGZA/uBAm5xDm35AoxSC232EzBfhoCpM1w61XY1Lmtq/0L9buft1PjL3tM3nlQMgjrfShJExwMXsPXgWMPBL99dDrX+oD4g+yPZYuX6CogLOu5TjvXDK4Jm2J6v2+WIlXPex97ycKdceRrjcAQhrOYELsTT9zp6khHXmZo7AeuJewBfIZQHSv7ZUPg=; Domain=.te.com; Path=/; Expires=Mon, 23 Mar 2026 01:11:29 GMT; Max-Age=7199; HttpOnly'
    }


handlecookie(Response)


def get_url(start):
    return URL.format(start=start)


url = get_url(0)

response = requests.get(url, headers=header)
handlecookie(response)

try:
    data = response.json()
except:
    print(response.content.decode('utf-8'))
    raise

record_count = data['results']['pagingLinks']['totalRecords']
cur_start = 0

out_data = []
file_num = 1

filename = f'products{file_num}.json'
import os
import json

while os.path.exists(filename):
    with open(filename, 'r') as f:
        data = json.loads(f.read())
        cur_start += len(data)

    file_num += 1
    filename = f'products{file_num}.json'
    del data


if cur_start:
    cur_start += 1

error_count = 0

while cur_start < record_count:
    chunk = min(record_count - cur_start, 100)

    url = get_url(cur_start)
    print(cur_start, cur_start + chunk, ':', url)
    time.sleep(0.05)
    response = requests.get(url, headers=header)
    handlecookie(response)
    cur_start += chunk

    try:
        data = response.json()
    except:  # NOQA
        import traceback

        traceback.print_exc()
        print(response.content.decode('utf-8'))

        error_count += 1

        if error_count < 3:
            cur_start -= chunk
        continue

    'baseCategory'
    'parentCategory'
    'friendlyDescription'
    'parentCategoryId'
    'aliasNameAndStatus'
    'documents'
    'brand'


    try:
        out_data.extend(data['results']['products'])
    except KeyError:
        cur_start -= chunk
        time.sleep(0.05)
        raise RuntimeError

    error_count = 0
    if len(out_data) > 10000:
        with open(f'products{file_num}.json', 'w') as f:
            f.write(json.dumps(out_data, indent=4))

        del out_data[:]
        file_num += 1
