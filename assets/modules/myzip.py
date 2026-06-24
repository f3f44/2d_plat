import os, struct

def dirToDict(path, basement={}, ID=0):
    result = {}
    print(f'Converting {path}')
    for i in os.listdir(path):
        ip = os.path.join(path, i)
        if os.path.isdir(ip):
            print(f'{ip} is dir')
            dec = dirToDict(ip, basement, ID)
            result[i] = dec[0]
            ID = dec[2]
            for NAME, DATA in dec[1].items():
                basement[NAME] = DATA
            print(f'{ip} converted')
        else:
            print(f'{ip} is file. encoding')
            ID += 1
            with open(ip, "rb") as f:
                file_bytes = f.read()
                result[i] = f'${ID}:{len(file_bytes)}' 
                basement[ID] = file_bytes
            print(f'{ip} converted and encoded with id {ID}')
    return result, basement, ID


def assemble_encode(Dict, tab=0):
    result = ''
    print(f'Encoding {Dict}')
    for j, i in Dict.items():
        if isinstance(i, dict):
            print(f'{j} is folder')
            result += f"#{j}\n{assemble_encode(i, tab+1)}$\n"
            print(f'{j} Encoded')
        else:
            print(f'{j} is file')
            result += f'{"    "*tab}!{j}@{i}\n'
            print(f'{j} Encoded')
    return result

def encode(folder_path, destination=r'.\encoded.lvl'):
    Dict = dirToDict(folder_path)
    r = f"!@THE#$LEVEL%^DATA&*\n{assemble_encode(Dict[0])}"
    r = r.encode("utf-8")
    with open(destination, 'wb') as f:
        f.write(struct.pack('<I', len(r)))
        f.write(r)
        basement = Dict[1]
        for current_id in sorted(basement.keys()):
            f.write(basement[current_id])
    print('Done')

def decode_to_dict(file_path):
    print(f"Parsing binary archive: {file_path}")
    with open(file_path, 'rb') as f:
        length_bytes = f.read(4)
        if not length_bytes:
            return None
        structure_length, = struct.unpack('<I', length_bytes)
        structure_bytes = f.read(structure_length)
        lines = structure_bytes.decode('utf-8').splitlines()
        binary_tail = f.read()
    header = "!@THE#$LEVEL%^DATA&*"
    if not lines or lines[0] != header:
        print("!? (Неверный формат архива)")
        return None
    root_dict = {}
    dict_stack = [root_dict]
    file_list = []
    for line in lines[1:]:
        clean_line = line.lstrip()
        if not clean_line:
            continue
        char = clean_line[0]
        if char == '#':
            end_name = clean_line.find('$')
            folder_name = clean_line[1:end_name]
            current_dir = dict_stack[-1]
            current_dir[folder_name] = {}
            dict_stack.append(current_dir[folder_name])
        elif char == '$':
            if len(dict_stack) > 1:
                dict_stack.pop()
        elif char == '!':
            separator = clean_line.find('@')
            file_name = clean_line[1:separator]
            meta = clean_line[separator+1:]
            link_id, file_size = meta.split(':')
            link_id = int(link_id.replace('$', ''))
            file_size = int(file_size)
            current_dir = dict_stack[-1]
            file_list.append((current_dir, file_name, link_id, file_size))
    file_list.sort(key=lambda x: x[2])
    current_offset = 0
    for current_dir, file_name, link_id, file_size in file_list:
        file_bytes = binary_tail[current_offset : current_offset + file_size]
        current_offset += file_size
        if file_name.endswith('.json') or file_name.endswith('.txt'):
            current_dir[file_name] = file_bytes.decode('utf-8')
        else:
            current_dir[file_name] = file_bytes
    print("Parsing Done")
    return root_dict