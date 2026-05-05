
import os
import json

file_num = 1

filename = f'products{file_num}.json'

base_categories = set()
parent_categories = set()
brands = set()

features = {}
feature_groups = {}


seals = {
    'products': [],
    'features': {},
    'feature_groups': {},
    'base_categories': set(),
    'parent_categories': set(),
    'brands': set()
}

bundles = {
    'products': [],
    'features': {},
    'feature_groups': {},
    'base_categories': set(),
    'parent_categories': set(),
    'brands': set()
}


cpa_locks = {
    'products': [],
    'features': {},
    'feature_groups': {},
    'base_categories': set(),
    'parent_categories': set(),
    'brands': set()
}

tpa_locks = {
    'products': [],
    'features': {},
    'feature_groups': {},
    'base_categories': set(),
    'parent_categories': set(),
    'brands': set()
}

locks = {
    'products': [],
    'features': {},
    'feature_groups': {},
    'base_categories': set(),
    'parent_categories': set(),
    'brands': set()
}

transitions = {
    'products': [],
    'features': {},
    'feature_groups': {},
    'base_categories': set(),
    'parent_categories': set(),
    'brands': set()
}

terminals = {
    'products': [],
    'features': {},
    'feature_groups': {},
    'base_categories': set(),
    'parent_categories': set(),
    'brands': set()
}

wires = {
    'products': [],
    'features': {},
    'feature_groups': {},
    'base_categories': set(),
    'parent_categories': set(),
    'brands': set()
}

housings = {
    'products': [],
    'features': {},
    'feature_groups': {},
    'base_categories': set(),
    'parent_categories': set(),
    'brands': set()
}

covers = {
    'products': [],
    'features': {},
    'feature_groups': {},
    'base_categories': set(),
    'parent_categories': set(),
    'brands': set()
}

accessories = {
    'products': [],
    'features': {},
    'feature_groups': {},
    'base_categories': set(),
    'parent_categories': set(),
    'brands': set()
}

boots = {
    'products': [],
    'features': {},
    'feature_groups': {},
    'base_categories': set(),
    'parent_categories': set(),
    'brands': set()
}

splices = {
    'products': [],
    'features': {},
    'feature_groups': {},
    'base_categories': set(),
    'parent_categories': set(),
    'brands': set()
}

generic = {
    'products': [],
    'features': {},
    'feature_groups': {},
    'base_categories': set(),
    'parent_categories': set(),
    'brands': set()
}


while os.path.exists(filename):
    print(filename)
    with open(filename, 'r') as f:
        data = json.loads(f.read())

    file_num += 1
    filename = f'products{file_num}.json'
    for product in data:
        if product.get('parentCategory', '') in (
            "Primary Wire",
            "Oriented Wire",
            "Multicore Cable",
            "High Speed Digital & Data Cable",
            "Power Cable",
            "Hook Up Wire",
            "Ribbon & Flat Cable",
            "Twisted Pair Cable",
            "Sensor Cable",
        ):
            container = wires

        elif product.get('parentCategory', '') in (
            'Insulation Boots & Sleeves',
            "EMI Shielded Boots",
            "Heat Shrink Boots",
            "Connector Strain Relief",

        ):
            container = boots

        elif product.get('parentCategory', '') in (
            "Data Bus Connectors",
            "Data Connectivity Housings",
            "Insulation Piercing Connectors",
            "SC Connectors",
            "Grounding/Earthing Connectors",
            "Automotive Housings",
            "Wedge Connectors",
            "Insulating Connectors",
            "Expanded Beam Fiber Housings",
            "Data Connectivity Headers",
            "Automotive Headers",
            "LC Connectors",
            "Compression Connectors",
            "Solar Connectors",
            "MC801 Fiber Connectors",
            "Card Edge Connector Housings",
            "Rack & Panel Connectors",
            "PCB Headers & Receptacles",
            "Internal I/O Connectors",
            "Backplane Power Connectors",
            "RJ14 Connectors",
            "SDL Connectors",
            "DisplayPort Connectors",
            "Card Edge Power Connectors",
            "RJ Point Five Connectors",
            "FFC Connectors",
            "Eurocard Connectors",
            "Plug & Socket Lighting Connectors",
            "RJ25 Connectors",
            "Street Lighting Connectors",
            "USB Connectors",
            "Two-Piece Edge Connectors",
            "Crimp Terminal Housings",
            "HSSDC2 Connectors",
            "Board-In Connectors",
            "Street Lighting Receptacles",
            "Circular Power Connectors",
            "Busbar Connectors",
            "Poke-In Connectors",
            "D-Shaped Connectors",
            "IEEE 1394 Connectors",
            "PC/104 Connectors",
            "Coax Connectors",
            "High Speed Pluggable IO Connectors & Cages",
            "RJ11 Connectors",
            "DIN Connectors",
            "Ballast Connectors",
            "Standard Circular Connectors",
            "FPC Connectors",
            "RJ45 Connectors",
            "Hard Metric Backplane Connectors",
            "Ribbon Cable Connectors",
            "RJ22 Connectors",
            "HDMI Connectors",
            "Industrial Mini I/O Connectors",
            "High Speed Backplane Connectors",
            "DC Jack Connectors",
            "Backplane Connector Housings",
            "Docking Connectors",
            "Quick Disconnects",
            "Standard Edge Connectors",
            "Standard Rectangular Connectors",
        ):
            container = housings

        elif product.get('parentCategory', '') in (
            'Splices',
            "Joints & Splices",
            "Cable-to-Cable Splicing",
            "Junction Splices",
        ):
            container = splices

        elif product.get('parentCategory', '') in (
            "Automotive Terminals",
            "Ring Connectors",
            "Fiber Optic Termini",
            "Power Cable Terminations",
            'Spade Terminals',
            'Special Purpose Terminals',
            'Ring Terminals',
            'Foil Terminals',
            'Power Terminals',
            'PCB Terminals',
            'Magnet Wire Terminals',
            "Circular Connector Contact Inserts",
            "Rectangular Contact Inserts",
            "Shielded Contacts",
            "Junction Contacts",
            "Connector Contacts",
            "Busbars & Terminals",
        ):
            container = terminals

        elif product.get('parentCategory', '') in (
            "Sealant Tape",
            "Heat Shrink Tubing",
            "Electrical Heat Shrink Tubing",
            "Fusion Tape",
            "Busbar Heat Shrink Tubing & Tape",
            "Power Cable Wraps",
        ):
            container = bundles

        elif product.get('parentCategory', '') in (
            "Automotive Connector Locks & Position Assurance",
        ):
            print(json.dumps(product, indent=4))

            for feature in product.get('primaryFeatures', []):
                label = feature.get('label', '')

                if label != 'Connector & Contact Retention Accessory Type':
                    continue

                for value in feature.get('primaryValues', []):
                    if value['value'] in (
                        "Latch Arm",
                        "CPA (Connector Position Assurance)"
                    ):
                        container = cpa_locks
                        break

                    elif value['value'] in (
                        "TPA (Terminal Position Assurance)",
                        "Secondary Lock"
                    ):
                        container = tpa_locks
                        break
                else:
                    continue

                break
            else:
                continue

        elif product.get('parentCategory', '') in (
            "Cable Transitions & Breakouts",
            "Power Cable Breakouts",
        ):
            container = transitions

        elif product.get('parentCategory', '') in (
            "Bushings & Bobbins",
            "Automotive Connector EMC Shielding",
            "Cable Mounting & Harness Accessories",
            "Cable Tie Mounts & Accessories",
            "Other Automotive Connector Accessories",
            "Cable Ties",
            "Connector Hardware",
        ):
            container = accessories

        elif product.get('parentCategory', '') in (
            "Sealing Sleeves",
            "Cable Entry Seals",
            "EMI Connector Gaskets",
            "Connector Seals & Cavity Plugs",
        ):
            container = seals

        elif product.get('parentCategory', '') in (
            "Fiber Connector Covers & Caps",
            "Automotive Connector Caps & Covers",
            "Heat Shrink Caps",
            "Rectangular Connector Hoods & Bases",
            "Wildlife Protection Covers",
            "Connector Backshells",
            "Connector Caps & Covers",
            "Power Cable End Caps",
        ):
            container = covers

        else:
            container = generic

        container['brands'].add(product.get('brand', None))
        container['base_categories'].add(product.get('baseCategory', None))
        container['parent_categories'].add(product.get('parentCategory', None))
        container['products'].append(product)

        for feature in product.get('primaryFeatures', []):
            label = feature.get('label', None)
            if 'Packaging' in label or 'Industry' in label:
                continue

            if label not in container['features']:
                container['features'][label] = {'primaryValues': set(), 'p_uom': set()}

            for value in feature.get('primaryValues', []):
                container['features'][label]['primaryValues'].add(value.get('value', None))

            if feature.get('uom', False):
                punit = feature.get('primaryUnit', None)

                if punit is not None:
                    container['features'][label]['p_uom'].add(punit.get('code', None))

        for fg in product.get('featureGroups', []):
            label = fg.get('label', None)
            if 'Packaging' in label or 'Industry' in label:
                continue

            if label not in container['feature_groups']:
                container['feature_groups'][label] = {}

            for feature in fg.get('features', []):

                label2 = feature.get('label', None)
                if 'Packaging' in label2 or 'Industry' in label2:
                    continue

                if label2 not in container['feature_groups'][label]:
                    container['feature_groups'][label][label2] = {'primaryValues': set(), 'p_uom': set()}

                for value in feature.get('primaryValues', []):
                    container['feature_groups'][label][label2]['primaryValues'].add(value.get('value', None))
                if feature.get('uom', False):
                    punit = feature.get('primaryUnit', None)

                    if punit is not None:
                        container['feature_groups'][label][label2]['p_uom'].add(punit.get('code', None))


def convert_sets(d):
    for key, value in list(d.items()):
        if isinstance(value, dict):
            convert_sets(value)
        elif isinstance(value, set):
            d[key] = list(value)


for container, label in (
    (seals, 'SEALS'),
    (bundles, 'BUNDLES'),
    (cpa_locks, 'CPA_LOCKS'),
    (tpa_locks, 'TPA_LOCKS'),
    (transitions, 'TRANSITIONS'),
    (terminals, 'TERMINALS'),
    (wires, 'WIRES'),
    (housings, 'HOUSINGS'),
    (covers, 'COVERS'),
    (accessories, 'ACCESSORIES'),
    (boots, 'BOOTS'),
    (splices, 'SPLICES'),
    (generic, 'GENERIC')
):

    products = container.pop('products')
    with open(f'separated/{label.lower()}.json', 'w') as f:
        f.write(json.dumps(products, indent=4))

    convert_sets(container)
    with open(f'new_temp/{label}.json', 'w') as f:
        f.write(json.dumps(container, indent=4))

    print(label)
    print('-' * 40)
    print(json.dumps(container, indent=4))
    print()
    print()
