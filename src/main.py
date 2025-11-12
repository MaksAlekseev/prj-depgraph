import sys
import configparser
from pathlib import Path
import argparse
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from collections import defaultdict, deque

# -------------------
# Конфиг / утилиты
# -------------------
def load_config(path):
    cfg = configparser.ConfigParser()
    if not Path(path).exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    cfg.read(path, encoding='utf-8')
    if 'main' not in cfg:
        raise KeyError("Section [main] is missing in config file")
    return cfg['main']

def parse_package_name(pkg):
    parts = pkg.split(':')
    if len(parts) != 3:
        raise ValueError("package_name must be in format groupId:artifactId:version")
    return tuple(parts)

def build_pom_url(repo_url, group, artifact, version):
    base = repo_url.rstrip('/') + '/'
    group_path = group.replace('.', '/') + '/'
    pom_name = f"{artifact}-{version}.pom"
    return base + group_path + artifact + '/' + version + '/' + pom_name

def download_pom(url):
    with urllib.request.urlopen(url, timeout=10) as resp:
        return resp.read()

def extract_direct_dependencies_from_pom(pom_bytes):
    try:
        root = ET.fromstring(pom_bytes)
    except ET.ParseError as e:
        raise RuntimeError(f"POM parse error: {e}")

    deps = []
    for dep in root.findall('.//{*}dependency'):
        gid = dep.find('{*}groupId')
        aid = dep.find('{*}artifactId')
        ver = dep.find('{*}version')
        scope = dep.find('{*}scope')

        gid_text = gid.text.strip() if gid is not None and gid.text else '?'
        aid_text = aid.text.strip() if aid is not None and aid.text else '?'
        ver_text = ver.text.strip() if ver is not None and ver.text else '?'
        scope_text = scope.text.strip() if scope is not None and scope.text else ''

        # Пропускаем тестовые/provided зависимости для загрузки
        if scope_text.lower() in ('test', 'provided'):
            continue

        deps.append(f"{gid_text}:{aid_text}:{ver_text}")
    return deps

def read_test_repo(file_path):
    d = {}
    p = Path(file_path)
    if not p.exists():
        raise FileNotFoundError(f"Test repo file not found: {file_path}")
    for line in p.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if ':' in line:
            name, deps = line.split(':', 1)
            deps_list = [x.strip() for x in deps.split(',') if x.strip()]
            d[name.strip()] = deps_list
        else:
            d[line] = []
    return d

# -------------------
# Построение графа
# -------------------
def build_dependency_graph(root_pkg, repo_url, test_mode, test_file):
    graph = defaultdict(list)
    if test_mode:
        data = read_test_repo(test_file)
        for k, v in data.items():
            graph[k] = v
        return graph

    visited = set()
    queue = [root_pkg]

    while queue:
        current = queue.pop(0)
        if current in visited:
            continue
        visited.add(current)
        try:
            group, artifact, version = parse_package_name(current)
            pom_url = build_pom_url(repo_url, group, artifact, version)
            pom_bytes = download_pom(pom_url)
            deps = extract_direct_dependencies_from_pom(pom_bytes)
            graph[current] = deps
            for dep in deps:
                if dep not in visited and dep not in queue:
                    queue.append(dep)
        except Exception as e:
            print(f"Warning: could not load {current}: {e}")
            graph[current] = []
    return graph

# -------------------
# Топологическая сортировка (Kahn) с обработкой циклов
# -------------------
def topo_sort_kahn(graph):
    """
    Возвращает (order, cycles)
    - order: список вершин в топологическом порядке (если DAG)
             если есть циклы - order содержит порядок для тех узлов, которые удалось упорядочить
    - cycles: множество узлов, которые остались в цикле (если пусто — DAG)
    """
    # соберём все узлы (ключи + все соседи)
    nodes = set(graph.keys())
    for deps in graph.values():
        nodes.update(deps)

    indeg = {n: 0 for n in nodes}
    for u, deps in graph.items():
        for v in deps:
            indeg[v] = indeg.get(v, 0) + 1

    q = deque([n for n, d in indeg.items() if d == 0])
    order = []
    while q:
        u = q.popleft()
        order.append(u)
        for v in graph.get(u, []):
            indeg[v] -= 1
            if indeg[v] == 0:
                q.append(v)

    remaining = [n for n, d in indeg.items() if d > 0]
    cycles = set(remaining)

    return order, cycles

def best_effort_order(graph, order_partial, cycles):
    """
    Когда есть циклы — постараемся вернуть «best-effort» порядок:
    - сначала уже упорядоченные (order_partial)
    - затем добавляем оставшиеся узлы (cycles) в порядке обхода DFS без зацикливания
    """
    result = list(order_partial)
    visited = set(result)

    def dfs(node, stack):
        if node in visited:
            return
        if node in stack:
            # цикл — не добавляем рекурсивно
            return
        stack.add(node)
        for nb in graph.get(node, []):
            dfs(nb, stack)
        stack.remove(node)
        if node not in visited:
            visited.add(node)
            result.append(node)

    for node in list(cycles):
        dfs(node, set())

    # Если остались какие-то nodes не в result — добавим их
    all_nodes = set(graph.keys()) | {n for deps in graph.values() for n in deps}
    for n in all_nodes:
        if n not in result:
            result.append(n)
    return result

# -------------------
# Вывод и main
# -------------------
def print_graph_ascii(graph, root, indent=0, visited=None):
    if visited is None:
        visited = set()
    prefix = "  " * indent + ("- " if indent else "")
    print(prefix + root)
    visited.add(root)
    for dep in graph.get(root, []):
        if dep not in visited:
            print_graph_ascii(graph, dep, indent + 1, visited)
        else:
            print("  " * (indent + 1) + f"- {dep} (cycle)")

def main(config_path):
    try:
        cfg = load_config(config_path)
        pkg = cfg.get('package_name', '').strip()
        repo = cfg.get('repo_url', '').strip()
        test_mode = cfg.getboolean('test_repo_mode', fallback=False)
        test_file = cfg.get('test_file', 'examples/test_repo_A.txt')
        ascii_tree = cfg.getboolean('ascii_tree', fallback=True)

        if not pkg:
            raise ValueError("package_name is required in config")

        print(f"Root package: {pkg}")
        print(f"Mode: {'TEST' if test_mode else 'REAL'}")

        graph = build_dependency_graph(pkg, repo, test_mode, test_file)

        print("\n--- Dependency graph ---")
        if ascii_tree:
            print_graph_ascii(graph, pkg)
        else:
            for u, deps in graph.items():
                print(f"{u} -> {', '.join(deps) if deps else '[]'}")

        # Топологическая сортировка
        order_partial, cycles = topo_sort_kahn(graph)
        if not cycles:
            print("\n--- Topological order (safe load order) ---")
            for i, node in enumerate(order_partial, start=1):
                print(f"{i}. {node}")
        else:
            print("\n--- Warning: cycles detected in dependency graph ---")
            print("Nodes in cycles:", ", ".join(sorted(cycles)))
            best = best_effort_order(graph, order_partial, cycles)
            print("\n--- Best-effort order (try to load in this sequence) ---")
            for i, node in enumerate(best, start=1):
                print(f"{i}. {node}")

    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(2)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Stage 4: dependency graph + load order (topological sort)")
    parser.add_argument('--config', '-c', default='config.ini')
    args = parser.parse_args()
    main(args.config)
