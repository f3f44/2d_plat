import os, base64

def dirToDict(path):
    result = {}
    print(f'Converting {path}')
    for i in os.listdir(path):
        ip = os.path.join(path, i)
        if os.path.isdir(ip):
            print(f'{ip} is dir')
            result[i] = dirToDict(ip)
            print(f'{ip} converted')
        else:
            print(f'{ip} is file. encoding')
            with open(ip, "rb") as f:
                result[i] = base64.b64encode(f.read()).decode('utf-8')
            print(f'{ip} converted and encoded')
    return result

def assemble_encode(Dict, tab=0):
    result = ''
    print(f'Encoding {Dict}')
    for j, i in Dict.items():
        if isinstance(i, dict):
            print(f'{j} is folder: {i}')
            result += f"#{j}\n{assemble_encode(i, tab+1)}$\n"
            print(f'{j} Encoded')
        else:
            print(f'{j} is file')
            result += f'{"    "*tab}!{j}@{i}\n'
            print(f'{j} Encoded')
    return result

def encode(folder_path, destination=r'.\encoded.lvl'):
    r = f"!@THE#$LEVEL%^DATA&*\n{assemble_encode(dirToDict(folder_path))}"
    with open(destination, 'w') as f:
        f.write(r)
    print('Done')

def decode_to_dict(file_path):
    print(f"Parsing archive to dict: {file_path}")
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.read().splitlines()
    header = "!@THE#$LEVEL%^DATA&*"
    if not lines or lines[0] != header:
        print("!? (Неверный формат архива)")
        return None
    root_dict = {}
    dict_stack = [root_dict]
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
            base64_data = clean_line[separator+1:]
            current_dir = dict_stack[-1]
            current_dir[file_name] = base64_data
    print("Parsing Done")
    print(root_dict)
    return root_dict

encode(r'.\test', r'.\test.lvl')