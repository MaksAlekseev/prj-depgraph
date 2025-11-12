# src/main.py
import sys
import configparser
from pathlib import Path
import argparse
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from collections import defaultdict, deque

# -----------------------------
# Конфиг / утилиты
# -----------------------------
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

        # Пропускаем тестовые зависимости
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

# -----------------------------
# Построение графа и сортировка
# -----------------------------
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

def topo_sort(graph):
    nodes = set(graph.keys()) | {v for deps in graph.values() for v in deps}
    indeg = {n: 0 for n in nodes}
    for u, deps in graph.items():
        for v in deps:
            indeg[v] += 1
    q = deque([n for n, d in indeg.items() if d == 0])
    order = []
    while q:
        u = q.popleft()
        order.append(u)
        for v in graph.get(u, []):
            indeg[v] -= 1
            if indeg[v] == 0:
                q.append(v)
    cycles = [n for n, d in indeg.items() if d > 0]
    return order, cycles

# -----------------------------
# Визуализация
# -----------------------------
def generate_mermaid(graph, output_file="graph.mmd"):
    """
    Генерирует Mermaid-диаграмму (graph TD) для визуализации зависимостей.
    """
    lines = ["graph TD"]
    for src, deps in graph.items():
        if not deps:
            lines.append(f'    "{src}"')
        for dst in deps:
            lines.append(f'    "{src}" --> "{dst}"')
    Path(output_file).write_text("\n".join(lines), encoding="utf-8")
    print(f"\nMermaid diagram saved to: {output_file}")
    print("You can view it on https://mermaid.live/")

# -----------------------------
# Основная логика
# -----------------------------
def main(config_path):
    cfg = load_config(config_path)
    pkg = cfg.get('package_name', '').strip()
    repo = cfg.get('repo_url', '').strip()
    test_mode = cfg.getboolean('test_repo_mode', fallback=False)
    test_file = cfg.get('test_file', 'examples/test_repo_A.txt')

    print(f"Root package: {pkg}")
    print(f"Mode: {'TEST' if test_mode else 'REAL'}")

    graph = build_dependency_graph(pkg, repo, test_mode, test_file)

    print("\n--- Dependency graph (text) ---")
    for u, deps in graph.items():
        print(f"{u} -> {', '.join(deps) if deps else '[]'}")

    order, cycles = topo_sort(graph)
    if cycles:
        print("\n--- Cycles detected ---")
        print(", ".join(cycles))
    else:
        print("\n--- Safe load order ---")
        for i, node in enumerate(order, start=1):
            print(f"{i}. {node}")

    # Визуализация в Mermaid
    generate_mermaid(graph)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Stage 5: visualization of dependency graph")
    parser.add_argument('--config', '-c', default='config.ini')
    args = parser.parse_args()
    main(args.config)
