import json
import math

in_path = 'separated/wires.json'
out_path = 'output/wires.json'

te_url = 'https://api.te.com/'

with open(in_path, 'r') as f:
    in_data = json.loads(f.read())

out_data = []


def get_temperatures(val):
    if not val:
        return None, None

    val = val.split(' – ')
    if len(val) == 1:
        min_val = max_val = val[0]
    else:
        min_val, max_val = val

    return int(min_val), int(max_val)


def get_diameter(val):
    if not val:
        return None, None

    val = val.split(' – ')
    if len(val) == 1:
        min_val = max_val = val[0]
    else:
        min_val, max_val = val

    return float(min_val), float(max_val)



from decimal import Decimal


def _d(v):
    try:
        return Decimal(str(v))
    except:
        print(repr(v))
        raise


def kcmil_to_mm2(kcmil):
    return float(round(_d(kcmil) * _d(0.5067), 4))


def awg_to_mm2(awg: int) -> float:
    if '#' in awg:
        awg = awg.replace('#', '')

    awg = awg.split('(', 1)[0].strip()

    mapping = {
        '4/0': 107,
        '3/0': 85.0,
        '2/0': 67.4,
        '1/0': 53.5
    }
    if awg in mapping:
        return mapping[awg]

    awg = int(float(awg))

    if awg >= 250:
        mm2 = kcmil_to_mm2(awg)
    else:
        d_in = _d(0.005) * (_d(92) ** ((_d(36) - _d(awg)) / _d(39)))
        d_mm = d_in * _d(25.4)
        mm2 = (_d(math.pi) / _d(4)) * (d_mm ** _d(2))

    return float(round(mm2, 4))


def mm2_to_awg(mm2: float) -> int:
    if mm2 >= 53.5:
        mapping = {
            53.5: -1,
            67.4: -2,
            85.0: -3,
            107.0: -4
        }
        if mm2 in mapping:
            return mapping[mm2]

        return int(round(_d(mm2) / _d(0.5067)))

    d_mm = _d(2.0) * _d(math.sqrt(_d(mm2) / _d(math.pi)))
    d_in = d_mm / _d(25.4)
    awg = _d(36) - _d(39) * _d(math.log(float(d_in / _d(0.005)), 92))
    return int(round(awg))


def awg_to_d_mm(awg: int) -> float:
    return mm2_to_d_mm(awg_to_mm2(awg))


def mm2_to_d_mm(mm2: float) -> float:
    d_mm = _d(2.0) * _d(math.sqrt(_d(mm2) / _d(math.pi)))
    return float(round(d_mm, 4))


def d_mm_to_mm2(d_mm: float) -> float:
    mm2 = _d(d_mm) / _d(2.0)
    mm2 *= mm2
    mm2 *= _d(math.pi)
    return float(round(mm2, 4))


def get_wire_size(val, unit='AWG'):
    if not val:
        return None

    if unit == 'AWG':
        return awg_to_mm2(val)
    elif unit == 'mm':
        if val.startswith('.'):
            val = '0' + val

        val = float(val)

        return d_mm_to_mm2(val)

    elif unit == 'CMA':
        val = float(round(_d(0.0005067075) * _d(val), 4))

        return val
    elif unit == 'mm²':
        try:
            val = float(round(_d(val), 4))
        except:
            print(repr(val))
            raise
        return val

    else:
        raise RuntimeError(uom)


def get_resistance(val):
    if val is None:
        return 0.0

    val = val.split('Ω/1000')[0]
    val = float(val.strip())
    val = float(_d(0.3048) * _d(val))

    return val

def get_size(val, unit):
    val = val.replace('mm', '')

    if 'K' in val:
        return 0.0

    if unit == 'AWG':
        val = val.replace('Size', '').strip()
        val = val.split('(', 1)[0].strip()

        return awg_to_d_mm(val)

    if val.startswith('.'):
        val = '0' + val

    return float(val)


def get_od(val):
    if val is None:
        return 0.0

    val = val.split(' – ')
    if len(val) == 1:
        val = val[0]
        if val.startswith('.'):
            val = '0' + val

        val = float(val)
    else:
        min_val, max_val = val
        if min_val.startswith('.'):
            min_val = '0' + min_val

        if max_val.startswith('.'):
            max_val = '0' + max_val

        val = float((_d(min_val) + _d(max_val)) / _d(2))

    return val


model3d_count = 0


'''
part_number, 
description, 
mfg=None, 
family=None,
series=None,
color=None, 
image=None, 
datasheet=None, 
cad=None, 
min_temp=None,
max_temp=None, 
material=None, 
stripe_color=None, 
core_material=None,
num_conductors=1, 
shielded=0, 
tpi=0.0, 
conductor_dia_mm=0.0, 
size_mm2=0.0,
size_awg=-1, 
od_mm=0.0, 
weight_1km=0.0, 
resistance_1km=0.0, 
volts=0.0
'''

for product in in_data:
    part_number = product.get('marketingPartNumNormalized', None)
    description = product.get('friendlyDescription', '')
    mfg = product.get('brand', None)
    family = None  # *
    series = None  # *
    color = None  # *
    image = None  # *
    datasheet = None  # *
    cad = None  # *
    min_temp = None  # *
    max_temp = None  # *

    material = None
    stripe_color = None
    core_material = None
    num_conductors = 1
    shielded = 0
    tpi = 0.0
    conductor_dia_mm = 0.0
    size_mm2 = 0.0
    size_awg = -1
    od_mm = 0.0
    weight_1km = 0.0
    resistance_1km = 0.0
    volts = 0.0

    if part_number is None:
        part_number = product.get('tcpn', None)

    if part_number is None:
        continue

    if mfg is None:
        continue

    for doc in product.get('documents', []):
        doc_type = doc.get('type', '')

        if doc_type == 'Customer Drawing' and cad is None:
            cad = doc.get('url', None)

        elif doc_type == 'Specification Or Standard' and datasheet is None:
            datasheet = doc.get('url', None)

    images = product.get('images', [])

    if images:
        image = te_url + images[0].get('imageUrl', '')
    else:
        images = product.get('primaryImages', [])

        if images:
            image = te_url + images[0]['path'] + images[0]['imageName']

    features = product.get('primaryFeatures', [])

    for feature in features:
        label = feature.get('label', '')

        if label == 'Wire & Cable Insulation Material':
            if material:
                continue

            values = feature.get('primaryValues', [])
            if values:
                material = values[0].get('value', None)

        if label == 'Conductor Material':
            if core_material:
                continue

            values = feature.get('primaryValues', [])
            if values:
                core_material = values[0].get('value', None)

        if label == 'Operating Voltage':
            if volts:
                continue

            values = feature.get('primaryValues', [])
            if values:
                volts = int(values[0].get('value', None))

        if label == 'Wire Size':
            values = feature.get('primaryValues', [])
            if values:
                uom = feature['primaryUnit']['code']

                size_mm2 = get_wire_size(values[0].get('value', ''), uom)
                conductor_dia_mm = mm2_to_d_mm(size_mm2)
                size_awg = mm2_to_awg(size_mm2)

        if label == 'Outside Cable Diameter':

            values = feature.get('primaryValues', [])
            if values:
                od_mm = float(values[0].get('value', '0.0'))

        if label == 'Shielded':
            values = feature.get('primaryValues', [])
            if values:
                shielded = int(values[0].get('value', 'No') == 'Yes')

        if label == 'Number of Conductors':
            if num_conductors:
                continue

            values = feature.get('primaryValues', [])
            if values:
                num_conductors = int(values[0].get('value', '0'))

        if label == 'Operating Temperature Range':
            if min_temp and max_temp:
                continue

            values = feature.get('primaryValues', [])
            if values:
                min_temp, max_temp = get_temperatures(values[0].get('value', ''))

        if label == 'Wire Color (Base)':
            if color:
                continue

            values = feature.get('primaryValues', [])
            if values:
                color = values[0].get('value', '')

        if label == 'Wire Color (Stripe)':
            if stripe_color:
                continue

            values = feature.get('primaryValues', [])
            if values:
                stripe_color = values[0].get('value', '')

    for fg in product.get('featureGroups', []):
        label = fg.get('label', '')

        if label == 'Electrical Characteristics':
            for feature in fg.get('features', []):
                label2 = feature.get('label', '')

                if label2 == 'Resistance Rating Conditions (Max)':
                    if resistance_1km:
                        continue

                    values = feature.get('primaryValues', [])
                    if values:
                        resistance_1km = get_resistance(values[0].get('value', None))

        if label == 'Dimensions':
            for feature in fg.get('features', []):
                label2 = feature.get('label', '')

                if label2 == 'Outside Cable Diameter':
                    values = feature.get('primaryValues', [])
                    if values:
                        od_mm = get_od(values[0].get('value', None))

                if label2 == 'Outside Cable Diameter':
                    values = feature.get('primaryValues', [])
                    if values:
                        value = values[0].get('value', '0.0')
                        if value.startswith('.'):
                            value = '0' + value

                        value = value.split(' – ')
                        if len(value) == 1:
                            value = float(value[0])
                        else:
                            min_value, max_value = value
                            if max_value.startswith('.'):
                                max_value = '0' + max_value

                            value = float((_d(min_value) + _d(max_value)) / _d(2))

                        weight_1km = value

    productFamily = product.get('productFamily', None)
    if productFamily is not None:
        for crumb in productFamily.get('crumbTrailItems', []):
            if family:
                break

            family = crumb.get('name', None)

    seriesTrail = product.get('seriesTrail', None)
    if seriesTrail is not None:
        for crumb in seriesTrail.get('crumbTrailItems', []):
            if series:
                break

            series = crumb.get('name', None)

    if family is None and 'TE' not in mfg:
        family = mfg
        mfg = 'TE Connectivity'

    if family is not None and family.lower() == mfg.lower():
        family = mfg
        mfg = 'TE Connectivity'

    if color is None:
        color = 'Gray'

    out_data.append(dict(
        part_number=part_number,
        description=description,
        mfg=mfg,
        family=family,
        series=series,
        color=color,
        image=image,
        datasheet=datasheet,
        cad=cad,
        min_temp=min_temp,
        max_temp=max_temp,
        material=material,
        stripe_color=stripe_color,
        core_material=core_material,
        num_conductors=num_conductors,
        shielded=shielded,
        tpi=tpi,
        conductor_dia_mm=conductor_dia_mm,
        size_mm2=size_mm2,
        size_awg=size_awg,
        od_mm=od_mm,
        weight_1km=weight_1km,
        resistance_1km=resistance_1km,
        volts=volts
    ))


with open(out_path, 'w') as f:
    f.write(json.dumps(out_data, indent=4))


print(len(out_data))
print(model3d_count)
