# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

import os
import json

file_num = 1

filename = f'products{file_num}.json'

cpa_locks = []
tpa_locks = []


while os.path.exists(filename):
    print(filename)
    with open(filename, 'r') as f:
        data = json.loads(f.read())

    file_num += 1
    filename = f'products{file_num}.json'

    for product in data:
        if product.get('parentCategory', '') not in (
            "Automotive Connector Locks & Position Assurance",
        ):
            continue

        features = product.get('primaryFeatures', [])

        for feature in features:
            label = feature.get('label', '')

            if label == 'Connector & Contact Retention Accessory Type':
                values = feature.get('primaryValues', [])
                for value in values:
                    if value == "TPA (Terminal Position Assurance)":
                        tpa_locks.append(product)
                    elif value == "CPA (Connector Position Assurance)":
                        cpa_locks.append(product)
                    elif value == "Secondary Lock":
                        tpa_locks.append(product)
                    else:
                        continue

                    break
                else:
                    continue


with open('separated/cpa_locks.json', 'w') as f:
    f.write(json.dumps(cpa_locks, indent=4))

with open('separated/tpa_locks.json', 'w') as f:
    f.write(json.dumps(tpa_locks, indent=4))

'Connector & Contact Retention Accessory Type'


'''

LOCKS
----------------------------------------
{
    "features": [
        "Operating Temperature Range",
        "Number of Positions",
        "Primary Product Color",
        "Primary Product Material",
        "Connector & Contact Retention Accessory Type"
    ],
    "feature_groups": {
        "Product Type Features": [
            "Sealable",
            "Connector & Contact Retention Accessory Type"
        ],
        "Configuration Features": [
            "Number of Positions"
        ],
        "Body Features": [
            "Primary Product Color",
            "Primary Product Material"
        ],
        "Usage Conditions": [
            "Operating Temperature Range"
        ],

    },
    "base_categories": [
        "Automotive Parts"
    ],
    "parent_categories": [
        "Automotive Connector Locks & Position Assurance"
    ],
    "brands": [
        "TE Connectivity",
        "AMP"
    ]
}


'''