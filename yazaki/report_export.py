# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

import json
import os
import time

import requests

DELAY_SECONDS = 1.0

SAVE_PATH = os.path.dirname(__file__)
RAW_CSV_PATH = os.path.join(SAVE_PATH, 'raw_csv')

# Yazaki's "Download Catalog" report is a DevExpress XtraReports document that
# requires a real, exact CavitySize value to return any rows at all (empty or
# missing CavitySize just renders one blank row). The site's report parameter
# panel only offers this filter as a fixed dropdown, so we walk it value by
# value instead of relying on pagination in the search grid.
CONNECTOR_CAVITY_SIZES = [
    '0.3', '0.6', '0.63', '0.64', '0.8', '0.9', '1.0', '1.1', '1.2', '1.3',
    '1.4', '1.5', '1.8', '14.5', '2.3', '2.8', '3.0', '3.2', '4.4', '4.8',
    '5.2', '6.3', '7.8', '8.0', '9.5', 'D1.0', 'D2.8', 'D8.0', 'other',
]


def _load_template(name):
    with open(os.path.join(SAVE_PATH, f'report_{name}_template.json'), encoding='utf-8') as f:
        return json.load(f)


def export_connector_batch(session, cavity_size):
    template = _load_template('connector')
    form = dict(template['form'])

    viewer_key = 'ctl00$cph1$ASPxDocumentViewer1$Splitter$Viewer'
    viewer = json.loads(form[viewer_key].replace('&quot;', '"'))
    viewer['parameters']['parameterCavitySize'] = cavity_size
    form[viewer_key] = json.dumps(viewer).replace('"', '&quot;')

    editor_key = 'ctl00$cph1$ASPxDocumentViewer1$Splitter$ParametersPanel$dxxrppEditor2'
    editor_vi_key = 'cph1_ASPxDocumentViewer1_Splitter_ParametersPanel_dxxrppEditor2_VI'
    editor_dd_key = 'ctl00$cph1$ASPxDocumentViewer1$Splitter$ParametersPanel$dxxrppEditor2$DDD$L'
    form[editor_key] = cavity_size
    form[editor_vi_key] = cavity_size
    form[editor_dd_key] = cavity_size

    response = session.post(template['url'], data=form, headers=template['headers'], timeout=60)
    return response


def harvest_connector():
    os.makedirs(RAW_CSV_PATH, exist_ok=True)
    session = requests.Session()

    for cavity_size in CONNECTOR_CAVITY_SIZES:
        out_path = os.path.join(RAW_CSV_PATH, f'Connector_{cavity_size}.csv')
        if os.path.exists(out_path):
            print('SKIP (already cached):', cavity_size)
            continue

        response = export_connector_batch(session, cavity_size)
        print(cavity_size, response.status_code, len(response.content))

        with open(out_path, 'wb') as f:
            f.write(response.content)

        time.sleep(DELAY_SECONDS)


if __name__ == '__main__':
    harvest_connector()
