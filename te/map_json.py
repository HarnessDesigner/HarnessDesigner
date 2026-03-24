import os
import json
import multiprocessing
multiprocessing.Queue()


def iter_dict(d):
    res = []

    for key, value in d.items():
        if isinstance(value, dict):
            res.append([key, iter_dict(value)])
        elif isinstance(value, list):
            res.append([key, iter_list(value)])
        else:
            res.append(key)

    return res


def iter_list(l):
    dict_entry = None
    list_entry = None
    for item in l:
        if isinstance(item, dict):
            if dict_entry is None:
                dict_entry = iter_dict(item)
            else:
                entry = iter_dict(item)
                if entry != dict_entry:
                    dict_entry = join(entry, dict_entry)

        elif isinstance(item, list):
            if list_entry is None:
                list_entry = iter_list(item)
            else:
                entry = iter_list(item)
                if entry != list_entry:
                    list_entry = join(entry, list_entry)

    if dict_entry is not None:
        return dict_entry
    if list_entry is not None:
        return list_entry
    return []


def run(f_name, q, print_lock):
    with print_lock:
        print('starting', f_name)

    with open(f_name, 'r') as f:
        data = json.loads(f.read())

    n_data = iter_list(data)

    q.put(n_data)
    with print_lock:
        print('finished', f_name)


def join(items1, items2):
    res1 = []
    res2 = []

    for item in items1[:]:
        if not isinstance(item, list):
            res1.append(item)
            items1.remove(item)

    for item in items2[:]:
        if not isinstance(item, list):
            res2.append(item)
            items2.remove(item)

    res1 = set(res1)
    res2 = set(res2)

    joined = list(res1.union(res2))

    for item1 in items1[:]:
        items1.remove(item1)
        if not item1:
            continue

        try:
            key = item1[0]
        except IndexError:
            print(item1)
            raise

        for item2 in items2[:]:

            if not item2:
                items2.remove(item2)
                continue

            try:
                if item2[0] == key:
                    break
            except IndexError:
                print(item2)
                raise
        else:
            joined.append(item1)
            continue

        items2.remove(item2)

        joined.extend(join(item1, item2))

    joined.extend(items2)

    return joined


import time

if __name__ == '__main__':

    file_num = 1

    filename = f'products{file_num}.json'

    queue = multiprocessing.Queue()
    lock = multiprocessing.Lock()

    output = []
    processes = []

    while os.path.exists(filename):
        print(filename)

        p = multiprocessing.Process(target=run, args=(filename, queue, lock))
        processes.append(p)
        p.start()

        file_num += 1
        filename = f'products{file_num}.json'

    while len(output) < 16:
        if queue.empty():
            time.sleep(5)
        else:
            output.append(queue.get())

    results = None

    for item in output:
        if results is None:
            results = item
        elif results != item:
            results = join(results, item)

    print(json.dumps(results, indent=4))
