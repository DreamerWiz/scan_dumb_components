import sys
import os
import re
import json


from termcolor import colored, COLORS



'''
 This is a useful function to export your dumb co-worker's
 react components dependencies relations.
 
 Res will be exported as pics.

 wizdaydream@gmail.com
'''

global_path = ''

string_to_node = {}
visited_paths = set()
sourced_components = set()
color_list = list(COLORS.keys())

remappings = []

comps_filter = []
class Comp:
  def __init__(self, filePath, name, body) -> None:
    self.path = filePath
    self.name = name
    self.body = body
    self.complete = False
    self.chidren = []

  def add_child(self, comp):
    if comp:
      self.chidren.append(comp)

  def complete(self):
    self.complete = True

  # def to_dict(self):
  #   res = []
  #   for c in self.chidren:
  #     res.append("\t" + c.to_dict() + "\n")
    
  #   res_str = ""
  #   if len(res) > 0:
  #     res_str = " chidren: \n" + "\n".join(res)

  #   return \
  #      "path: " + self.path.replace(global_path, '@') + " name: " + self.name + res_str
  
  def to_dict(self, layer=1):
    res = []
    for c in self.chidren:
      res.append("  " * layer + c.to_dict(layer + 1))
    
    res_str = ""
    if len(res) > 0:
      res_str = "\n" + "\n".join(res)

    display_path = self.path
    for rule in remappings:
      display_path = display_path.replace(rule[1], rule[0])
    
    display_path = re.sub(r'^.*src', '[masked]', display_path)

    return \
       colored("path: " + display_path + " name: " + self.name + res_str, color_list[(layer -1) % len(color_list)])

  def __str__(self) -> str:
    return self.to_dict(1)

def _get_file_content(p:str) -> str:
  if not os.path.exists(p):
    print("File '%s' not exist" % p)
    return ""
  
  with open(p, 'r') as file:
    return str(file.read())


def _find_relative_content_in_path(p:str, key:str):
  """
  find context according to the path and keyword
  """
  print("Seaching file ", p)
  content = ""
  with open(p, 'r') as file:
    content = str(file.read())
  pattern = r'\n[^\{\n]*\s+'+key+'[\s\(<]+[^\{]*\{'
  print(pattern)
  res = re.findall(pattern, content)
  # print(res)
  if len(res) == 0:
    return ''
  idx = content.index(res[0])
  # print(idx)

  content = content.replace('forwardRef(', '$$$$$$$$$$$')
  crack = 0
  b_brack = 0
  b_brack_closed = False
  target = 0
  for i in range(idx, len(content)):
    if content[i] == '(':
      b_brack += 1
    elif content[i] == ')':
      b_brack -= 1
      b_brack_times = True if not b_brack_closed else False
    elif content[i] == '{':
      crack += 1
    elif content[i] == '}':
      crack -= 1
      if crack == 0 and b_brack == 0:
        target = i
        break

  return content[idx: target+1]

def _get_dependencies_by_path(p:str):
  """
  according to import sentences
  """
  content = _get_file_content(p)
  if content == '':
    return
  
  pattern = r'(import|export)([^;]*)from([^;]*);'

  res = re.findall(pattern, content)

  ret = []
  for i in range(len(res)):
    _comp = res[i][1]
    # _comp = re.sub(r'default\s*as\s*', '', _comp)
    _origin = res[i][2]
    _loc = res[i][2].replace("../", os.path.dirname(os.path.dirname(p)) + "/").replace('./', os.path.dirname(p) + "/").replace("'", "").replace('"', '').strip()
    if _loc.startswith('.'):
      print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!", _loc, p, _origin)
    for rule in remappings:
      _loc = _loc.replace(rule[0], rule[1])
    
    # print(_loc)
    _comp = _comp.strip()
    if _comp.startswith("{"):
      _comp = _comp[1:-2]
    
    comps = _comp.split(",")

    comps = [c.replace('\n', '').replace(' ', '').replace('type{', '').replace('}', '') for c in comps if c != '']
    ret.append({"fileLocation": _loc, "components": comps})

  return ret
  # print(res)

def _get_main_component_by_path(p:str) -> []:
  """
  
  """
  content = _get_file_content(p)
  # print(content)
  if content == '':
    return
  
  pattern = r'export\s+default\s+function([^\{]*)\{\}'

  res = re.findall(pattern, content)


  # print(res)

def _test_comp(comp:str):
  """
  every comps_filter should test the comp
  """
  global comps_filter
  for cf in comps_filter:
    res = re.findall(cf, comp)
    # print(res)
    if len(res) > 0:
      # print(res)
      return False
  return True


def _get_all_components(content:str):
  """
  get all components in the content
  """
  # print(content)
  content = re.sub(r'function[^\)]*\)[^\{]\{', '', content)
  content = re.sub(r'use[a-zA-Z0-9_]+<[^>]*>', '', content)
  pattern = r'<([a-zA-Z0-9_]+)[^>]*>'
  # print(content)
  res = re.findall(pattern, content)
  # print(res)
  res =  [f for f in res if _test_comp(f)]

  return res
  # print(res)


def _get_all_functions(p:str):
  """
  sequence read all functions
  """
  content = _get_file_content(p)
  in_func_layer = 0

  raw_infos = []
  ret = []

  stack = []

  # Func mode
  for i in range(len(content)):
    if i >= len("function") and content[i-8:i] == "function":
      in_func_layer += 1
      stack.append({"flag": "function", "loc": i-8})
    if content[i] == '{':
      stack.append({"flag": "{", "loc": i})
    if content[i] == "(":
      stack.append({"flag": "(", "loc": i})
    if content[i] == ")":
      if stack[-1]["flag"] == "(":
        stack.pop()
      # stack.append({"flag": "(", "loc": i})
    if content[i] == '}':
      s = stack.pop()
      if len(stack) == 0:
        continue

      if stack[-1]["flag"] == "function":
        m_content = content[stack[-1]["loc"]:i+1]
        stack.pop()
        raw_infos.append(m_content)
  for func in raw_infos:
    res = re.findall(r'(function([^\{\(]+)[^\{]*\{)', func)

    start_idx = content.index(res[0][0])
    target_idx = content.rfind("\n", 0, start_idx)
    # find the line of funcion identifier, check if it is default comp
    func_name = res[0][1].strip()
    func_name = re.sub(r'<[^>]*>', '', func_name)
    if "default" in content[target_idx:start_idx]:
      ret.append({"funcName": func_name, "body": func, "root": True})
    else:
      ret.append({"funcName": func_name, "body": func, "root": False})
  
  # Class mode
      
  pattern = r'^class[^\{]*([^\{]*)extends([^\{]*)Component[^\{]*\{'
  res = re.findall(pattern, content)
  print(p)
  print(res)
  
  return ret


def recursive_get_components(p: str):
  """
  This file should contain a default
  """
  file_functions = []

  content = _get_file_content(p)
  res = _get_all_functions(p)

  dependencies = _get_dependencies_by_path(p)
  # print(dependencies)

  comp_to_file = {}

  for obj in dependencies:
    for c in obj["components"]:
      comp_to_file[c] = obj["fileLocation"]
      # print(c, obj["fileLocation"])

  comps_all = []

  for f in res:
    # print(f["body"])
    file_functions.append(f["funcName"])
    comps = _get_all_components(f["body"])
    print(f["funcName"], comps)
    comps = [{"comp": p + ":" + c, "loc": comp_to_file.get(c, "")} for c in comps]
    print(f["funcName"], comps)
    comps_all.append({"comp": Comp(p, f["funcName"]), "children": comps})

    # print(comps)
    # comps.append([{"comp": p + ":" + c["comp"], "loc": comp_to_file.get(c, "")} for c in comps])
  # print(comps_all)
    # print(comps)


  # print(comps_all)

  remove_list = []
  for i in range(len(comps_all)):
    """
    check if has 
    """
    _origin_comp = comps_all[i]['comp']
    for _c in comps_all[i]['children']:
      if _c['comp'].startswith(p):
        _tmp_path, tmp_comp = _c['comp'].split(":")
        print("comp:", _tmp_path, tmp_comp)
        print("original comp:", _origin_comp)

        for _comp_idx in [_comp_idx for _comp_idx in range(len(comps_all)) 
                          if _comp_idx != i 
                          and comps_all[_comp_idx]['comp'].name == tmp_comp
                          ]:
          _comp = comps_all[_comp_idx]['comp']
          _origin_comp.add_child(_comp)


  print(comps_all)


  # print(comps_all)
  

def bfs_search_components(start_path: str, res):
  """
  BFS algorithm record the components, if encounter new path
  process in the new loop
  """
   
  # scan all the related components
  visited = set()
  bfs = []

  bfs.append(start_path)
  visited.add(start_path)

  while len(bfs) > 0:
    cur_path = bfs.pop()


    print(cur_path)

    if os.path.isdir(cur_path):
      continue
    content = _get_file_content(cur_path)
    functions = _get_all_functions(cur_path)
    dependencies = _get_dependencies_by_path(cur_path)

    comp_to_file = {}

    for obj in dependencies:
      for c in obj["components"]:
        comp_to_file[c] = obj["fileLocation"]

    # print(dependencies)
    for f in functions:
      components = _get_all_components(f["body"])

      # this function contains the component it might be a comp in this file
      if len(components) > 0:
        res.append(cur_path + ":" + f["funcName"])

      for comp in components:
        file = comp_to_file.get(comp, "")
        if file not in visited and file != "":
          bfs.append(os.path.join(file, "src", comp, "index.ts"))
          res.append(file + ":" + comp)

def source_component(symbol):
  global string_to_node, sourced_components
  print("\nstart finding " + symbol)
  res = string_to_node.get(symbol, None)
  if symbol in sourced_components:
    return res
  sourced_components.add(symbol)

  if res is not None:
    print("exist symbol " + symbol + ", register for its comps")
    [file, comp] = symbol.split(":")

    # print(res.body)
    comps = _get_all_components(res.body)
    print("comps: " + str(comps))
    dependencies = _get_dependencies_by_path(res.path)
    comp_to_file = {}
    for obj in dependencies:
      for c in obj["components"]:
        comp_to_file[c] = obj["fileLocation"]
    
    for comp in comps:
      print(comp)
      # if comp in comp_to_file:
      #   res.add_child(source_component(comp_to_file[comp] + ":" + comp))
      symbol = comp_to_file.get(comp, res.path) + ":" + comp
      res.add_child(source_component(symbol))
    return res
    
  else:
    
    [loc, comp] = symbol.split(":")
    paths = []

    paths.append(os.path.join(loc))
    paths.append(os.path.join(loc, "index.ts"))
    paths.append(os.path.join(loc, comp, "index.ts"))
    paths.append(os.path.join(loc, "src", comp, "index.ts"))
    paths.append(os.path.join(loc, "src", "index.ts"))
    paths.append(os.path.join(loc, "index.tsx"))
    paths.append(os.path.join(loc, comp, "index.tsx"))
    paths.append(os.path.join(loc, "src", comp, "index.tsx"))
    paths.append(os.path.join(loc, "src", "index.tsx"))

    # print(paths)
    while len(paths) > 0:
      p = paths.pop(0)
      if not os.path.isfile(p):
        continue
      print("Searching file ", p)
      dependencies = _get_dependencies_by_path(p)
  
      comp_to_file = {}
      for obj in dependencies:
        for c in obj["components"]:
          comp_to_file[c] = obj["fileLocation"]
      
      # print(comp_to_file)
      if comp in comp_to_file or "defaultas" + comp in comp_to_file:
        # this file does not contain
        key = comp if comp in comp_to_file else 'defaultas' + comp
        # print(key, comp)
        _path = os.path.join(os.path.dirname(p), comp_to_file[key] + ".tsx").replace('/./', '/')
        paths.append(_path)
        continue
      print("Containing dependencies:", str(comp_to_file.keys()))
      # funcs = _get_all_functions(p)
      # print("Containing funcs:", str([obj['funcName'] for obj in funcs]))
      context = _find_relative_content_in_path(p, comp.replace('defaultas', ''))

      if context == '' and comp.startswith("defaultas"):
        context = _find_relative_content_in_path(p, 'default')

      print(context, comp, p, comp.replace('defaultas', ''))

      find = None
      if len(context) > 0:
        # find here
        string_to_node[p + ":" + comp] = Comp(p, comp, context)
        find = string_to_node[p + ":" + comp]
      
      # # print("HERERHERHEHRERHERHHE")
      if find is not None:
        print("Find comp in this file!")
        comps = _get_all_components(find.body)
        # print(p + ":" + comp, string_to_node[p + ":" + comp])
        res = source_component(p + ":" + comp)
        # print(res)
        return source_component(p + ":" + comp)
      else:
        return None
    print(colored("missed : " + symbol, color_list[1]))
    return None

def _register_comps_in_file(path) -> list[Comp]:
  global string_to_node, visited_paths
  
  if path in visited_paths:
    return []

  native_funcs = _get_all_functions(path)
  comp_to_file = {}
  # print(len(native_funcs))
  res = []

  root = None

  for obj in native_funcs:
    # print(obj["funcName"], obj["root"])
    comp_to_file[obj["funcName"]] = path

    cur_symbol = path + ":" + obj["funcName"]
    cur_node = Comp(path, obj["funcName"], obj["body"])
    string_to_node[cur_symbol] = cur_node
    # print(obj["root"])
    if obj["root"]:
      root = cur_node
    else:
      res.append(cur_node)
  
  res.insert(0, root)

  visited_paths.add(path)

  return res

def dfs_search_components(start_path):
  """
  dfs search components to get tree data
  """
  global string_to_node, visited_paths

  res = _register_comps_in_file(start_path)
  root = res[0]

  dependencies = _get_dependencies_by_path(start_path)
  chidren_comps = _get_all_components(root.body)

  comp_to_file = {}
  for obj in dependencies:
    for c in obj["components"]:
      comp_to_file[c] = obj["fileLocation"]

  processed_comps = []
  for comp in chidren_comps:
    symbol = comp_to_file.get(comp, start_path) + ":" + comp
    root.add_child(source_component(symbol))
  
  print(str(root))
  # root.complete()
    
if __name__ == "__main__":
  path = sys.argv[1]
  if path == '':
    exit("No path provided.")

  comps = []
  dfs_search_components(path)

  # for obj in comps:
  #   print(obj)

