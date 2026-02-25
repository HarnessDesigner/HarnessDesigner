import requests
import time
from requests.utils import requote_uri


header = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Accept-Language": "en-US,en;q=0.5",
    "Connection": "keep-alive",
    "Cookie": "AMCV_A638776A5245AFE50A490D44%40AdobeOrg=-432600572%7CMCIDTS%7C20372%7CMCMID%7C37036414041189707455185991421694069091%7CMCAID%7CNONE%7CMCOPTOUT-1760150989s%7CNONE%7CvVersion%7C4.5.2; mbox=PC#beb9df17c300479ca08ccf13ef8a58b2.35_0#1823388590|session#0fde73c337574919bc796ac0e86961b5#1760145650; PIM-SESSION-ID=lnbMaQRuQe5PtK1M; at_check=true; dtCookie=v_4_srv_1_sn_DAA37FA613246E91BE4B6615A705E3E0_perc_100000_ol_0_mul_1_app-3A619a1bcb124cd83e_1; AMCVS_A638776A5245AFE50A490D44%40AdobeOrg=1; SSO=guestusr@te.com; SMIDENTITY=nE7kGrDWHUWNevsUTRXI80CG3+tFrtVwZQ00fRusoY+BiSURY3pBgO9wOzdqVYMY/sQ/jmNCNXwKkgdp0K85tdwXzlFqkBvZq7ThjB4o/Mlmnnm7bvJPsXO31kAiml7Fh5qOb+wTUKPyx/BRyABRuV4psjSEqfv5oSsbNg7QwHbhLRV0so7hYWP3Ub/nMKBG0PYBkclvYHySBbu7/XhKHcqONXZ3D6P3VMHZHdkFxrdDbDV7W2sbXqqvgEKeC0iTR06JrGNyRskLOePkGD86TPyaPSyFSlDGbPFa3EYHtfQdsLMR3nEMxJBQ+rySUrdpWg9aWOaLAxKMXDn5Q2wq+NOOCFrHTfukeY/LfyeJovQhUqWA25xMQ34M43zpnWqktbPYFlxKl1FjItiI0Z/WN0wTLNT2YRkSXGL5Uds/zJuK9Dbthc9iz6R85ebLN0KnnpalV5cIkZUsklgaTZXr3uw79ndBNcjBKdlPB4bihlAzqWDMS4P1z5rQbvsS14/5zgRblBwHNzjby/A3nYCOo/TcjjDibhbWhLAT3sUFL0fF5yz3XEtAZgF85ImuYoJh; ak_bmsc=1A4E94700E9BCB529B5C2C0AA7F55224~000000000000000000000000000000~YAAQpFkhF5r5raWZAQAAi72+0B31jvwgvJXIh01oRT0NJ+TJUpCqYUKRGEmik8+8MUb3cciP2Wj8mAh2kspCOpllSo7zF3zHr0UWKgHMhiQsZGmqbDb8OYG1vFgxpRL7J+ryIxGI4C682OS/pE3iQJbqGTWXQRrEUCfK4T+U8jZx7qzTjS/1wAUX0Mo0xEJowvxsTqqBtsz4nLXPzgLiFHCRF9xXIwDv8vC9I/JfnoITBANY8y5gCxAy4+YcP5Y0tlpHmQgrADD0/Z+X8VBkt4tZWgBV0iVOPbMUqMQnvnHg1DyR7VMwy6XjT548kJjFPCmhAjZSjJDBou6m1Eko2BphKT5gXFTS8gxsiPly/91BVZomRh6p8KI8kNpCyHKGEFLdhQp7H+g=; bm_sv=E38DE1968225466265BFD0176661AD9A~YAAQpFkhF0JotaWZAQAAfIUk0R2FrW+zcbwOw1wi8k01yeyHZ4w/MLvbswVZZdsrnd+P28rGX1TK+/CYaf8cqPJnhBHj8WMhu9VtYlONmzIT66dcc1g/RTBStrg4V7AqEkTx+7cXztbs1LZDeh9lXPYSgyvEk8r3XN9fai9s948GBjPE1vhnl28nGIq4iyBvM7vQ5dUBQ3+ytwYl6u1CJs5wMHMjYa2NrX9hRqYLW2E0/6cyfNPbVEAdmM1q~1",
    "Host": "api.te.com",
    "Priority": "u=4",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "cross-site",
    "TE": "trailers",
    "Upgrade-Insecure-Requests": "1",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:143.0) Gecko/20100101 Firefox/143.0"
}


URL = 'https://api.te.com/api/v1/search/service/search/products?o={last}&s=100&storeid=TEUSA&c=usa&l=en&st=web&mediaType=jsonns&dist_region=North America'
TE_URL = 'https://www.te.com'


COMPAT_URL = 'https://api.te.com/api/v1/search/service/product/related-products?c=usa&l=en&tcpn={part_number}&dist_region=North+America&s=100&r={last}&mediaType=jsonns&has_ida=y&storeid=TEUSA'


feature_codes = {
    904930: 'nominal_voltage',
    901869: 'number_of_cavaties',
    901870: 'sealable',
    901781: 'min_max_temp',
    905928: 'row_count',
    902861: 'has_cpa',  # No, Yes
    905428: 'primary_lock_type',
    901867: 'connection_system',  # Wire-to-Wire
    901847: 'centerline',
    903799: 'color',
    901868: 'current',
}

'''


['compatibleProducts']['pagingLinks']['totalRecords']
['compatibleProducts']['pagingLinks']['beginDisplayRecordNumber']
['compatibleProducts']['pagingLinks']['endDisplayRecordNumber']

'''


def read_compat_parts(products):
    compat_parts = []

    for product in products:
        part_number = product['tcpn']
        features = []

        for group in product.get('featureGroups', []):
            for feature in group.get('features', []):
                code = feature.get('code', None)
                label = feature.get('displayValue', None)
                values = []
                uom = feature.get('primaryUnit', {}).get('code', None)

                for value in feature.get('primaryValues', []):
                    values.append(value['value'])

                features.append(dict(
                    code=code,
                    label=label,
                    uom=uom,
                    values=values))

        compat_parts.append(dict(
            part_number=part_number,
            features=features))

    return compat_parts


def get_compatable_parts(part_number):
    url = requote_uri(COMPAT_URL.format(last=0, part_number=part_number))
    print(url)
    response = requests.get(url, headers=header)
    handlecookie(response)

    data = response.json()
    count = data['results']['compatibleProducts']['pagingLinks']['totalRecords']

    compat_parts = read_compat_parts(data['results']['compatibleProducts']['products'])
    last = data['results']['compatibleProducts']['pagingLinks']['endDisplayRecordNumber']

    while last < count:
        new_url = requote_uri(COMPAT_URL.format(last=last, part_number=part_number))
        if new_url == url:
            break
        url = new_url

        print(url)
        response = requests.get(url, headers=header)
        handlecookie(response)
        data = response.json()
        compat_parts.extend(read_compat_parts(data['results']['compatibleProducts']['products']))
        last = data['results']['compatibleProducts']['pagingLinks']['endDisplayRecordNumber']

    return compat_parts


def read_products(products):
    product_output = []

    for product in products:
        images = []
        datasheets = []
        cads = []
        models3d = []
        models2d = []
        features = []
        feature_groups = []

        for alias in product.get('aliasNameAndStatus', []):
            if alias.get("productAliasStatus", '') == 'P_tcpn':
                part_number = alias["productAliasNbr"]
                break
        else:
            continue

        description1 = product.get('friendlyDescription', None)
        description2 = product.get('description', None)

        for image in product.get('images', []):
            images.append(TE_URL + image['imageUrl'])

        for document in product.get('documents', []):
            doc_type = document['type']
            doc_format = document['format']
            doc_url = document['url']
            doc_filename = document['filename']

            if doc_type == 'Data Sheet':
                datasheets.append((doc_url, doc_format))
            elif doc_format == '3d_stp.zip':
                models3d.append((doc_url, doc_filename))
            elif doc_format == '2d_dxf.zip':
                models2d.append((doc_url, doc_filename))

        if 'docDrawing' in product:
            cads.append((product['docDrawing']['url'], product['docDrawing']['format']))

        for feature in product.get('primaryFeatures', []):
            label = feature.get('label', None)
            code = feature.get('code', None)
            uom = feature.get('primaryUnit', {}).get('code', None)

            feature_values = []
            for value in feature.get('primaryValues', []):
                feature_values.append(value['value'])

            features.append(dict(code=code, label=label, values=feature_values, uom=uom))

        for feature_group in product.get('featureGroups', []):
            for feature in feature_group.get('features', []):
                code = feature.get('code', None)
                label = feature.get('displayValue', None)
                values = []

                uom = feature.get('primaryUnit', {}).get('code', None)

                for value in feature.get('primaryValues', []):
                    values.append(value['value'])

                feature_groups.append(dict(code=code, label=label, values=values, uom=uom))

        compat_parts = get_compatable_parts(part_number)

        product_output.append(dict(
            part_number=part_number,
            images=images,
            datasheets=datasheets,
            cads=cads,
            models3d=models3d,
            models2d=models2d,
            features=features,
            feature_groups=feature_groups,
            description1=description1,
            description2=description2,
            compat_parts=compat_parts))

    return product_output


'''
ak_bmsc=1A4E94700E9BCB529B5C2C0AA7F55224~000000000000000000000000000000~YAAQpFkhF/DYt6WZAQAA5a9H0R0yHpE5EIF7NhwgRjlDEHufIiFDktdFszRa50LYFtQ1rc9r/tnMym5us3cYHCd4RxtY4e4q/xWtY7tUzX6EQNfBbe1ed+jWghxUTid2qph6cDOm3Z+lznyVuLzmjvA0AJ3jdFgIDtvO7oTSFZ+GaOFi4ul6NyykndAXrBA/13ezuG0F73rgKmm0FGwMatN71CYfibrcFM0DGK0ex+H5wKrdMT5NPsa6n4Dv3YISXLS1elvt+riTvCMq3hGZFGGu0wXYyX31wFjjEh/lWpGTs+lqihkGRxAFCTzVvNzorBrDdxZ5WmcdjYvdv1EEYxXiXBjNU4VGu9bHtOExibxNlkmq8yDZpeSZxLJXbpwLYJb14FfLwq0=; 
Domain=.te.com; 
Path=/; 
Expires=Sat, 11 Oct 2025 03:19:20 GMT; 
Max-Age=0, 
bm_sv=E38DE1968225466265BFD0176661AD9A~YAAQpFkhF/HYt6WZAQAA5a9H0R1kqjfRKcDj1MLHH30ejexkgSBYT10H9wTRjpLL5F4ra7L1dsU1cWAFzi7p7BkOttxdj+dJ2LaZWAiBosQ6gM6+K8GL5rCrS496r8iGqdS1mnxtzyZVaFFtuV2ZOpMdfVPnFjAy648ZbSQkTKDQdFCbUDpEQwJqhRfy23XfMvyLCZlmq74AUTeWMu8Q35wiwlJanbJipmzhBfyvpk81YTn+tZqJ9fQ25H7i~1; 
Domain=.te.com; 
Path=/; 
Expires=Sat, 11 Oct 2025 03:19:18 GMT; 
Max-Age=0; 
Secure
'''


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


import os  # NOQA


def get_url(last, **kwargs):
    url = URL.format(last=last)
    kwargs = [f'&{key}={value}' for key, value in kwargs.items()]
    url += ''.join(kwargs)
    return requote_uri(url)


def get_category(filename, start_num=0, file_num=None, **kwargs):
    url = get_url(start_num, **kwargs)
    print(url)
    response = requests.get(url, headers=header)
    handlecookie(response)

    data = response.json()
    count = data['results']['pagingLinks']['totalRecords']
    last = data['results']['pagingLinks']['endDisplayRecordNumber']

    print(count, '...', last)
    products = read_products(data['results']['products'])

    if file_num is not None:
        name = filename.rsplit('.', 1)[0]
        name += str(file_num) + '.json'
        file_num += 1
    else:
        name = filename

    with open(name, 'w') as f:
        f.write(json.dumps(products, indent=4))

    while last < count:
        url = get_url(last, **kwargs)
        print(url)
        response = requests.get(url, headers=header)
        handlecookie(response)
        data = response.json()
        last = data['results']['pagingLinks']['endDisplayRecordNumber']
        print(count, '...', last)
        products.extend(read_products(data['results']['products']))

        with open(name, 'w') as f:
            f.write(json.dumps(products, indent=4))

        if len(products) >= 5000 and file_num is not None:
            name = filename.rsplit('.', 1)[0]
            name += str(file_num) + '.json'
            file_num += 1
            del products[:]

    return products


import json  # NOQA


def get_count(filename):
    count = 0
    file_count = 0

    if os.path.exists(filename):
        with open(filename, 'r') as f:
            data = json.loads(f.read())
            count += len(data)

    while True:
        file_count += 1
        name = filename.rsplit('.', 1)[0]
        name += str(file_count) + '.json'
        if not os.path.exists(name):
            break

        with open(name, 'r') as f:
            data = json.loads(f.read())
            count += len(data)

    return filename, count, file_count


connectors = get_category(*get_count('new_connectors.json'), d='545674+545676+545677+659727', n=41620, nr=41620)
terminals = get_category(*get_count('terminals.json'), q='terminals', n='42722')

import sys  # NOQA

sys.exit()
wire_protection = get_category(*get_count('wire_protection.json'), n=42374, nr=42374)
shrink_tubing = get_category(*get_count('shrink_tubing.json'), n=42395, nr=42395)
wire_cable = get_category(*get_count('wire_cable.json'), n=42772, nr=42772)


'''
GET 

41620 = connectors
42395 = shrink tubing
42772 = wire and cable
42374 = wire protection and management

893246 = automotive connector accessories
41621 = automotive connectors


545677 = wire to wire
545676 = wire to panel
https://api.te.com/api/v1/search/service/search/products?o=0&s=20&nr=41634&n=41634&d=659727&storeid=TEUSA&c=usa&l=en&st=web&mediaType=jsonns&dist_region=North+America


nr="539832"
n="539832"
https://api.te.com/api/v1/search/service/search/products?o=0&s=20&nr=41634&n=41634&d=&storeid=TEUSA&c=usa&l=en&st=web&mediaType=jsonns&dist_region=North+America

https://api.te.com/api/v1/search/service/search/products?o=0&s=20&nr=539832&n=539832&d=545677+545676&storeid=TEUSA&c=usa&l=en&st=web&mediaType=jsonns&dist_region=North+America
https://api.te.com/api/v1/search/service/search/products?o=0&s=20&nr=539832&n=539832&d=545677&storeid=TEUSA&c=usa&l=en&st=web&mediaType=jsonns&dist_region=North+America


https://api.te.com/api/v1/search/service/search/products?o=0&s=20&nr=893246&n=893246&storeid=TEUSA&c=usa&l=en&st=web&mediaType=jsonns&dist_region=North+America
GET
https://api.te.com/api/v1/search/service/search/products?o=0&s=20&nr=41621&n=41621&storeid=TEUSA&c=usa&l=en&st=web&mediaType=jsonns&dist_region=North America
'''